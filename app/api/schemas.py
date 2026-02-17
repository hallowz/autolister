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


# Scrape Job Queue Schemas

class ScrapeJobCreate(BaseModel):
    """Schema for creating a scrape job"""
    name: str
    source_type: str  # 'search', 'forum', 'manual_site', 'gdrive', 'multi_site'
    query: str
    max_results: int = 100  # Default to 100 results for comprehensive scraping
    scheduled_time: Optional[str] = None  # ISO format datetime
    schedule_frequency: Optional[str] = None  # 'daily', 'weekly', 'monthly'
    equipment_type: Optional[str] = None
    manufacturer: Optional[str] = None
    autostart_enabled: bool = False  # Auto-start next job in queue
    
    # Advanced scraping settings
    sites: Optional[str] = None  # JSON array of site URLs to scrape
    search_terms: Optional[str] = None  # Comma-separated search terms
    exclude_terms: Optional[str] = None  # Comma-separated terms to exclude
    min_pages: Optional[int] = None  # Minimum PDF page count
    max_pages: Optional[int] = None  # Maximum PDF page count
    min_file_size_mb: Optional[float] = None  # Minimum file size in MB
    max_file_size_mb: Optional[float] = None  # Maximum file size in MB
    follow_links: Optional[bool] = None  # Whether to follow links on pages
    max_depth: Optional[int] = None  # Maximum link depth to follow
    extract_directories: Optional[bool] = None  # Whether to extract PDFs from directories
    file_extensions: Optional[str] = None  # Comma-separated file extensions to look for
    skip_duplicates: Optional[bool] = None  # Whether to skip duplicate URLs
    notes: Optional[str] = None  # Additional notes for the job


class ScrapeJobUpdate(BaseModel):
    """Schema for updating a scrape job"""
    name: Optional[str] = None
    source_type: Optional[str] = None
    query: Optional[str] = None
    max_results: Optional[int] = None
    scheduled_time: Optional[str] = None
    schedule_frequency: Optional[str] = None
    equipment_type: Optional[str] = None
    manufacturer: Optional[str] = None
    autostart_enabled: Optional[bool] = None
    
    # Advanced scraping settings
    sites: Optional[str] = None  # JSON array of site URLs to scrape
    search_terms: Optional[str] = None  # Comma-separated search terms
    exclude_terms: Optional[str] = None  # Comma-separated terms to exclude
    min_pages: Optional[int] = None  # Minimum PDF page count
    max_pages: Optional[int] = None  # Maximum PDF page count
    min_file_size_mb: Optional[float] = None  # Minimum file size in MB
    max_file_size_mb: Optional[float] = None  # Maximum file size in MB
    follow_links: Optional[bool] = None  # Whether to follow links on pages
    max_depth: Optional[int] = None  # Maximum link depth to follow
    extract_directories: Optional[bool] = None  # Whether to extract PDFs from directories
    file_extensions: Optional[str] = None  # Comma-separated file extensions to look for
    skip_duplicates: Optional[bool] = None  # Whether to skip duplicate URLs
    notes: Optional[str] = None  # Additional notes for the job


class ScrapeJobResponse(BaseModel):
    """Schema for scrape job response"""
    id: int
    name: str
    source_type: str
    query: str
    max_results: int
    status: str  # 'queued', 'scheduled', 'running', 'completed', 'failed'
    scheduled_time: Optional[datetime] = None
    schedule_frequency: Optional[str] = None
    equipment_type: Optional[str] = None
    manufacturer: Optional[str] = None
    queue_position: Optional[int] = None
    progress: Optional[int] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    autostart_enabled: bool
    
    # Advanced scraping settings
    sites: Optional[str] = None  # JSON array of site URLs to scrape
    search_terms: Optional[str] = None  # Comma-separated search terms
    exclude_terms: Optional[str] = None  # Comma-separated terms to exclude
    min_pages: Optional[int] = None  # Minimum PDF page count
    max_pages: Optional[int] = None  # Maximum PDF page count
    min_file_size_mb: Optional[float] = None  # Minimum file size in MB
    max_file_size_mb: Optional[float] = None  # Maximum file size in MB
    follow_links: Optional[bool] = None  # Whether to follow links on pages
    max_depth: Optional[int] = None  # Maximum link depth to follow
    extract_directories: Optional[bool] = None  # Whether to extract PDFs from directories
    file_extensions: Optional[str] = None  # Comma-separated file extensions to look for
    skip_duplicates: Optional[bool] = None  # Whether to skip duplicate URLs
    notes: Optional[str] = None  # Additional notes for the job
    
    class Config:
        from_attributes = True


class ScrapeJobListResponse(BaseModel):
    """Schema for scrape job list response"""
    jobs: List[ScrapeJobResponse]
    stats: dict


class ScrapeJobStatsResponse(BaseModel):
    """Schema for scrape job statistics"""
    queued: int
    scheduled: int
    running: int
    completed: int
    failed: int


class GenerateConfigRequest(BaseModel):
    """Schema for generating scrape config with AI"""
    prompt: str


class GenerateConfigResponse(BaseModel):
    """Schema for generated scrape config response"""
    name: str
    source_type: str
    query: str
    max_results: int
    equipment_type: Optional[str] = None
    manufacturer: Optional[str] = None
    # Additional fields for advanced scraping
    search_terms: Optional[str] = None  # Comma-separated search terms
    exclude_terms: Optional[str] = None  # Terms to exclude from search
    min_pages: Optional[int] = None  # Minimum PDF page count
    traversal_pattern: Optional[str] = None  # Pattern for traversing links
