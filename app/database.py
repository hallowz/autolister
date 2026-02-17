"""
Database models and connection management
"""
from pathlib import Path
from typing import Optional
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from app.config import get_settings

settings = get_settings()

# Ensure data directory exists
Path(settings.database_path).parent.mkdir(parents=True, exist_ok=True)

# Create engine with SQLite-specific settings to prevent locking
engine = create_engine(
    f"sqlite:///{settings.database_path}",
    connect_args={
        "check_same_thread": False,
        "timeout": 30  # 30 second timeout for database locks
    },
    pool_pre_ping=True,  # Check connections before using
    echo=False
)

# Enable WAL mode for better concurrency (allows readers and writers)
from sqlalchemy import event

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """Set SQLite pragmas for better performance and concurrency"""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging for better concurrency
    cursor.execute("PRAGMA synchronous=NORMAL")  # Balance between safety and speed
    cursor.execute("PRAGMA busy_timeout=30000")  # 30 second busy timeout
    cursor.close()

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


class Manual(Base):
    """Manual model for storing PDF manual information"""
    __tablename__ = "manuals"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("scrape_jobs.id"), nullable=True, index=True)  # Associated scrape job
    source_url = Column(String, nullable=False, index=True)
    source_type = Column(String, nullable=False)  # 'search', 'forum', 'manual_site', 'gdrive'
    title = Column(String, nullable=True)
    equipment_type = Column(String, nullable=True)
    manufacturer = Column(String, nullable=True)
    model = Column(String, nullable=True)
    year = Column(String, nullable=True)
    status = Column(String, nullable=False, default='pending', index=True)  # 'pending', 'approved', 'rejected', 'downloaded', 'processing', 'processed', 'listed', 'error'
    pdf_path = Column(String, nullable=True)
    description = Column(Text, nullable=True)  # Generated listing description
    tags = Column(String, nullable=True)  # Comma-separated tags for Etsy
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    error_message = Column(Text, nullable=True)
    
    # Queue and processing state fields
    queue_position = Column(Integer, nullable=True, index=True)  # Position in processing queue
    processing_state = Column(String, nullable=True)  # 'queued', 'downloading', 'processing', 'completed', 'failed'
    processing_started_at = Column(DateTime, nullable=True)
    processing_completed_at = Column(DateTime, nullable=True)
    resources_zip_path = Column(String, nullable=True)  # Path to pre-generated resources zip file
    
    # Relationships
    job = relationship("ScrapeJob", backref="manuals")
    etsy_listing = relationship("EtsyListing", back_populates="manual", uselist=False)
    processing_logs = relationship("ProcessingLog", back_populates="manual")


class EtsyListing(Base):
    """Etsy listing model for tracking Etsy listings"""
    __tablename__ = "etsy_listings"
    
    id = Column(Integer, primary_key=True, index=True)
    manual_id = Column(Integer, ForeignKey("manuals.id"), nullable=False)
    listing_id = Column(Integer, unique=True, nullable=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    price = Column(Float, nullable=False)
    quantity = Column(Integer, default=1)
    status = Column(String, nullable=False, default='draft')  # 'draft', 'active', 'inactive', 'sold_out'
    etsy_file_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    manual = relationship("Manual", back_populates="etsy_listing")
    images = relationship("EtsyImage", back_populates="listing")


class EtsyImage(Base):
    """Etsy image model for tracking uploaded images"""
    __tablename__ = "etsy_images"
    
    id = Column(Integer, primary_key=True, index=True)
    listing_id = Column(Integer, ForeignKey("etsy_listings.id"), nullable=False)
    etsy_image_id = Column(Integer, nullable=True)
    image_path = Column(String, nullable=False)
    is_primary = Column(Boolean, default=False)
    sort_order = Column(Integer, default=0)
    
    # Relationships
    listing = relationship("EtsyListing", back_populates="images")


class ProcessingLog(Base):
    """Processing log model for tracking processing stages"""
    __tablename__ = "processing_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    manual_id = Column(Integer, ForeignKey("manuals.id"), nullable=True)
    stage = Column(String, nullable=False)  # 'scrape', 'download', 'process', 'list'
    status = Column(String, nullable=False)  # 'started', 'completed', 'failed'
    message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    manual = relationship("Manual", back_populates="processing_logs")


class ScrapedSite(Base):
    """Track which sites have been scraped to avoid duplicates"""
    __tablename__ = "scraped_sites"
    
    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, nullable=False, unique=True)
    domain = Column(String, nullable=False)
    first_scraped_at = Column(DateTime, default=datetime.utcnow)
    last_scraped_at = Column(DateTime, default=datetime.utcnow)
    scrape_count = Column(Integer, default=1)
    status = Column(String, nullable=False, default='active')  # 'active', 'exhausted', 'blocked'
    notes = Column(Text, nullable=True)


class ScrapeJobLog(Base):
    """Log entries for scrape jobs"""
    __tablename__ = "scrape_job_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("scrape_jobs.id"), nullable=False, index=True)
    time = Column(DateTime, default=datetime.utcnow, index=True)
    level = Column(String, nullable=True)  # 'info', 'warning', 'error', 'success'
    message = Column(Text, nullable=False)
    
    # Relationship
    job = relationship("ScrapeJob", back_populates="logs")


class ScrapeJob(Base):
    """Scrape job model for managing scrape job queue"""
    __tablename__ = "scrape_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    source_type = Column(String, nullable=False)  # 'search', 'forum', 'manual_site', 'gdrive', 'multi_site'
    query = Column(String, nullable=False)
    max_results = Column(Integer, nullable=False, default=100)  # Increased default to 100
    status = Column(String, nullable=False, default='queued', index=True)  # 'queued', 'scheduled', 'running', 'completed', 'failed'
    scheduled_time = Column(DateTime, nullable=True, index=True)
    schedule_frequency = Column(String, nullable=True)  # 'daily', 'weekly', 'monthly'
    equipment_type = Column(String, nullable=True)
    manufacturer = Column(String, nullable=True)
    queue_position = Column(Integer, nullable=True, index=True)
    progress = Column(Integer, nullable=True)  # 0-100
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    autostart_enabled = Column(Boolean, nullable=False, default=False)  # Whether to auto-start next job in queue
    
    # Advanced scraping settings
    sites = Column(Text, nullable=True)  # JSON array of site URLs to scrape
    search_terms = Column(Text, nullable=True)  # Comma-separated search terms
    exclude_terms = Column(Text, nullable=True)  # Comma-separated terms to exclude
    min_pages = Column(Integer, nullable=True, default=5)  # Minimum PDF page count
    max_pages = Column(Integer, nullable=True)  # Maximum PDF page count
    min_file_size_mb = Column(Float, nullable=True)  # Minimum file size in MB
    max_file_size_mb = Column(Float, nullable=True)  # Maximum file size in MB
    follow_links = Column(Boolean, nullable=True, default=True)  # Whether to follow links on pages
    max_depth = Column(Integer, nullable=True, default=2)  # Maximum link depth to follow
    extract_directories = Column(Boolean, nullable=True, default=True)  # Whether to extract PDFs from directories
    file_extensions = Column(Text, nullable=True, default='pdf')  # Comma-separated file extensions to look for
    skip_duplicates = Column(Boolean, nullable=True, default=True)  # Whether to skip duplicate URLs
    notes = Column(Text, nullable=True)  # Additional notes for the job
    
    # Relationship to logs
    logs = relationship("ScrapeJobLog", back_populates="job", cascade="all, delete-orphan")


def create_tables():
    """Create all tables in database"""
    Base.metadata.create_all(bind=engine)
    

def get_db() -> Session:
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize the database"""
    create_tables()


def regenerate_db():
    """Regenerate the database by dropping all tables and recreating them"""
    # Drop all tables
    Base.metadata.drop_all(bind=engine)
    # Recreate all tables
    Base.metadata.create_all(bind=engine)
    print("Database regenerated successfully!")
