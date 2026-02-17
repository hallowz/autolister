# Multi-Site Scraping Implementation

## Overview
This document describes the implementation of multi-site scraping with directory traversal and PDF detection for AutoLister.

## Features Implemented

### 1. Multi-Site Scraper (`app/scrapers/multi_site_scraper.py`)
- **Concurrent Scraping**: Uses ThreadPoolExecutor to scrape multiple sites concurrently
- **Link Following**: Follows links on pages up to configurable depth (max_depth parameter)
- **Directory Traversal**: Detects and extracts PDFs from directories containing multiple PDFs
- **PDF Detection**: Identifies PDF files by extension and content type
- **Advanced Filtering**:
  - Search terms matching (search_terms parameter)
  - Exclude terms filtering (exclude_terms parameter)
  - File size filtering (min_file_size_mb, max_file_size_mb parameters)
  - Page count filtering (min_pages, max_pages parameters)
  - File extension filtering (file_extensions parameter)
  - Duplicate URL tracking and skipping (skip_duplicates parameter)
- **Default Configuration**: Pre-configured for service manual scraping:
  - Excludes: preview, operator, operation, user manual
  - Minimum pages: 5
  - Follows links: enabled
  - Extracts from directories: enabled
  - Skips duplicates: enabled

### 2. Database Schema Updates (`app/database.py`)
- **ScrapedSite Model**: Tracks which sites have been scraped to avoid duplicates
  - url: Unique URL of the site
  - domain: Domain name
  - first_scraped_at, last_scraped_at: Timestamps
  - scrape_count: Number of times scraped
  - status: 'active', 'exhausted', 'blocked'
  - notes: Additional notes

- **ScrapeJob Model**: Extended with advanced scraping settings
  - sites: JSON array of site URLs to scrape
  - search_terms: Comma-separated search terms
  - exclude_terms: Comma-separated terms to exclude
  - min_pages, max_pages: PDF page count filters
  - min_file_size_mb, max_file_size_mb: File size filters
  - follow_links: Whether to follow links on pages
  - max_depth: Maximum link depth to follow
  - extract_directories: Whether to extract PDFs from directories
  - file_extensions: Comma-separated file extensions to look for
  - skip_duplicates: Whether to skip duplicate URLs
  - notes: Additional notes for the job

### 3. Job Execution Updates (`app/tasks/jobs.py`)
- **run_multi_site_scraping_job()**: New function for multi-site scraping
  - Parses sites from JSON or newline-separated string
  - Configures MultiSiteScraper with advanced settings
  - Tracks scraped sites in ScrapedSite model
  - Supports progress tracking via log_callback
  - Filters results by search/exclude terms
  - Saves new manuals to database
  - Logs completion statistics

### 4. API Endpoints Updates (`app/api/scrape_routes.py`)
- **create_scrape_job()**: Updated to accept advanced scraping settings
  - Saves all advanced settings to ScrapeJob model
  - Supports multi_site source_type

- **run_scrape_job()**: Updated to handle multi-site scraping
  - Detects source_type and routes to appropriate scraper
  - For multi_site: Calls run_multi_site_scraping_job() with advanced settings
  - For other types: Calls run_scraping_job() with query
  - Parses sites from JSON or newline-separated format
  - Parses search/exclude terms from comma-separated format
  - Parses file extensions from comma-separated format

- **start_next_queued_job()**: Updated to support multi-site scraping
  - Same logic as run_scrape_job() for autostart

### 5. Pydantic Schemas Updates (`app/api/schemas.py`)
- **ScrapeJobCreate**: Extended with advanced scraping settings
  - sites: JSON array of site URLs to scrape
  - search_terms, exclude_terms: Comma-separated search/exclude terms
  - min_pages, max_pages: PDF page count filters
  - min_file_size_mb, max_file_size_mb: File size filters
  - follow_links, max_depth, extract_directories: Boolean settings
  - file_extensions: Comma-separated file extensions
  - skip_duplicates: Boolean setting
  - notes: Additional notes

- **ScrapeJobUpdate**: Same advanced settings for editing
- **ScrapeJobResponse**: Extended with advanced settings in response

### 6. UI Updates (`app/static/scrape-queue.html`)
- **Source Type Dropdown**: Added 'multi_site' option
  - onchange="toggleMultiSiteFields()" to show/hide relevant fields

- **Multi-Site Fields Section**: New section for multi-site configuration
  - Sites textarea (one URL per line)
  - File extensions input
  - Max link depth input
  - Follow links checkbox
  - Extract directories checkbox
  - Skip duplicates checkbox
  - Min/Max file size inputs

- **Regular Search Fields Section**: Wrapped in div for conditional display
  - Search query field (hidden for multi-site)
  - Traversal pattern field

- **AI Generated Source Type**: Added 'multi_site' option

- **Edit Modal**: Added 'multi_site' option to source type dropdown

### 7. JavaScript Updates (`app/static/js/scrape-queue.js`)
- **toggleMultiSiteFields()**: New function to show/hide multi-site fields
  - Shows multi-site fields when source_type is 'multi_site'
  - Shows regular search fields for other source types

- **createScrapeJob()**: Updated to handle multi-site scraping
  - Detects source_type and builds appropriate jobData
  - For multi_site:
    - Parses sites from newline-separated string
    - Converts to JSON array
    - Includes all advanced settings
  - For other types:
    - Uses search query
    - Includes basic advanced settings (search_terms, exclude_terms, min_pages, max_pages)
  - Validates required fields based on source_type

- **getSourceTypeLabel()**: Added 'multi_site' label

### 8. Database Migration (`migrations/add_multi_site_columns.py`)
- Creates all tables including scraped_sites
- Adds advanced scraping columns to scrape_jobs if they don't exist
- Columns added:
  - sites (TEXT)
  - search_terms (TEXT)
  - exclude_terms (TEXT)
  - min_pages (INTEGER, default 5)
  - max_pages (INTEGER)
  - min_file_size_mb (REAL)
  - max_file_size_mb (REAL)
  - follow_links (BOOLEAN, default 1)
  - max_depth (INTEGER, default 2)
  - extract_directories (BOOLEAN, default 1)
  - file_extensions (TEXT, default 'pdf')
  - skip_duplicates (BOOLEAN, default 1)
  - notes (TEXT)

## Usage

### Creating a Multi-Site Scrape Job

1. Navigate to Scrape Queue page
2. Click "New Scrape Job"
3. Select "Multi-Site Scraper" from Source Type dropdown
4. Enter sites to scrape (one URL per line):
   ```
   https://example.com/manuals
   https://another-site.com/documents
   https://manual-archive.com
   ```
5. Configure advanced settings:
   - Search Terms: service manual, repair manual (comma-separated)
   - Exclude Terms: preview, operator, user manual (comma-separated)
   - Min Pages: 5
   - Max Pages: (optional)
   - Min File Size (MB): (optional)
   - Max File Size (MB): (optional)
   - Max Link Depth: 2
   - Follow Links: (checked)
   - Extract Directories: (checked)
   - Skip Duplicates: (checked)
   - File Extensions: pdf
6. Set job name and schedule (optional)
7. Click "Create Job"

### Running the Job

The job will:
1. Scrape all sites concurrently (up to 5 at a time)
2. Follow links on each page up to max_depth
3. Detect PDF directories (pages with 3+ PDFs)
4. Filter results based on search/exclude terms
5. Filter by file size if specified
6. Skip duplicate URLs if enabled
7. Track scraped sites to avoid re-scraping
8. Update progress in real-time
9. Save discovered PDFs to database

### Default Configuration for Service Manual Scraping

The multi-site scraper is pre-configured for serious work:
- **Excludes**: preview, operator, operation, user manual, quick start
- **Minimum Pages**: 5
- **Follow Links**: Enabled
- **Extract Directories**: Enabled
- **Skip Duplicates**: Enabled

This configuration focuses on finding comprehensive service manuals while excluding preview documents and basic user guides.

## Files Modified

### New Files Created
- `app/scrapers/multi_site_scraper.py`: Multi-site scraper implementation
- `migrations/add_multi_site_columns.py`: Database migration script

### Files Modified
- `app/scrapers/__init__.py`: Added MultiSiteScraper export
- `app/database.py`: Fixed indentation, added ScrapedSite model, extended ScrapeJob model
- `app/tasks/jobs.py`: Added run_multi_site_scraping_job() function, imported ScrapedSite
- `app/api/scrape_routes.py`: Updated create_scrape_job() and run_scrape_job() to handle multi-site
- `app/api/schemas.py`: Already had advanced settings in ScrapeJobCreate/Update/Response
- `app/static/scrape-queue.html`: Added multi-site option, multi-site fields section
- `app/static/js/scrape-queue.js`: Added toggleMultiSiteFields(), updated createScrapeJob(), added multi_site label

## Testing

To test the implementation:

1. Run the migration: `python migrations/add_multi_site_columns.py`
2. Start the application: `python -m app.main`
3. Navigate to Scrape Queue page
4. Create a multi-site scrape job with sample sites
5. Run the job and monitor progress
6. Check the database for discovered manuals
7. Check the scraped_sites table for tracking

## Notes

- The multi-site scraper uses BeautifulSoup for HTML parsing
- Requests library for HTTP requests
- ThreadPoolExecutor for concurrent scraping (max 5 workers)
- URL normalization to avoid duplicates
- Domain-based filtering to stay on same site during traversal
- Progress tracking via log_callback for real-time updates
- ScrapedSite model tracks previously scraped domains
