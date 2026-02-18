"""
Pydantic schemas for API requests and responses
"""
from pydantic import BaseModel, Field
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
    exclude_sites: Optional[str] = None  # JSON array of site URLs/domains to exclude
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
    exclude_sites: Optional[str] = None  # JSON array of site URLs/domains to exclude
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
    exclude_sites: Optional[str] = None  # JSON array of site URLs/domains to exclude
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
    """Schema for generated scrape config response - ALL fields populated by AI"""
    
    # Basic configuration
    name: str = Field(description="Short, descriptive name for the job")
    source_type: str = Field(default="multi_site", description="Source type: multi_site, search, forum, manual_site, gdrive")
    query: str = Field(description="Search query with OR between terms for better results")
    max_results: int = Field(default=100, description="Maximum number of results to fetch")
    
    # Equipment categorization
    equipment_type: Optional[str] = Field(default=None, description="Type of equipment (e.g., Camera, ATV, Generator)")
    manufacturer: Optional[str] = Field(default=None, description="Manufacturer name (e.g., Honda, Canon, Nikon)")
    model_patterns: Optional[str] = Field(default=None, description="Model patterns to match (e.g., TRX, EOS, D750)")
    year_range: Optional[str] = Field(default=None, description="Year range (e.g., 1990-2020, 1970s)")
    
    # Search terms - CRITICAL for finding correct files
    search_terms: str = Field(description="Comma-separated terms that MUST appear in URL or title")
    exclude_terms: str = Field(default="preview,operator,operation,user manual,owner manual,quick start,brochure,catalog,sample", 
                              description="Comma-separated terms to EXCLUDE")
    
    # File filtering - CRITICAL for getting the right files
    file_extensions: str = Field(default="pdf", description="File extensions to search for (e.g., pdf, zip)")
    min_pages: int = Field(default=5, description="Minimum PDF page count to avoid previews")
    max_pages: Optional[int] = Field(default=None, description="Maximum PDF page count")
    min_file_size_mb: float = Field(default=0.5, description="Minimum file size in MB")
    max_file_size_mb: Optional[float] = Field(default=100, description="Maximum file size in MB")
    
    # Crawling behavior
    follow_links: bool = Field(default=True, description="Whether to follow links on discovered pages")
    max_depth: int = Field(default=3, description="Maximum depth to follow links")
    extract_directories: bool = Field(default=True, description="Extract from PDF directories")
    skip_duplicates: bool = Field(default=True, description="Skip URLs already in database")
    
    # Site targeting
    sites: Optional[str] = Field(default=None, description="Specific sites to scrape (JSON array or newline-separated)")
    exclude_sites: Optional[str] = Field(default=None, description="Sites/domains to exclude from scraping (JSON array or newline-separated)")
    url_patterns: Optional[str] = Field(default=None, description="URL patterns to match (regex patterns)")
    
    # Advanced filtering
    title_patterns: Optional[str] = Field(default=None, description="Patterns that must be in the title")
    content_keywords: Optional[str] = Field(default=None, description="Keywords expected in PDF content")
    
    # Priority and scheduling
    priority: int = Field(default=5, description="Job priority 1-10 (1=highest)")
    
    # Metadata
    description: Optional[str] = Field(default=None, description="Human-readable description of what this job targets")
