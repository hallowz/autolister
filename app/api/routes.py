"""
FastAPI routes for the dashboard API
"""
import os
import zipfile
import threading
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
from app.utils import generate_safe_filename

settings = get_settings()

router = APIRouter(prefix="/api", tags=["API"])


@router.get("/stats", response_model=StatsResponse)
def get_stats(db: Session = Depends(get_db)):
    """Get system statistics (excluding rejected manuals)"""
    total_manuals = db.query(Manual).filter(Manual.status != 'rejected').count()
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
    include_rejected: bool = False,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all manuals, optionally filtered by status"""
    query = db.query(Manual)
    
    # Exclude rejected by default unless explicitly requested
    if not include_rejected:
        query = query.filter(Manual.status != 'rejected')
    
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


@router.delete("/manuals/{manual_id}")
def delete_manual(manual_id: int, db: Session = Depends(get_db)):
    """Delete a manual"""
    manual = db.query(Manual).filter(Manual.id == manual_id).first()
    
    if not manual:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Manual not found"
        )
    
    # Delete associated files if they exist
    if manual.pdf_path and os.path.exists(manual.pdf_path):
        try:
            os.remove(manual.pdf_path)
        except Exception as e:
            print(f"Error deleting PDF file: {e}")
    
    # Delete generated images
    try:
        from app.processors import PDFProcessor
        processor = PDFProcessor()
        processor.cleanup_images(
            manual_id=manual_id,
            manufacturer=manual.manufacturer,
            model=manual.model,
            year=manual.year
        )
    except Exception as e:
        print(f"Error cleaning up images: {e}")
    
    # Delete from database
    db.delete(manual)
    db.commit()
    
    return {"message": "Manual deleted successfully", "manual_id": manual_id}


@router.get("/pending", response_model=List[ManualResponse])
def get_pending_manuals(db: Session = Depends(get_db)):
    """Get all pending manuals for approval"""
    manuals = db.query(Manual).filter(
        Manual.status == 'pending'
    ).order_by(Manual.created_at.desc()).all()
    
    return manuals


def process_manual_background(manual_id: int, pdf_path: str):
    """Background task to process a manual after download"""
    from app.database import SessionLocal
    
    db = SessionLocal()
    try:
        manual = db.query(Manual).filter(Manual.id == manual_id).first()
        if not manual:
            return
        
        # Process PDF (extract images, generate summary)
        processor = PDFProcessor()
        summary_gen = SummaryGenerator()
        
        # Extract metadata
        pdf_metadata = processor.extract_metadata(manual.pdf_path)
        
        # Extract text
        text = processor.extract_first_page_text(manual.pdf_path)
        
        # Generate images with meaningful filenames
        images = processor.generate_listing_images(
            manual.pdf_path,
            manual_id,
            manufacturer=manual.manufacturer,
            model=manual.model,
            year=manual.year
        )
        
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
        
        manual.description = description
        manual.status = 'processed'
        db.commit()
        
    except Exception as e:
        manual = db.query(Manual).filter(Manual.id == manual_id).first()
        if manual:
            manual.status = 'error'
            manual.error_message = str(e)
            db.commit()
    finally:
        db.close()


@router.post("/pending/{manual_id}/approve")
def approve_manual(manual_id: int, db: Session = Depends(get_db)):
    """Approve a pending manual and auto-download/process it"""
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
    
    try:
        # Download PDF
        downloader = PDFDownloader()
        pdf_path = downloader.download(
            manual.source_url,
            manual_id,
            manufacturer=manual.manufacturer,
            model=manual.model,
            year=manual.year
        )
        
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
        
        # Process PDF in background thread
        thread = threading.Thread(target=process_manual_background, args=(manual_id, pdf_path))
        thread.daemon = True
        thread.start()
        
        return {
            "message": "Manual approved and downloaded. Processing in background.",
            "manual_id": manual_id,
            "status": "downloaded"
        }
        
    except Exception as e:
        manual.status = 'error'
        manual.error_message = str(e)
        db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process manual: {str(e)}"
        )


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

@router.post("/manuals/{manual_id}/download-resources")
def download_resources(manual_id: int, db: Session = Depends(get_db)):
    """Download all resources (PDF, images, README, description) for a processed manual"""
    manual = db.query(Manual).filter(Manual.id == manual_id).first()
    
    if not manual:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Manual not found"
        )
    
    if manual.status != 'processed':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Manual is not processed yet"
        )
    
    if not manual.pdf_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No PDF file found"
        )
    
    try:
        # Import processors
        from app.processors import PDFProcessor, SummaryGenerator
        
        # Process PDF to get content
        processor = PDFProcessor()
        summary_gen = SummaryGenerator()
        
        # Extract metadata and text
        pdf_metadata = processor.extract_metadata(manual.pdf_path)
        text = processor.extract_first_page_text(manual.pdf_path)
        page_count = processor.get_page_count(manual.pdf_path)
        
        # Generate title and description
        title = summary_gen.generate_title(
            {**pdf_metadata, 'manufacturer': manual.manufacturer, 'model': manual.model},
            text
        )
        description = summary_gen.generate_description(
            {**pdf_metadata, 'manufacturer': manual.manufacturer, 'model': manual.model},
            text,
            page_count
        )
        
        # Check if images already exist from previous processing
        # Generate listing images (will reuse existing images if available)
        images = processor.generate_listing_images(
            manual.pdf_path,
            manual_id,
            manufacturer=manual.manufacturer,
            model=manual.model,
            year=manual.year
        )
        
        # Create a zip file with all resources
        # Use PDF metadata for model/year if not in manual record
        pdf_model = manual.model or pdf_metadata.get('model')
        pdf_year = manual.year or pdf_metadata.get('year')
        
        zip_name = generate_safe_filename(
            manual.manufacturer,
            pdf_model,
            pdf_year,
            title=manual.title
        )
        zip_path = f"./data/{zip_name}_resources.zip"
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add PDF
            if os.path.exists(manual.pdf_path):
                zipf.write(manual.pdf_path, os.path.basename(manual.pdf_path))
            
            # Add generated images directly to zip
            all_images = images.get('main', []) + images.get('additional', [])
            # Filter out None values and check existence
            valid_images = [img for img in all_images if img is not None and os.path.exists(img)]
            
            if valid_images:
                for image_path in valid_images:
                    # Use just the filename in the zip
                    zipf.write(image_path, os.path.basename(image_path))
            else:
                # If no images were generated, log this
                print(f"Warning: No valid images found for manual {manual_id}")
                print(f"All images: {all_images}")
            
            # Generate and add README.md
            readme_content = f"""# Listing Instructions for: {title}

## Quick Start Guide

### 1. Upload the PDF
- Go to your Etsy shop manager
- Click "Add a listing"
- Upload the PDF file: `{os.path.basename(manual.pdf_path)}`
- This will be the digital file buyers download

### 2. Upload Images
Use the following images in order for your listing:

**Main Image (First Image):**
- Use: `manual_{manual_id}_main.jpg` (or .png)
- This is the cover/title page of the manual

**Additional Images:**
- Upload the remaining images: `manual_{manual_id}_additional_*.jpg` (or .png)
- These show sample pages including the index/table of contents
- Upload up to 5 images total (1 main + 4 additional)

### 3. Title
Copy and paste this title:
```
{title}
```

### 4. Description
Copy and paste this description:
```
{description}
```

### 5. Pricing & Quantity
- Price: $4.99 (or adjust as needed)
- Quantity: 9999 (unlimited digital downloads)

### 6. Category & Tags
- Category: Choose the most relevant equipment category (ATV, Lawn Mower, Generator, etc.)
- Tags: Add relevant tags like "service manual", "repair manual", "digital download", "{manual.manufacturer or 'manual'}"

### 7. Shipping
- Set shipping to "Digital Item" or "No shipping required"
- Buyers will receive an instant download link after purchase

## Tips for Success

- Use high-quality images (already provided)
- Make sure the title includes manufacturer and model
- Include all relevant keywords in tags
- Respond quickly to buyer questions
- Consider creating variations for different models

## File Information

- PDF File: `{os.path.basename(manual.pdf_path)}`
- Pages: {page_count}
- Images Included: {len(valid_images)} (minimum 5 images provided)
- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
            
            zipf.writestr('README.md', readme_content)
            
            # Add short description file
            short_desc = f"""Title: {title}

Description:
{description}

Manufacturer: {manual.manufacturer or 'N/A'}
Model: {manual.model or 'N/A'}
Pages: {page_count}
"""
            zipf.writestr('description.txt', short_desc)
        
        # Read the zip file and return it
        with open(zip_path, 'rb') as f:
            from fastapi.responses import FileResponse
            
            return FileResponse(
                path=zip_path,
                filename=f'manual_{manual_id}_resources.zip',
                media_type='application/zip'
            )
            
    except Exception as e:
        manual.status = 'error'
        manual.error_message = f"Failed to create resources package: {str(e)}"
        db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create resources package: {str(e)}"
        )

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
        images = processor.generate_listing_images(
            manual.pdf_path,
            manual_id,
            manufacturer=manual.manufacturer,
            model=manual.model,
            year=manual.year
        )
        
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
        images = processor.generate_listing_images(
            manual.pdf_path,
            manual_id,
            manufacturer=manual.manufacturer,
            model=manual.model,
            year=manual.year
        )
        
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


@router.post("/manuals/{manual_id}/upload-to-etsy")
def upload_to_etsy(manual_id: int, db: Session = Depends(get_db)):
    """Upload a processed manual to Etsy programmatically"""
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
        # Process PDF to get content
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
        images = processor.generate_listing_images(
            manual.pdf_path,
            manual_id,
            manufacturer=manual.manufacturer,
            model=manual.model,
            year=manual.year
        )
        
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
        
    except Exception as e:
        manual.status = 'error'
        manual.error_message = str(e)
        db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload to Etsy: {str(e)}"
        )


@router.post("/manuals/{manual_id}/mark-listed")
def mark_as_listed(manual_id: int, db: Session = Depends(get_db)):
    """Manually mark a processed manual as listed (after manual Etsy listing)"""
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
        # Get title and description for the listing
        processor = PDFProcessor()
        summary_gen = SummaryGenerator()
        
        pdf_metadata = processor.extract_metadata(manual.pdf_path)
        text = processor.extract_first_page_text(manual.pdf_path)
        
        title = summary_gen.generate_title(
            {**pdf_metadata, 'manufacturer': manual.manufacturer, 'model': manual.model},
            text
        )
        description = summary_gen.generate_description(
            {**pdf_metadata, 'manufacturer': manual.manufacturer, 'model': manual.model},
            text,
            processor.get_page_count(manual.pdf_path)
        )
        
        # Create Etsy listing record (without calling Etsy API)
        etsy_listing = EtsyListing(
            manual_id=manual_id,
            listing_id=None,  # No actual Etsy listing ID since it's manual
            title=title,
            description=description,
            price=settings.etsy_default_price,
            status='draft'  # Mark as draft since it was manually listed
        )
        db.add(etsy_listing)
        
        # Update manual status
        manual.status = 'listed'
        db.commit()
        
        return {
            "message": "Manual marked as listed successfully",
            "manual_id": manual_id,
            "etsy_listing_id": etsy_listing.id
        }
        
    except Exception as e:
        manual.status = 'error'
        manual.error_message = str(e)
        db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to mark manual as listed: {str(e)}"
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
