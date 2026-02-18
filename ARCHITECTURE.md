# AutoLister - Architecture Document

## Table of Contents

1. [Simple Description](#simple-description)
2. [Detailed Architecture](#detailed-architecture)
3. [Important Function Explanations](#important-function-explanations)
   - [Multi-Site Scraper](#multi-site-scraper)
   - [PDF Processing Pipeline](#pdf-processing-pipeline)
   - [AI-Based Metadata Extraction](#ai-based-metadata-extraction)
   - [Listing Content Generation](#listing-content-generation)
   - [Processing Queue Manager](#processing-queue-manager)
   - [Scrape Job Management](#scrape-job-management)

---

## Simple Description

**AutoLister** is a Python-based application designed to automatically discover, download, process, and prepare PDF equipment manuals for sale on Etsy. The system runs on Raspberry Pi (or any Linux/Windows system) and provides a web-based dashboard for managing the entire workflow.

### Core Workflow

1. **Discovery**: Scrape multiple sources (search engines, forums, manual sites, Google Drive) to find PDF manual URLs
2. **Approval**: Review discovered manuals via web dashboard before downloading
3. **Download**: Download approved PDFs to local storage
4. **Process**: Extract text, generate images, create listing descriptions using AI
5. **List**: Generate file-based listings for manual upload to Etsy (or use Etsy API for direct listing)

### Key Features

- **Multi-source scraping**: Search engines (DuckDuckGo/Google/Bing), equipment forums, manual-specific websites, Google Drive links
- **Concurrent crawling**: Multi-site scraper can crawl multiple websites simultaneously with configurable depth
- **AI-powered content**: Uses Groq's free Llama API for metadata extraction and listing content generation
- **Web dashboard**: Real-time monitoring and manual approval workflow
- **Background processing**: Celery + Redis for asynchronous task execution
- **File-based listings**: Create listing files for manual Etsy upload (no API required)

---

## Detailed Architecture

### Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Backend Framework** | Python 3.11+ / FastAPI | Web API and dashboard |
| **Database** | SQLite (with WAL mode) | Persistent storage |
| **Task Queue** | Celery + Redis | Background job processing |
| **Scraping** | BeautifulSoup4, requests | Web content extraction |
| **PDF Processing** | PyPDF2, pdfplumber, Pillow | PDF text/image extraction |
| **AI Processing** | Groq API (Llama 3.3) | Metadata and content generation |
| **Frontend** | HTML/CSS/JavaScript (Vanilla) | Web dashboard |
| **Deployment** | Docker + Docker Compose | Containerization |

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Web Dashboard                                   │
│                         (FastAPI + Static Files)                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   Dashboard  │  │  Scrape Queue│  │   Manual     │  │   Listing     │  │
│  │   (index)    │  │   Management │  │   Approval   │  │   Manager    │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              API Layer                                       │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐        │
│  │  Manual Routes   │  │  Scrape Job      │  │  File Listing    │        │
│  │  (approval,      │  │  Routes          │  │  Routes          │        │
│  │   download,      │  │  (create, queue, │  │  (create, export)│        │
│  │   process)       │  │   execute)       │  │                  │        │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘        │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Business Logic Layer                               │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐        │
│  │  Scrapers        │  │  Processors      │  │  Etsy Integration│        │
│  │  ┌────────────┐  │  │  ┌────────────┐  │  │  ┌────────────┐  │        │
│  │  │ Multi-Site │  │  │  │ PDF Handler│  │  │  │ Listing    │  │        │
│  │  │ Scraper    │  │  │  │ PDF Proc   │  │  │  │ Manager    │  │        │
│  │  ├────────────┤  │  │  │ AI Extract │  │  │  │ File Mgr   │  │        │
│  │  │ Search Eng │  │  │  │ List Gen   │  │  │  └────────────┘  │        │
│  │  │ Forums     │  │  │  │ Queue Mgr  │  │  │                  │        │
│  │  │ Manual Sites│  │  │  └────────────┘  │  │                  │        │
│  │  │ Google Drive│  │  │                  │  │                  │        │
│  │  └────────────┘  │  │                  │  │                  │        │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘        │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Background Tasks (Celery)                            │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐        │
│  │  Search Jobs     │  │  Download Jobs   │  │  Processing Jobs │        │
│  │  (run_search_job)│  │  (download_pdf)  │  │  (process_pdf)   │        │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘        │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            Data Layer                                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   SQLite DB  │  │   PDF Files  │  │   Images     │  │   Listing    │  │
│  │   (autolister│  │   (/data/    │  │   (/data/    │  │   Files      │  │
│  │    .db)      │  │    pdfs/)    │  │    images/)  │  │   (/data/    │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │    listings/) │  │
│                                                         └──────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            External Services                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   Search     │  │   Groq AI   │  │   Redis      │  │   Etsy API   │  │
│  │   APIs       │  │   API        │  │   (Queue)    │  │   (Optional) │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Directory Structure

```
AutoLister/
├── app/
│   ├── api/                    # API routes and schemas
│   │   ├── routes.py          # Manual management endpoints
│   │   ├── scrape_routes.py   # Scrape job management endpoints
│   │   ├── file_routes.py     # File-based listing endpoints
│   │   └── schemas.py         # Pydantic schemas
│   ├── scrapers/              # Web scraping modules
│   │   ├── base.py            # Base scraper class
│   │   ├── multi_site_scraper.py  # Multi-site concurrent scraper
│   │   ├── search_engine.py   # Search engine scrapers
│   │   ├── forums.py          # Forum scrapers
│   │   ├── manual_sites.py    # Manual site scrapers
│   │   ├── gdrive.py          # Google Drive link extractor
│   │   └── duckduckgo.py      # DuckDuckGo scraper
│   ├── processors/            # PDF and content processing
│   │   ├── pdf_handler.py     # PDF download and validation
│   │   ├── pdf_processor.py   # Text extraction and image generation
│   │   ├── pdf_ai_extractor.py # AI-based metadata extraction
│   │   ├── listing_generator.py # AI-based listing content generation
│   │   ├── summary_gen.py     # Summary generation
│   │   └── queue_manager.py   # Processing queue management
│   ├── etsy/                  # Etsy integration
│   │   ├── client.py          # Etsy API client
│   │   ├── listing.py         # Listing management
│   │   └── file_manager.py    # File-based listing manager
│   ├── tasks/                 # Celery background tasks
│   │   └── jobs.py            # Scraping and processing jobs
│   ├── static/                # Web dashboard frontend
│   │   ├── index.html         # Main dashboard
│   │   ├── scrape-queue.html  # Scrape queue management
│   │   ├── css/               # Stylesheets
│   │   └── js/                # JavaScript
│   ├── utils/                 # Utility functions
│   │   └── filename_utils.py  # Filename utilities
│   ├── config.py              # Configuration management
│   ├── database.py            # Database models and connection
│   └── main.py                # FastAPI application entry point
├── config/                    # Configuration files
│   └── search_terms.yaml      # Equipment categories and search terms
├── data/                      # Data storage
│   ├── autolister.db          # SQLite database
│   ├── pdfs/                  # Downloaded PDFs
│   ├── images/                # Generated images
│   └── listings/              # Generated listing files
├── docker/                    # Docker configuration
│   ├── Dockerfile
│   └── docker-compose.yml
├── migrations/                # Database migrations
├── scripts/                   # Utility scripts
└── requirements.txt           # Python dependencies
```

### Database Schema

#### Manual Table
```sql
CREATE TABLE manuals (
    id INTEGER PRIMARY KEY,
    job_id INTEGER,                    -- Associated scrape job
    source_url TEXT NOT NULL,          -- Original PDF URL
    source_type TEXT,                  -- 'search', 'forum', 'manual_site', 'gdrive'
    title TEXT,                        -- Extracted title
    equipment_type TEXT,               -- Equipment category
    manufacturer TEXT,                -- Manufacturer name
    model TEXT,                        -- Model name
    year TEXT,                         -- Year
    status TEXT,                       -- 'pending', 'approved', 'rejected', 
                                       -- 'downloaded', 'processed', 'listed', 'error'
    pdf_path TEXT,                     -- Local PDF file path
    description TEXT,                  -- Generated listing description
    tags TEXT,                         -- Comma-separated tags
    queue_position INTEGER,            -- Position in processing queue
    processing_state TEXT,             -- 'queued', 'downloading', 'processing', 
                                       -- 'completed', 'failed'
    processing_started_at DATETIME,
    processing_completed_at DATETIME,
    resources_zip_path TEXT,           -- Pre-generated resources zip
    created_at DATETIME,
    updated_at DATETIME,
    error_message TEXT
);
```

#### ScrapeJob Table
```sql
CREATE TABLE scrape_jobs (
    id INTEGER PRIMARY KEY,
    name TEXT,                         -- Job name
    source_type TEXT,                   -- 'search', 'forum', 'manual_site', 'multi_site'
    query TEXT,                         -- Search query
    max_results INTEGER,                -- Maximum results
    status TEXT,                        -- 'queued', 'scheduled', 'running', 
                                       -- 'completed', 'failed', 'paused'
    scheduled_time DATETIME,            -- Scheduled execution time
    schedule_frequency TEXT,            -- 'once', 'daily', 'weekly'
    queue_position INTEGER,            -- Position in job queue
    autostart_enabled BOOLEAN,         -- Auto-start on app startup
    -- Advanced scraping settings
    sites TEXT,                        -- JSON array of sites for multi-site scraping
    search_terms TEXT,                  -- Comma-separated search terms
    exclude_terms TEXT,                 -- Comma-separated exclude terms
    min_pages INTEGER,                 -- Minimum pages to crawl
    max_pages INTEGER,                  -- Maximum pages to crawl
    min_file_size_mb REAL,              -- Minimum file size filter
    max_file_size_mb REAL,              -- Maximum file size filter
    follow_links BOOLEAN,              -- Follow links on pages
    max_depth INTEGER,                  -- Maximum crawl depth
    extract_directories BOOLEAN,        -- Extract from PDF directories
    file_extensions TEXT,               -- File extensions to find
    equipment_type TEXT,
    manufacturer TEXT,
    created_at DATETIME,
    updated_at DATETIME,
    started_at DATETIME,
    completed_at DATETIME
);
```

#### EtsyListing Table
```sql
CREATE TABLE etsy_listings (
    id INTEGER PRIMARY KEY,
    manual_id INTEGER,                 -- Associated manual
    listing_id INTEGER,                -- Etsy listing ID (if created via API)
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    price REAL NOT NULL,
    quantity INTEGER DEFAULT 1,
    status TEXT,                       -- 'draft', 'active', 'inactive', 'sold_out'
    etsy_file_id INTEGER,              -- Etsy file ID (if uploaded via API)
    created_at DATETIME,
    updated_at DATETIME
);
```

#### ScrapedSite Table
```sql
CREATE TABLE scraped_sites (
    id INTEGER PRIMARY KEY,
    url TEXT NOT NULL UNIQUE,          -- Site URL/domain
    domain TEXT NOT NULL,
    first_scraped_at DATETIME,
    last_scraped_at DATETIME,
    scrape_count INTEGER DEFAULT 1,    -- Number of times scraped
    status TEXT,                       -- 'active', 'exhausted', 'blocked'
    notes TEXT
);
```

#### ProcessingLog Table
```sql
CREATE TABLE processing_logs (
    id INTEGER PRIMARY KEY,
    manual_id INTEGER,
    stage TEXT,                        -- 'scrape', 'download', 'process', 'list'
    status TEXT,                       -- 'started', 'completed', 'failed'
    message TEXT,
    created_at DATETIME
);
```

---

## Important Function Explanations

### Multi-Site Scraper

The **Multi-Site Scraper** ([`app/scrapers/multi_site_scraper.py`](app/scrapers/multi_site_scraper.py)) is the most powerful scraping component, capable of crawling multiple websites concurrently with advanced filtering and directory traversal capabilities.

#### Key Features

1. **Concurrent Crawling**: Uses ThreadPoolExecutor to crawl multiple sites simultaneously
2. **Directory Traversal**: Can follow links and traverse directories to find PDFs
3. **Smart Filtering**: Search term matching, exclude term filtering, file size limits
4. **Duplicate Prevention**: Tracks saved URLs within session and across database
5. **Immediate Persistence**: Saves discovered PDFs to database immediately upon discovery
6. **Job Tracking**: Associates discovered manuals with specific scrape jobs

#### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `sites` | List[str] | [] | List of base URLs to crawl |
| `search_terms` | List[str] | [] | Terms that must be present in URL/title |
| `exclude_terms` | List[str] | ['preview', 'operator', ...] | Terms to exclude (default filters non-service manuals) |
| `min_pages` | int | 5 | Minimum number of pages to crawl per site |
| `max_pages` | int | None | Maximum pages to crawl per site (unlimited if None) |
| `min_file_size_mb` | float | None | Minimum PDF file size |
| `max_file_size_mb` | float | None | Maximum PDF file size |
| `follow_links` | bool | True | Whether to follow links on discovered pages |
| `max_depth` | int | 2 | Maximum crawl depth from base URL |
| `extract_directories` | bool | True | Extract from directories containing multiple PDFs |
| `file_extensions` | List[str] | ['pdf'] | File extensions to search for |
| `skip_duplicates` | bool | True | Skip URLs already in database |
| `save_immediately` | bool | True | Save to DB immediately upon discovery |
| `job_id` | int | None | Associated scrape job ID |

#### Core Methods

##### `scrape_sites(sites: List[str], log_callback: Callable = None) -> Dict`

Main entry point for multi-site scraping.

**Process Flow:**
1. Validates and normalizes input sites
2. Creates ThreadPoolExecutor for concurrent crawling
3. For each site:
   - Fetches the page
   - Extracts PDF links
   - Follows links if enabled (up to max_depth)
   - Checks for PDF directories (3+ PDFs on a page)
   - Validates against search/exclude terms
   - Checks file size limits
   - Saves to database immediately if valid
4. Returns summary statistics

**Returns:**
```python
{
    'total_found': 100,           # Total PDFs found
    'new_saved': 50,              # New PDFs saved to database
    'duplicates_skipped': 40,     # Already in database
    'filtered_out': 10,           # Filtered by terms/size
    'sites_scraped': 5,           # Number of sites processed
    'errors': []                  # List of any errors
}
```

##### `_crawl_site(base_url: str, log_callback: Callable = None) -> List[PDFResult]`

Crawls a single site and returns discovered PDFs.

**Process:**
1. Fetches base URL
2. Extracts all links from the page
3. For each link:
   - Checks if it's a direct PDF link
   - If not a PDF and follow_links is enabled, recursively crawls
   - Validates against search/exclude terms
   - Checks file size if URL is a direct link
4. Returns list of valid PDFResult objects

##### `_extract_pdf_links(html: str, base_url: str) -> List[Dict]`

Extracts PDF links from HTML content.

**Returns list of:**
```python
{
    'url': str,           # Full PDF URL
    'title': str,          # Link text/title
    'is_directory': bool   # Whether this is a directory page
}
```

##### `_is_pdf_directory(url: str, html: str) -> bool`

Detects if a page is a PDF directory (contains 3+ PDF links).

This is useful for identifying pages that serve as repositories of manuals.

##### `_save_pdf_to_database(result: PDFResult, log_callback: Callable = None) -> bool`

Saves a discovered PDF to the database immediately.

**Process:**
1. Checks if URL already saved in current session
2. Checks if URL exists in database
3. Creates Manual record with status='pending'
4. Updates or creates ScrapedSite record
5. Returns True if saved, False if duplicate

#### Usage Example

```python
from app.scrapers.multi_site_scraper import MultiSiteScraper

# Configure scraper
config = {
    'sites': [
        'https://example-manuals.com/atv',
        'https://another-site.com/lawnmowers'
    ],
    'search_terms': ['service', 'repair', 'workshop'],
    'exclude_terms': ['preview', 'operator', 'quick start'],
    'min_file_size_mb': 0.5,
    'max_file_size_mb': 50,
    'follow_links': True,
    'max_depth': 2,
    'job_id': 123
}

scraper = MultiSiteScraper(config)
results = scraper.scrape_sites(config['sites'], log_callback=print)

print(f"Found {results['total_found']} PDFs")
print(f"Saved {results['new_saved']} new manuals")
```

#### Key Design Decisions

1. **Immediate Persistence**: PDFs are saved to database immediately upon discovery to prevent data loss if scraping is interrupted
2. **Session-level Deduplication**: Tracks saved URLs in memory to avoid duplicate database queries within the same scrape
3. **ThreadPoolExecutor**: Uses thread pool for concurrent crawling rather than asyncio to simplify HTTP requests with requests library
4. **Directory Detection**: Automatically identifies and prioritizes pages with multiple PDFs (directories)
5. **Job Association**: Each discovered manual is associated with the scrape job that created it for tracking

---

### PDF Processing Pipeline

The **PDF Processing Pipeline** ([`app/processors/pdf_processor.py`](app/processors/pdf_processor.py)) handles all PDF-related operations including metadata extraction, text extraction, and image generation.

#### Core Components

##### `PDFProcessor` Class

Main class for PDF processing operations.

**Key Methods:**

1. **`extract_metadata(pdf_path: str) -> Dict`**
   - Extracts PDF metadata (title, author, subject, keywords)
   - Parses manufacturer, model, year from title
   - Returns page count
   - Uses PyPDF2 for metadata extraction

2. **`extract_text(pdf_path: str, max_pages: int = 10) -> str`**
   - Extracts text content from PDF
   - Uses pdfplumber for better text extraction
   - Limits pages to process (for large PDFs)
   - Returns concatenated text

3. **`generate_images(pdf_path: str) -> List[str]`**
   - Converts PDF pages to images
   - Generates main image from page 1
   - Generates additional images from configured pages
   - Returns list of image file paths
   - Uses PyPDF2 + Pillow for conversion

4. **`validate_pdf(pdf_path: str) -> bool`**
   - Checks if file is a valid PDF
   - Verifies file can be opened and read
   - Checks file size against limits

#### Processing Flow

```
Downloaded PDF
       │
       ▼
┌──────────────┐
│ validate_pdf │
└──────────────┘
       │
       ▼
┌──────────────┐
│extract_metadata│
└──────────────┘
       │
       ├──────────────────────────┐
       ▼                          ▼
┌──────────────┐         ┌──────────────┐
│extract_text  │         │generate_images│
└──────────────┘         └──────────────┘
       │                          │
       ▼                          ▼
  Text Content              Image Files
       │                          │
       └──────────────────────────┘
                    │
                    ▼
         ┌──────────────────┐
         │ AI Processing    │
         │ (if configured)  │
         └──────────────────┘
                    │
                    ▼
         ┌──────────────────┐
         │ Listing Data     │
         └──────────────────┘
```

#### Configuration

Settings are loaded from [`app/config.py`](app/config.py):

```python
image_dpi: int = 150              # Image resolution
image_format: str = "jpeg"       # Image format (jpeg, png)
main_image_page: int = 1          # Page for main listing image
additional_image_pages: str = "2, 3, 4"  # Additional pages to convert
max_pdf_size_mb: int = 50        # Maximum PDF file size
```

---

### AI-Based Metadata Extraction

The **AI Metadata Extractor** ([`app/processors/pdf_ai_extractor.py`](app/processors/pdf_ai_extractor.py)) uses Groq's free Llama 3.3 API to intelligently extract metadata from PDF content.

#### Key Features

1. **Free API**: Uses Groq's free tier (no cost)
2. **Smart Extraction**: Extracts manufacturer, model, year, title from PDF text
3. **Fallback Handling**: Gracefully handles API failures
4. **Configurable**: Can limit pages and characters analyzed

#### Core Methods

##### `extract_from_pdf(pdf_path: str, max_pages: int = 3, max_chars_per_page: int = 3000) -> Dict`

Main extraction method.

**Process:**
1. Extracts text from first N pages of PDF
2. Sends text to Groq API with structured prompt
3. Parses JSON response to extract metadata
4. Returns extracted data

**Returns:**
```python
{
    'manufacturer': 'Honda',      # Extracted manufacturer
    'model': 'TRX420',            # Extracted model
    'year': '2010',               # Extracted year
    'title': 'Honda TRX420 Service Manual',  # Full title
    'success': True,              # Whether extraction succeeded
    'error': None                 # Error message if failed
}
```

##### `_extract_metadata_with_ai(text_content: str) -> Dict`

Sends text to Groq API and parses response.

**Prompt Structure:**
```
Extract the following information from this PDF manual text:
- manufacturer: The equipment manufacturer
- model: The model number/name
- year: The year (4 digits)
- title: A descriptive title

Return as JSON with keys: manufacturer, model, year, title
```

#### Configuration

```python
api_key: str = os.getenv('GROQ_API_KEY')  # Groq API key
api_url: str = "https://api.groq.com/openai/v1/chat/completions"
model: str = "llama-3.3-70b-versatile"   # Free tier model
timeout: int = 30
```

---

### Listing Content Generation

The **Listing Content Generator** ([`app/processors/listing_generator.py`](app/processors/listing_generator.py)) creates SEO-optimized Etsy listing content using AI.

#### Key Features

1. **SEO-Optimized Titles**: Creates titles optimized for Etsy search
2. **Detailed Descriptions**: Generates comprehensive descriptions
3. **Relevant Tags**: Suggests tags for better discoverability
4. **AI-Powered**: Uses Groq API for content generation

#### Core Methods

##### `generate_all_content(pdf_path: str, metadata: Dict, max_pages: int = 10, max_chars_per_page: int = 5000) -> Dict`

Generates all listing content in one call.

**Process:**
1. Extracts text from PDF
2. Generates SEO-optimized title
3. Generates detailed description
4. Generates relevant tags
5. Returns all content

**Returns:**
```python
{
    'seo_title': '2010 Honda TRX420 Rancher Service Manual PDF Download',
    'description': 'Complete service manual for 2010 Honda TRX420...',
    'tags': ['honda', 'trx420', 'service manual', 'repair', 'atv'],
    'success': True,
    'error': None
}
```

##### `_generate_seo_title(text_content: str, metadata: Dict) -> str`

Generates SEO-optimized title.

**Prompt Structure:**
```
Create an SEO-optimized Etsy listing title for this manual.
Include: manufacturer, model, year, type of manual.
Keep it under 140 characters.
Focus on keywords people would search for.
```

##### `_generate_description(text_content: str, metadata: Dict) -> str`

Generates detailed description.

**Prompt Structure:**
```
Create a detailed Etsy listing description for this manual.
Include:
- What this manual covers
- Who needs this manual
- Key features/sections
- File format and size
- Any important notes
```

##### `_generate_tags(text_content: str, metadata: Dict) -> List[str]`

Generates relevant tags.

**Prompt Structure:**
```
Generate 13 Etsy tags for this manual.
Tags should be relevant and searchable.
Return as comma-separated list.
```

---

### Processing Queue Manager

The **Processing Queue Manager** ([`app/processors/queue_manager.py`](app/processors/queue_manager.py)) manages the processing queue for manuals, allowing ordered processing of approved PDFs.

#### Key Features

1. **Ordered Processing**: Manuals are processed in queue order
2. **Position Management**: Can move items up/down in queue
3. **Automatic Repositioning**: Automatically repositions items after removal
4. **State Tracking**: Tracks processing state (queued, downloading, processing, completed, failed)

#### Core Methods

##### `add_to_queue(manual_id: int) -> int`

Adds a manual to the processing queue.

**Process:**
1. Finds the manual by ID
2. Determines next queue position
3. Sets queue_position and processing_state
4. Returns assigned position

##### `remove_from_queue(manual_id: int) -> None`

Removes a manual from the queue.

**Process:**
1. Finds the manual by ID
2. Clears queue position and processing state
3. Repositions all items after the removed one

##### `get_queue() -> List[Manual]`

Returns all manuals in queue, ordered by position.

##### `move_in_queue(manual_id: int, new_position: int) -> None`

Moves a manual to a new position in the queue.

**Process:**
1. Finds the manual
2. Adjusts positions of other items
3. Sets new position

#### Queue States

| State | Description |
|-------|-------------|
| `queued` | Manual is in queue, waiting to be processed |
| `downloading` | PDF is being downloaded |
| `processing` | PDF is being processed (text extraction, image generation) |
| `completed` | Processing completed successfully |
| `failed` | Processing failed (check error_message) |

---

### Scrape Job Management

The **Scrape Job Management** system ([`app/api/scrape_routes.py`](app/api/scrape_routes.py), [`app/tasks/jobs.py`](app/tasks/jobs.py)) manages scheduled and on-demand scraping jobs.

#### Key Features

1. **Job Queue**: Jobs can be queued and executed in order
2. **Scheduling**: Jobs can be scheduled for specific times
3. **Recurrence**: Jobs can run once, daily, or weekly
4. **Autostart**: Jobs can be configured to auto-start on app startup
5. **Advanced Configuration**: Full multi-site scraper configuration per job

#### Job Types

| Type | Description |
|------|-------------|
| `search` | Search engine scraping (Google/Bing/DuckDuckGo) |
| `forum` | Forum scraping |
| `manual_site` | Manual-specific site scraping |
| `multi_site` | Multi-site concurrent scraping |

#### Job Status Flow

```
queued → scheduled → running → completed
   ↓         ↓          ↓          ↓
   └─────────┴──────────┴──────────┴──→ failed
```

#### Core API Endpoints

##### `POST /api/scrape-jobs`

Create a new scrape job.

**Request Body:**
```json
{
    "name": "Honda ATV Manuals",
    "source_type": "multi_site",
    "sites": ["https://example.com/honda"],
    "search_terms": "honda,service,repair",
    "exclude_terms": "preview,operator",
    "max_results": 100,
    "equipment_type": "ATV",
    "manufacturer": "Honda",
    "autostart_enabled": true
}
```

##### `GET /api/scrape-jobs`

Get all scrape jobs with statistics.

##### `POST /api/scrape-jobs/{id}/start`

Start a queued job.

##### `POST /api/scrape-jobs/{id}/pause`

Pause a running job.

##### `POST /api/scrape-jobs/{id}/stop`

Stop a running job.

#### Celery Tasks

##### `run_multi_site_scraping_job(...)`

Main task for multi-site scraping.

**Parameters:**
- `sites`: List of URLs to scrape
- `search_terms`: Comma-separated search terms
- `exclude_terms`: Comma-separated exclude terms
- `min_pages`, `max_pages`: Page limits
- `min_file_size_mb`, `max_file_size_mb`: File size limits
- `follow_links`: Whether to follow links
- `max_depth`: Maximum crawl depth
- `extract_directories`: Extract from PDF directories
- `job_id`: Associated job ID

**Process:**
1. Creates MultiSiteScraper with configuration
2. Scrapes all sites concurrently
3. Saves discovered PDFs to database
4. Updates job status and statistics
5. Logs results

---

## Data Flow Summary

### Discovery Flow

```
User creates scrape job (Web UI)
       │
       ▼
POST /api/scrape-jobs
       │
       ▼
ScrapeJob created (status: queued)
       │
       ▼
Celery worker picks up job
       │
       ▼
run_multi_site_scraping_job()
       │
       ▼
MultiSiteScraper.scrape_sites()
       │
       ▼
Concurrent crawling of sites
       │
       ▼
PDF links discovered
       │
       ▼
_validate_pdf_link()
       │
       ├─→ Search terms match? ── No ──→ Discard
       │
       ├─→ Exclude terms match? ── Yes ──→ Discard
       │
       ├─→ File size in range? ── No ──→ Discard
       │
       └─→ All checks pass ──→ Save to database
                │
                ▼
Manual record created (status: pending)
```

### Approval Flow

```
User views pending manuals (Web UI)
       │
       ▼
GET /api/pending
       │
       ▼
List of pending manuals displayed
       │
       ▼
User approves/rejects
       │
       ▼
POST /api/pending/{id}/approve
or
POST /api/pending/{id}/reject
       │
       ▼
Manual status updated
```

### Download Flow

```
User clicks download (Web UI)
       │
       ▼
POST /api/manuals/{id}/download
       │
       ▼
Celery task: download_pdf()
       │
       ▼
PDFDownloader.download()
       │
       ▼
PDF saved to /data/pdfs/
       │
       ▼
Manual status: downloaded
```

### Processing Flow

```
User adds to processing queue (Web UI)
       │
       ▼
POST /api/manuals/{id}/queue
       │
       ▼
ProcessingQueueManager.add_to_queue()
       │
       ▼
Celery task: process_pdf()
       │
       ▼
┌─────────────────────────────────┐
│  PDFProcessor.extract_metadata  │
└─────────────────────────────────┘
       │
       ├─────────────────────────────────┐
       ▼                                 ▼
┌──────────────────┐          ┌──────────────────┐
│ extract_text     │          │ generate_images  │
└──────────────────┘          └──────────────────┘
       │                                 │
       ▼                                 ▼
┌──────────────────────────────────────────────────┐
│  PDFAIExtractor.extract_from_pdf() (optional)   │
└──────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────┐
│  ListingContentGenerator.generate_all_content()  │
└──────────────────────────────────────────────────┘
       │
       ▼
Manual status: processed
```

### Listing Flow

```
User creates listing (Web UI)
       │
       ▼
POST /api/files/listings
       │
       ▼
FileManager.create_listing()
       │
       ▼
Generate listing files:
  - listing.txt (title, description)
  - tags.txt (tags)
  - images/ (listing images)
  - pdf/ (PDF file)
       │
       ▼
Zip created: listing_{id}.zip
       │
       ▼
User downloads zip and uploads to Etsy
```

---

## Configuration Summary

### Environment Variables (`.env`)

```bash
# Application
APP_NAME=AutoLister
APP_VERSION=1.0.0
DEBUG=false

# Scraping
SCRAPING_INTERVAL_HOURS=6
MAX_RESULTS_PER_SEARCH=20
USER_AGENT=AutoLister/1.0
REQUEST_TIMEOUT=30

# Search APIs (Optional)
GOOGLE_API_KEY=
GOOGLE_CX=
BING_API_KEY=

# Groq API (for AI features)
GROQ_API_KEY=

# Etsy API (Optional - for direct listing)
ETSY_API_KEY=
ETSY_API_SECRET=
ETSY_ACCESS_TOKEN=
ETSY_ACCESS_TOKEN_SECRET=
ETSY_SHOP_ID=
ETSY_DEFAULT_PRICE=4.99
ETSY_DEFAULT_QUANTITY=9999

# Processing
MAX_PDF_SIZE_MB=50
IMAGE_DPI=150
IMAGE_FORMAT=jpeg
MAIN_IMAGE_PAGE=1
ADDITIONAL_IMAGE_PAGES=[2, 3, 4]

# Database
DATABASE_PATH=./data/autolister.db

# Dashboard
DASHBOARD_HOST=0.0.0.0
DASHBOARD_PORT=8000

# Redis/Celery
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Logging
LOG_LEVEL=INFO
LOG_FILE=./logs/autolister.log
```

### Search Terms Configuration (`config/search_terms.yaml`)

```yaml
equipment_categories:
  - name: ATVs
    brands: [Honda, Yamaha, Polaris, Suzuki, Kawasaki, Can-Am]
    types: [Sport, Utility, Side-by-Side]
  
  - name: Lawnmowers
    brands: [Toro, Craftsman, John Deere, Husqvarna]
    types: [Riding, Push, Zero-Turn]

search_terms:
  - service manual
  - repair manual
  - workshop manual
  - owner's manual

exclude_terms:
  - preview
  - operator
  - operation
  - user manual
  - quick start
```

---

## Deployment Considerations

### Raspberry Pi Deployment

- Use Docker Compose for easy deployment
- SQLite with WAL mode for better concurrency
- Redis for Celery task queue
- Monitor disk space for PDF storage

### Windows Deployment

- Run with `python -m uvicorn app.main:app --reload` for development
- Use Task Scheduler for automated scraping jobs
- Ensure proper file permissions for data directories

### Performance Tuning

- Adjust `max_pages` and `max_depth` for multi-site scraping
- Configure Celery worker concurrency based on system resources
- Use Redis persistence for queue durability
- Monitor database size and consider PostgreSQL for large deployments

---

## Future Enhancements

1. **Multi-language Support**: Add scraping and processing for non-English manuals
2. **Advanced AI Integration**: Use vision models for better image selection
3. **Auto-pricing**: Analyze market to suggest optimal prices
4. **Bulk Operations**: Batch approve, download, and process manuals
5. **Analytics Dashboard**: Track sales, views, and conversion rates
6. **Scheduler UI**: Visual scheduler for recurring jobs
7. **Proxy Support**: Add proxy rotation for scraping
8. **Rate Limiting**: Built-in rate limiting for API calls
