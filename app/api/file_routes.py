"""
API routes for file-based listing management (no Etsy API required)
"""
from fastapi import APIRouter, HTTPException, status
from typing import List
from fastapi.responses import FileResponse
from pathlib import Path
from app.etsy.file_manager import FileListingManager
from app.api.schemas import ErrorResponse

router = APIRouter(prefix="/api/files", tags=["File Listings"])

# Initialize file manager
file_manager = FileListingManager()


@router.get("/listings")
def get_all_listings(status: str = None):
    """Get all file-based listings"""
    if status:
        listings = file_manager.get_all_listings(status=status)
    else:
        listings = file_manager.get_all_listings()
    
    return {
        "listings": listings,
        "statistics": file_manager.get_statistics()
    }


@router.get("/listings/{listing_id}")
def get_listing(listing_id: str):
    """Get a specific listing by ID"""
    listing = file_manager.get_listing(listing_id)
    
    if not listing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Listing not found"
        )
    
    return listing


@router.get("/listings/{listing_id}/files")
def get_listing_files(listing_id: str):
    """Get file paths for a listing"""
    files = file_manager.get_listing_files(listing_id)
    
    if not files:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Listing not found"
        )
    
    return files


@router.post("/listings")
def create_listing(
    title: str,
    description: str,
    pdf_path: str,
    images: List[str],
    price: float = None,
    tags: List[str] = None
):
    """Create a new file-based listing"""
    listing = file_manager.create_listing(
        title=title,
        description=description,
        pdf_path=pdf_path,
        images=images,
        price=price,
        tags=tags
    )
    
    return listing


@router.put("/listings/{listing_id}/status")
def update_listing_status(listing_id: str, status: str):
    """Update the status of a listing"""
    valid_statuses = ['ready', 'uploaded', 'sold', 'archived']
    
    if status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        )
    
    success = file_manager.update_status(listing_id, status)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Listing not found"
        )
    
    return {"message": f"Listing status updated to {status}"}


@router.delete("/listings/{listing_id}")
def delete_listing(listing_id: str):
    """Delete a listing and its files"""
    success = file_manager.delete_listing(listing_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Listing not found"
        )
    
    return {"message": "Listing deleted successfully"}


@router.get("/export/csv")
def export_listings_csv():
    """Export all listings to CSV format"""
    csv_path = file_manager.export_listings_csv()
    
    return {
        "message": "CSV export created",
        "path": csv_path
    }


@router.get("/download/{filename:path}")
def download_file(filename: str):
    """Download a file from the listings directory"""
    from app.config import get_settings
    settings = get_settings()
    
    # Security: only allow downloading from listings directory
    listings_dir = Path(settings.database_path).parent / 'listings'
    file_path = listings_dir / filename
    
    # Ensure the file is within listings directory
    try:
        file_path = file_path.resolve()
        if not str(file_path).startswith(str(listings_dir)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        return FileResponse(
            path=str(file_path),
            filename=filename,
            media_type='application/octet-stream'
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/statistics")
def get_statistics():
    """Get statistics about listings"""
    return file_manager.get_statistics()
