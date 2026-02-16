"""
FastAPI routes for the dashboard API
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db, Manual, EtsyListing, ProcessingLog, ScrapedSite
from datetime import datetime
from app.api.schemas import (
    ManualResponse, ManualApproval, EtsyListingResponse,
    StatsResponse, ErrorResponse
)
from app.scrapers import DuckDuckGoScraper
from app.processors import PDFDownloader, PDFProcessor, SummaryGenerator
from app.etsy import ListingManager
from app.config import get_settings

settings = get_settings()

router = APIRouter(prefix="/api", tags=["API"])


@router.get("/stats", response_model=StatsResponse)
def get_stats(db: Session = Depends(get_db)):
    """Get system statistics"""
    total_manuals = db.query(Manual).count()
    pending_manuals = db.query(Manual).filter(Manual.status == 'pending').count()
    approved_manuals = db.query(Manual).filter(Manual.status == 'approved').count()
    downloaded_manuals = db.query(Manual).filter(Manual.status == 'downloaded').count()
    processed_manuals = db.query(Manual).filter(Manual.status == 'processed').count()
    listed_manuals = db.query(Manual).filter(Manual.status == 'listed').count()
    total_listings = db.query(EtsyListing).count()
    active_listings = db.query(EtsyListing).filter(EtsyListing.status == 'active').count()
    
    return StatsResponse(
        total_manuals=total_manuals,
        pending_manuals=pending_manuals,
        approved_manuals=approved_manuals,
        downloaded_manuals=downloaded_manuals,
        processed_manuals=processed_manuals,
        listed_manuals=listed_manuals,
        total_listings=total_listings,
        active_listings=active_listings
    )


@router.get("/manuals", response_model=List[ManualResponse])
def get_manuals(
    status: str = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all manuals, optionally filtered by status"""
    query = db.query(Manual)
    
    if status:
        query = query.filter(Manual.status == status)
    
    manuals = query.order_by(Manual.created_at.desc()).limit(limit).all()
    return manuals


@router.get("/manuals/{manual_id}", response_model=ManualResponse)
def get_manual(manual_id: int, db: Session = Depends(get_db)):
    """Get a specific manual by ID"""
    manual = db.query(Manual).filter(Manual.id == manual_id).first()
    
    if not manual:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Manual not found"
        )
    
    return manual


@router.get("/pending", response_model=List[ManualResponse])
def get_pending_manuals(db: Session = Depends(get_db)):
    """Get all pending manuals for approval"""
    manuals = db.query(Manual).filter(
        Manual.status == 'pending'
    ).order_by(Manual.created_at.desc()).all()
    
    return manuals


@router.post("/pending/{manual_id}/approve")
def approve_manual(manual_id: int, db: Session = Depends(get_db)):
    """Approve a pending manual for download"""
    manual = db.query(Manual).filter(Manual.id == manual_id).first()
    
    if not manual:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Manual not found"
        )
    
    if manual.status != 'pending':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Manual is not pending"
        )
    
    manual.status = 'approved'
    db.commit()
    
    # Trigger download task (would use Celery in production)
    # For now, just update status
    
    return {"message": "Manual approved for download", "manual_id": manual_id}


@router.post("/pending/{manual_id}/reject")
def reject_manual(manual_id: int, db: Session = Depends(get_db)):
    """Reject a pending manual"""
    manual = db.query(Manual).filter(Manual.id == manual_id).first()
    
    if not manual:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Manual not found"
        )
    
    if manual.status != 'pending':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Manual is not pending"
        )
    
    manual.status = 'rejected'
    db.commit()
    
    return {"message": "Manual rejected", "manual_id": manual_id}


@router.post("/manuals/{manual_id}/download")
def download_manual(manual_id: int, db: Session = Depends(get_db)):
    """Download an approved manual"""
    manual = db.query(Manual).filter(Manual.id == manual_id).first()
    
    if not manual:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Manual not found"
        )
    
    if manual.status != 'approved':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Manual is not approved"
        )
    
    # Download PDF
    downloader = PDFDownloader()
    pdf_path = downloader.download(manual.source_url, manual_id)
    
    if not pdf_path:
        manual.status = 'error'
        manual.error_message = "Failed to download PDF"
        db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to download PDF"
        )
    
    manual.status = 'downloaded'
    manual.pdf_path = pdf_path
    db.commit()
    
    return {"message": "Manual downloaded successfully", "pdf_path": pdf_path}


@router.post("/manuals/{manual_id}/process")
def process_manual(manual_id: int, db: Session = Depends(get_db)):
    """Process a downloaded manual (extract images, generate summary)"""
    manual = db.query(Manual).filter(Manual.id == manual_id).first()
    
    if not manual:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Manual not found"
        )
    
    if manual.status != 'downloaded':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Manual is not downloaded"
        )
    
    if not manual.pdf_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No PDF file found"
        )
    
    try:
        # Process PDF
        processor = PDFProcessor()
        summary_gen = SummaryGenerator()
        
        # Extract metadata
        pdf_metadata = processor.extract_metadata(manual.pdf_path)
        
        # Extract text
        text = processor.extract_first_page_text(manual.pdf_path)
        
        # Generate images
        images = processor.generate_listing_images(manual.pdf_path, manual_id)
        
        # Generate title and description
        title = summary_gen.generate_title(
            {**pdf_metadata, 'manufacturer': manual.manufacturer, 'model': manual.model},
            text
        )
        description = summary_gen.generate_description(
            {**pdf_metadata, 'manufacturer': manual.manufacturer, 'model': manual.model},
            text,
            processor.get_page_count(manual.pdf_path)
        )
        
        # Update manual
        if not manual.title:
            manual.title = title
        
        manual.status = 'processed'
        db.commit()
        
        return {
            "message": "Manual processed successfully",
            "title": title,
            "description": description,
            "images": images
        }
    
    except Exception as e:
        manual.status = 'error'
        manual.error_message = str(e)
        db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process manual: {str(e)}"
        )


@router.post("/manuals/{manual_id}/list")
def list_on_etsy(manual_id: int, db: Session = Depends(get_db)):
    """Create Etsy listing for a processed manual"""
    manual = db.query(Manual).filter(Manual.id == manual_id).first()
    
    if not manual:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Manual not found"
        )
    
    if manual.status != 'processed':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Manual is not processed"
        )
    
    try:
        # Process PDF to get images and content
        processor = PDFProcessor()
        summary_gen = SummaryGenerator()
        
        # Extract metadata and text
        pdf_metadata = processor.extract_metadata(manual.pdf_path)
        text = processor.extract_first_page_text(manual.pdf_path)
        
        # Generate title and description
        title = summary_gen.generate_title(
            {**pdf_metadata, 'manufacturer': manual.manufacturer, 'model': manual.model},
            text
        )
        description = summary_gen.generate_description(
            {**pdf_metadata, 'manufacturer': manual.manufacturer, 'model': manual.model},
            text,
            processor.get_page_count(manual.pdf_path)
        )
        
        # Generate images
        images = processor.generate_listing_images(manual.pdf_path, manual_id)
        
        # Create Etsy listing
        listing_manager = ListingManager()
        listing_id = listing_manager.create_digital_listing(
            title=title,
            description=description,
            pdf_path=manual.pdf_path,
            image_paths=images['main'] + images['additional'],
            price=settings.etsy_default_price
        )
        
        if not listing_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create Etsy listing"
            )
        
        # Create listing record
        etsy_listing = EtsyListing(
            manual_id=manual_id,
            listing_id=listing_id,
            title=title,
            description=description,
            price=settings.etsy_default_price,
            status='draft'
        )
        db.add(etsy_listing)
        
        # Update manual status
        manual.status = 'listed'
        db.commit()
        
        return {
            "message": "Etsy listing created successfully",
            "listing_id": listing_id,
            "etsy_listing_id": etsy_listing.id
        }
    
    except HTTPException:
        raise
    except Exception as e:
        manual.status = 'error'
        manual.error_message = str(e)
        db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create listing: {str(e)}"
        )


@router.get("/listings", response_model=List[EtsyListingResponse])
def get_listings(db: Session = Depends(get_db)):
    """Get all Etsy listings"""
    listings = db.query(EtsyListing).order_by(
        EtsyListing.created_at.desc()
    ).all()
    
    return listings


@router.post("/listings/{listing_id}/activate")
def activate_listing(listing_id: int, db: Session = Depends(get_db)):
    """Activate an Etsy listing"""
    listing = db.query(EtsyListing).filter(EtsyListing.id == listing_id).first()
    
    if not listing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Listing not found"
        )
    
    if not listing.listing_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No Etsy listing ID found"
        )
    
    # Activate on Etsy
    listing_manager = ListingManager()
    success = listing_manager.activate_listing(listing.listing_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to activate listing on Etsy"
        )
    
    listing.status = 'active'
    db.commit()
    
    return {"message": "Listing activated successfully"}


@router.post("/listings/{listing_id}/deactivate")
def deactivate_listing(listing_id: int, db: Session = Depends(get_db)):
    """Deactivate an Etsy listing"""
    listing = db.query(EtsyListing).filter(EtsyListing.id == listing_id).first()
    
    if not listing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Listing not found"
        )
    
    if not listing.listing_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No Etsy listing ID found"
        )
    
    # Deactivate on Etsy
    listing_manager = ListingManager()
    success = listing_manager.deactivate_listing(listing.listing_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to deactivate listing on Etsy"
        )
    
    listing.status = 'inactive'
    db.commit()
    
    return {"message": "Listing deactivated successfully"}


@router.post("/database/reset")
def reset_database(db: Session = Depends(get_db)):
    """Reset database - delete all manuals and listings"""
    try:
        # Delete all processing logs
        db.query(ProcessingLog).delete()
        
        # Delete all Etsy listings
        db.query(EtsyListing).delete()
        
        # Delete all manuals
        db.query(Manual).delete()
        
        # Delete all scraped sites tracking
        db.query(ScrapedSite).delete()
        
        db.commit()
        
        return {"message": "Database reset successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset database: {str(e)}"
        )


@router.get("/scraped-sites", response_model=List[dict])
def get_scraped_sites(db: Session = Depends(get_db)):
    """Get all scraped sites with statistics"""
    sites = db.query(ScrapedSite).order_by(ScrapedSite.last_scraped_at.desc()).all()
    
    return [
        {
            "id": site.id,
            "url": site.url,
            "domain": site.domain,
            "first_scraped_at": site.first_scraped_at.isoformat() if site.first_scraped_at else None,
            "last_scraped_at": site.last_scraped_at.isoformat() if site.last_scraped_at else None,
            "scrape_count": site.scrape_count,
            "status": site.status,
            "notes": site.notes
        }
        for site in sites
    ]


@router.post("/scraped-sites")
def add_scraped_site(site_data: dict, db: Session = Depends(get_db)):
    """Add a scraped site to tracking"""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(site_data.get('url', ''))
        domain = parsed.netloc
        
        # Check if site already exists
        existing = db.query(ScrapedSite).filter(ScrapedSite.url == site_data['url']).first()
        if existing:
            # Update existing site
            existing.last_scraped_at = datetime.utcnow()
            existing.scrape_count += 1
            existing.status = 'active'
            existing.notes = site_data.get('notes', '')
            db.commit()
            return {"message": "Scraped site updated", "id": existing.id}
        
        # Create new site
        new_site = ScrapedSite(
            url=site_data['url'],
            domain=domain,
            status='active',
            notes=site_data.get('notes', '')
        )
        db.add(new_site)
        db.commit()
        
        return {"message": "Scraped site added", "id": new_site.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add scraped site: {str(e)}"
        )


@router.delete("/scraped-sites/{site_id}")
def delete_scraped_site(site_id: int, db: Session = Depends(get_db)):
    """Delete a scraped site from tracking"""
    try:
        site = db.query(ScrapedSite).filter(ScrapedSite.id == site_id).first()
        if not site:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Scraped site not found"
            )
        
        db.delete(site)
        db.commit()
        
        return {"message": "Scraped site deleted"}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete scraped site: {str(e)}"
        )


@router.post("/scraped-sites/{site_id}/mark-exhausted")
def mark_site_exhausted(site_id: int, db: Session = Depends(get_db)):
    """Mark a scraped site as exhausted (no more results)"""
    try:
        site = db.query(ScrapedSite).filter(ScrapedSite.id == site_id).first()
        if not site:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Scraped site not found"
            )
        
        site.status = 'exhausted'
        site.notes = 'No more results found in last scrape'
        db.commit()
        
        return {"message": "Site marked as exhausted"}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to mark site as exhausted: {str(e)}"
        )
