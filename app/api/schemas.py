"""
Pydantic schemas for API requests and responses
"""
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class ManualBase(BaseModel):
    """Base manual schema"""
    source_url: str
    source_type: str
    title: Optional[str] = None
    equipment_type: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    year: Optional[str] = None


class ManualCreate(ManualBase):
    """Schema for creating a manual"""
    pass


class ManualUpdate(BaseModel):
    """Schema for updating a manual"""
    title: Optional[str] = None
    equipment_type: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    year: Optional[str] = None
    status: Optional[str] = None


class ManualResponse(ManualBase):
    """Schema for manual response"""
    id: int
    status: str
    pdf_path: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    error_message: Optional[str] = None
    queue_position: Optional[int] = None
    processing_state: Optional[str] = None
    processing_started_at: Optional[datetime] = None
    processing_completed_at: Optional[datetime] = None
    resources_zip_path: Optional[str] = None
    
    class Config:
        from_attributes = True


class ManualApproval(BaseModel):
    """Schema for manual approval"""
    approved: bool


class EtsyListingBase(BaseModel):
    """Base Etsy listing schema"""
    title: str
    description: str
    price: float
    quantity: int = 1


class EtsyListingCreate(EtsyListingBase):
    """Schema for creating an Etsy listing"""
    manual_id: int


class EtsyListingResponse(EtsyListingBase):
    """Schema for Etsy listing response"""
    id: int
    manual_id: int
    listing_id: Optional[int] = None
    status: str
    etsy_file_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class StatsResponse(BaseModel):
    """Schema for system statistics"""
    total_manuals: int
    pending_manuals: int
    approved_manuals: int
    downloaded_manuals: int
    processed_manuals: int
    listed_manuals: int
    total_listings: int
    active_listings: int


class ScrapingJobRequest(BaseModel):
    """Schema for starting a scraping job"""
    query: Optional[str] = None
    max_results: Optional[int] = None


class ScrapingJobResponse(BaseModel):
    """Schema for scraping job response"""
    job_id: str
    status: str
    message: str


class ErrorResponse(BaseModel):
    """Schema for error responses"""
    error: str
    detail: Optional[str] = None
