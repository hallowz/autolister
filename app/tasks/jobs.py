"""
Background job definitions for scraping and processing
"""
from typing import List, Optional, Dict, Callable
from app.database import SessionLocal, Manual, ProcessingLog, ScrapedSite
from app.scrapers import DuckDuckGoScraper, MultiSiteScraper
from app.processors import PDFDownloader, PDFProcessor, SummaryGenerator
from app.processors.listing_generator import ListingContentGenerator
from app.processors.queue_manager import ProcessingQueueManager
from app.etsy import ListingManager
from app.config import get_settings
import os
import zipfile
import re
import json
from datetime import datetime
from urllib.parse import urlparse

settings = get_settings()


def run_scraping_job(query: str = None, max_results: int = None, log_callback=None):
    """
    Run a scraping job to discover PDF manuals
    
    Args:
        query: Optional specific query to search for
        max_results: Optional maximum results per search
        log_callback: Optional callback function for logging
    """
    db = SessionLocal()
    
    # Helper function for logging
    def log(message):
        print(message)  # Still print to stdout for backward compatibility
        if log_callback:
            log_callback(message)
    
    try:
        # Get search queries
        from app.config import get_search_config
        search_config = get_search_config()
        
        queries = [query] if query else search_config.get_search_queries()
        max_results = max_results or settings.max_results_per_search
        
        log(f"Starting scraping job with {len(queries)} search queries")
        log(f"Max results per search: {max_results}")
        
        # Initialize scraper (only DuckDuckGo - free, no API key required)
        duckduckgo_scraper = DuckDuckGoScraper(settings.model_dump())
        
        total_discovered = 0
        
        for idx, search_query in enumerate(queries, 1):
            log(f"Searching for: {search_query} ({idx}/{len(queries)})")
            
            # Search using DuckDuckGo (free, no API key required)
            results = []
            try:
                ddg_results = duckduckgo_scraper.search(search_query)
                results.extend(ddg_results)
                log(f"Found {len(ddg_results)} results from DuckDuckGo")
            except Exception as e:
                log(f"DuckDuckGo scraper error: {e}")
            
            # Save results to database
            new_count = 0
            for result in results[:max_results]:
                # Check if URL already exists
                existing = db.query(Manual).filter(
                    Manual.source_url == result.url
                ).first()
                
                if not existing:
                    manual = Manual(
                        source_url=result.url,
                        source_type=result.source_type,
                        title=result.title,
                        equipment_type=result.equipment_type,
                        manufacturer=result.manufacturer,
                        model=result.model,
                        year=result.year,
                        status='pending'
                    )
                    db.add(manual)
                    total_discovered += 1
                    new_count += 1
            
            db.commit()
            log(f"Saved {new_count} new manuals from '{search_query}'")
        
        log(f"Scraping job completed. Discovered {total_discovered} new manuals total.")
        
        # Log completion
        log = ProcessingLog(
            stage='scrape',
            status='completed',
            message=f'Discovered {total_discovered} new manuals'
        )
        db.add(log)
        db.commit()
        
    except Exception as e:
        log(f"Scraping job error: {e}")
        
        # Log error
        log = ProcessingLog(
            stage='scrape',
            status='failed',
            message=str(e)
        )
        db.add(log)
        db.commit()
    
    finally:
        db.close()


def run_multi_site_scraping_job(
sites: List[str] = None,
search_terms: List[str] = None,
exclude_terms: List[str] = None,
min_pages: int = 5,
max_pages: int = None,
min_file_size_mb: float = None,
max_file_size_mb: float = None,
follow_links: bool = True,
max_depth: int = 2,
extract_directories: bool = True,
file_extensions: List[str] = None,
skip_duplicates: bool = True,
max_results: int = None,
log_callback: Callable = None
):
"""
Run a multi-site scraping job to discover PDF manuals

Args:
    sites: List of site URLs to scrape
    search_terms: List of search terms to match
    exclude_terms: List of terms to exclude
    min_pages: Minimum PDF page count
    max_pages: Maximum PDF page count
    min_file_size_mb: Minimum file size in MB
    max_file_size_mb: Maximum file size in MB
    follow_links: Whether to follow links on pages
    max_depth: Maximum link depth to follow
    extract_directories: Whether to extract PDFs from directories
    file_extensions: List of file extensions to look for
    skip_duplicates: Whether to skip duplicate URLs
    max_results: Maximum results per site
    log_callback: Optional callback function for logging
"""
db = SessionLocal()

# Helper function for logging
def log(message):
    print(message)  # Still print to stdout for backward compatibility
    if log_callback:
        log_callback(message)

try:
    # Default file extensions to PDF if not specified
    if file_extensions is None:
        file_extensions = ['pdf']
    
    # Default exclude terms for service manual scraping
    if exclude_terms is None:
        exclude_terms = ['preview', 'operator', 'operation', 'user manual', 'quick start']
    
    # Prepare scraper configuration
    scraper_config = {
        'user_agent': settings.user_agent,
        'timeout': settings.request_timeout,
        'max_results': max_results or settings.max_results_per_search,
        'sites': sites,
        'search_terms': ','.join(search_terms) if search_terms else '',
        'exclude_terms': ','.join(exclude_terms) if exclude_terms else '',
        'min_pages': min_pages,
        'max_pages': max_pages,
        'min_file_size_mb': min_file_size_mb,
        'max_file_size_mb': max_file_size_mb,
        'follow_links': follow_links,
        'max_depth': max_depth,
        'extract_directories': extract_directories,
        'file_extensions': ','.join(file_extensions),
        'skip_duplicates': skip_duplicates,
    }
    
    log(f"Starting multi-site scraping job")
    log(f"Sites to scrape: {len(sites) if sites else 0}")
    if sites:
        for site in sites[:5]:  # Show first 5 sites
            log(f"  - {site}")
        if len(sites) > 5:
            log(f"  ... and {len(sites) - 5} more")
    log(f"Search terms: {', '.join(search_terms) if search_terms else 'None'}")
    log(f"Exclude terms: {', '.join(exclude_terms) if exclude_terms else 'None'}")
    log(f"Max depth: {max_depth}, Follow links: {follow_links}")
    
    # Initialize multi-site scraper
    multi_site_scraper = MultiSiteScraper(scraper_config)
    
    total_discovered = 0
    total_skipped = 0
    
    # Run the scraper
    results = multi_site_scraper.search(log_callback=log)
    
    # Save results to database
    new_count = 0
    for result in results[:max_results] if max_results else results:
        # Check if URL already exists
        existing = db.query(Manual).filter(
            Manual.source_url == result.url
        ).first()
        
        if existing:
            total_skipped += 1
            continue
        
        # Extract domain for tracking
        parsed_url = urlparse(result.url)
        domain = parsed_url.netloc
        
        # Track scraped site
        scraped_site = db.query(ScrapedSite).filter(
            ScrapedSite.url == domain
        ).first()
        
        if scraped_site:
            scraped_site.last_scraped_at = datetime.utcnow()
            scraped_site.scrape_count += 1
        else:
            scraped_site = ScrapedSite(
                url=domain,
                domain=domain,
                status='active'
            )
            db.add(scraped_site)
        
        # Create manual record
        manual = Manual(
            source_url=result.url,
            source_type=result.source_type,
            title=result.title,
            equipment_type=result.equipment_type,
            manufacturer=result.manufacturer,
            model=result.model,
            year=result.year,
            status='pending'
        )
        db.add(manual)
        total_discovered += 1
        new_count += 1
    
    db.commit()
    log(f"Saved {new_count} new manuals from multi-site scraping")
    log(f"Skipped {total_skipped} duplicate URLs")
    log(f"Multi-site scraping job completed. Discovered {total_discovered} new manuals total.")
    
    # Log completion
    processing_log = ProcessingLog(
        stage='scrape',
        status='completed',
        message=f'Discovered {total_discovered} new manuals from {len(sites) if sites else 0} sites'
    )
    db.add(processing_log)
    db.commit()
    
except Exception as e:
    log(f"Multi-site scraping job error: {e}")
    
    # Log error
    processing_log = ProcessingLog(
        stage='scrape',
        status='failed',
        message=str(e)
    )
    db.add(processing_log)
    db.commit()

finally:
    db.close()


def process_approved_manuals():
    """
    Process all approved manuals (download and process PDFs)
    """
    db = SessionLocal()
    
    try:
        # Get all approved manuals
        approved_manuals = db.query(Manual).filter(
            Manual.status == 'approved'
        ).all()
        
        downloader = PDFDownloader()
        processor = PDFProcessor()
        
        for manual in approved_manuals:
            try:
                # Download PDF
                print(f"[process_approved_manuals] Processing manual_id={manual.id}")
                print(f"[process_approved_manuals] Manual details:")
                print(f"  source_url: {manual.source_url}")
                print(f"  title: {manual.title}")
                print(f"  manufacturer: {manual.manufacturer}")
                print(f"  model: {manual.model}")
                print(f"  year: {manual.year}")
                pdf_path = downloader.download(
                    manual.source_url,
                    manual.id,
                    manufacturer=manual.manufacturer,
                    model=manual.model,
                    year=manual.year
                )
                
                if not pdf_path:
                    manual.status = 'error'
                    manual.error_message = 'Failed to download PDF'
                    db.commit()
                    continue
                
                # Update manual
                manual.status = 'downloaded'
                manual.pdf_path = pdf_path
                db.commit()
                
                # Process PDF
                pdf_metadata = processor.extract_metadata(pdf_path)
                text = processor.extract_first_page_text(pdf_path)
                images = processor.generate_listing_images(
                    pdf_path,
                    manual.id,
                    manufacturer=manual.manufacturer,
                    model=manual.model,
                    year=manual.year
                )
                
                # Update manual with processed data
                if not manual.title:
                    summary_gen = SummaryGenerator()
                    manual.title = summary_gen.generate_title(
                        {**pdf_metadata, 'manufacturer': manual.manufacturer, 'model': manual.model},
                        text
                    )
                
                manual.status = 'processed'
                db.commit()
                
                print(f"Processed manual {manual.id}: {manual.title}")
            
            except Exception as e:
                print(f"Error processing manual {manual.id}: {e}")
                manual.status = 'error'
                manual.error_message = str(e)
                db.commit()
        
        # Log completion
        log = ProcessingLog(
            stage='download',
            status='completed',
            message=f'Processed {len(approved_manuals)} manuals'
        )
        db.add(log)
        db.commit()
    
    except Exception as e:
        print(f"Processing job error: {e}")
        
        log = ProcessingLog(
            stage='download',
            status='failed',
            message=str(e)
        )
        db.add(log)
        db.commit()
    
    finally:
        db.close()


def create_etsy_listings():
    """
    Create Etsy listings for all processed manuals
    """
    db = SessionLocal()
    
    try:
        # Get all processed manuals that haven't been listed
        processed_manuals = db.query(Manual).filter(
            Manual.status == 'processed'
        ).all()
        
        listing_manager = ListingManager()
        processor = PDFProcessor()
        
        for manual in processed_manuals:
            try:
                # Use pre-generated title, description, and tags if available
                title = manual.title
                description = manual.description
                tags = manual.tags.split(',') if manual.tags else None
                
                # If no pre-generated content, generate it now
                if not title or not description:
                    print(f"Generating listing content for manual {manual.id}")
                    listing_gen = ListingContentGenerator()
                    
                    # Extract metadata
                    pdf_metadata = processor.extract_metadata(manual.pdf_path)
                    page_count = processor.get_page_count(manual.pdf_path)
                    
                    # Prepare metadata for listing generator
                    listing_metadata = {
                        'manufacturer': manual.manufacturer or pdf_metadata.get('manufacturer'),
                        'model': manual.model or pdf_metadata.get('model'),
                        'year': manual.year or pdf_metadata.get('year'),
                        'title': manual.title or pdf_metadata.get('title'),
                        'page_count': page_count
                    }
                    
                    # Generate listing content
                    listing_content = listing_gen.generate_all_content(
                        manual.pdf_path,
                        listing_metadata
                    )
                    
                    if listing_content['success']:
                        title = listing_content['seo_title']
                        description = listing_content['description']
                        tags = listing_content['tags']
                        
                        # Update manual with generated content
                        manual.title = title
                        manual.description = description
                        manual.tags = ','.join(tags) if tags else None
                        db.commit()
                
                # Generate images
                images = processor.generate_listing_images(
                    manual.pdf_path,
                    manual.id,
                    manufacturer=manual.manufacturer,
                    model=manual.model,
                    year=manual.year
                )
                
                # Create Etsy listing with tags
                listing_id = listing_manager.create_digital_listing(
                    title=title,
                    description=description,
                    pdf_path=manual.pdf_path,
                    image_paths=images['main'] + images['additional'],
                    price=settings.etsy_default_price,
                    tags=tags
                )
                
                if listing_id:
                    # Create listing record
                    from app.database import EtsyListing
                    etsy_listing = EtsyListing(
                        manual_id=manual.id,
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
                    
                    print(f"Created Etsy listing {listing_id} for manual {manual.id}")
                else:
                    print(f"Failed to create Etsy listing for manual {manual.id}")
            
            except Exception as e:
                print(f"Error creating listing for manual {manual.id}: {e}")
                manual.status = 'error'
                manual.error_message = str(e)
                db.commit()
        
        # Log completion
        log = ProcessingLog(
            stage='list',
            status='completed',
            message=f'Created listings for {len(processed_manuals)} manuals'
        )
        db.add(log)
        db.commit()
    
    except Exception as e:
        print(f"Listing job error: {e}")
        
        log = ProcessingLog(
            stage='list',
            status='failed',
            message=str(e)
        )
        db.add(log)
        db.commit()
    
    finally:
        db.close()


def process_single_manual(manual_id: int, log_callback=None) -> bool:
    """
    Process a single manual from the queue, generating resources during processing
    
    Args:
        manual_id: ID of the manual to process
        log_callback: Optional callback function for logging
        
    Returns:
        True if processing succeeded, False otherwise
    """
    db = SessionLocal()
    
    def log(message):
        print(message)
        if log_callback:
            log_callback(message)
    
    try:
        queue_manager = ProcessingQueueManager(db)
        manual = db.query(Manual).filter(Manual.id == manual_id).first()
        
        if not manual:
            log(f"Manual {manual_id} not found")
            return False
        
        # Set state to downloading
        queue_manager.set_processing_state(manual_id, 'downloading')
        log(f"Downloading manual {manual_id}: {manual.title or 'Untitled'}")
        
        downloader = PDFDownloader()
        processor = PDFProcessor()
        listing_gen = ListingContentGenerator()
        
        # Download PDF
        print(f"[process_single_manual] Processing manual_id={manual_id}")
        print(f"[process_single_manual] Manual details:")
        print(f"  source_url: {manual.source_url}")
        print(f"  title: {manual.title}")
        print(f"  manufacturer: {manual.manufacturer}")
        print(f"  model: {manual.model}")
        print(f"  year: {manual.year}")
        pdf_path = downloader.download(
            manual.source_url,
            manual.id,
            manufacturer=manual.manufacturer,
            model=manual.model,
            year=manual.year
        )
        
        if not pdf_path:
            log(f"Failed to download PDF for manual {manual_id}")
            queue_manager.mark_processing_complete(manual_id, success=False)
            return False
        
        # Update manual with PDF path
        manual.pdf_path = pdf_path
        db.commit()
        
        # Set state to processing
        queue_manager.set_processing_state(manual_id, 'processing')
        log(f"Processing manual {manual_id}")
        
        # Extract metadata
        pdf_metadata = processor.extract_metadata(pdf_path)
        text = processor.extract_first_page_text(pdf_path)
        page_count = processor.get_page_count(pdf_path)
        
        # Extract model_number from model if available
        model_number = None
        if manual.model:
            number_match = re.search(r'\d+', manual.model)
            if number_match:
                model_number = number_match.group()
        
        # Generate images
        log(f"Generating images for manual {manual_id}")
        images = processor.generate_listing_images(
            pdf_path,
            manual.id,
            manufacturer=manual.manufacturer,
            model=manual.model,
            model_number=model_number,
            year=manual.year
        )
        
        # Generate listing content using AI
        log(f"Generating listing content for manual {manual_id}")
        
        # Prepare metadata for listing generator
        listing_metadata = {
            'manufacturer': manual.manufacturer or pdf_metadata.get('manufacturer'),
            'model': manual.model or pdf_metadata.get('model'),
            'year': manual.year or pdf_metadata.get('year'),
            'title': manual.title or pdf_metadata.get('title'),
            'page_count': page_count
        }
        
        # Generate listing content
        listing_content = listing_gen.generate_all_content(
            pdf_path,
            listing_metadata
        )
        
        if listing_content['success']:
            seo_title = listing_content['seo_title']
            description = listing_content['description']
            tags = listing_content['tags']
            
            # Update manual with processed data
            if not manual.title:
                manual.title = seo_title
            manual.description = description
            manual.tags = ','.join(tags) if tags else None
            db.commit()
            
            log(f"Generated SEO title: {seo_title[:50]}...")
            log(f"Generated {len(tags)} tags")
        else:
            log(f"Warning: AI listing generation failed: {listing_content['error']}")
            # Fallback to old method
            summary_gen = SummaryGenerator()
            seo_title = summary_gen.generate_title(
                {**pdf_metadata, 'manufacturer': manual.manufacturer, 'model': manual.model},
                text
            )
            description = summary_gen.generate_description(
                {**pdf_metadata, 'manufacturer': manual.manufacturer, 'model': manual.model},
                text,
                page_count
            )
            
            if not manual.title:
                manual.title = seo_title
            manual.description = description
            db.commit()
        
        title = manual.title
        description = manual.description
        tags = manual.tags.split(',') if manual.tags else []
        
        # Generate resources zip file
        log(f"Generating resources zip for manual {manual_id}")
        
        # Clean up any old zip files with incorrect names for this manual
        import os
        import glob
        old_zips = glob.glob(f"./data/manual_{manual_id}_*.zip")
        for old_zip in old_zips:
            try:
                os.remove(old_zip)
                log(f"Removed old zip file: {old_zip}")
            except Exception as e:
                log(f"Failed to remove old zip file {old_zip}: {e}")
        
        resources_zip_path = generate_resources_zip(
            manual, pdf_metadata, text, page_count, images, title, description, tags
        )
        
        # Mark as complete
        queue_manager.mark_processing_complete(manual_id, success=True, resources_zip_path=resources_zip_path)
        log(f"Successfully processed manual {manual_id}: {manual.title}")
        
        return True
        
    except Exception as e:
        log(f"Error processing manual {manual_id}: {e}")
        try:
            queue_manager = ProcessingQueueManager(db)
            queue_manager.mark_processing_complete(manual_id, success=False)
        except:
            pass
        return False
    
    finally:
        db.close()


def generate_resources_zip(manual: Manual, pdf_metadata: dict, text: str,
                          page_count: int, images: dict, title: str,
                          description: str, tags: list = None) -> str:
    """
    Generate a resources zip file for a manual
    
    Args:
        manual: Manual object
        pdf_metadata: PDF metadata
        text: Extracted text
        page_count: Number of pages
        images: Generated images dict
        title: Generated title
        description: Generated description
        tags: List of tags
        
    Returns:
        Path to the generated zip file
    """
    import re
    from app.utils import generate_safe_filename, parse_make_model_modelnumber
    
    print(f"[generate_resources_zip] Input metadata:")
    print(f"  manual.model: {manual.model}")
    print(f"  manual.year: {manual.year}")
    print(f"  manual.manufacturer: {manual.manufacturer}")
    print(f"  pdf_metadata: {pdf_metadata}")
    
    # Use PDF metadata for model/year if not in manual record
    pdf_model = manual.model or pdf_metadata.get('model')
    pdf_year = manual.year or pdf_metadata.get('year')
    pdf_manufacturer = manual.manufacturer or pdf_metadata.get('manufacturer')
    
    # If pdf_model looks like a filename (contains .pdf), extract from it
    if pdf_model and '.pdf' in pdf_model:
        print(f"[generate_resources_zip] pdf_model looks like a filename, extracting model from it")
        parsed = parse_make_model_modelnumber(pdf_model, pdf_manufacturer)
        if parsed.get('model'):
            pdf_model = parsed['model']
            print(f"[generate_resources_zip] Extracted model from filename: {pdf_model}")
        if not pdf_manufacturer and parsed.get('make'):
            pdf_manufacturer = parsed['make']
            print(f"[generate_resources_zip] Extracted manufacturer from filename: {pdf_manufacturer}")
    
    # Extract model_number from model if available
    model_number = None
    if pdf_model:
        number_match = re.search(r'\d+', pdf_model)
        if number_match:
            model_number = number_match.group()
    
    # If we don't have good metadata, try to extract from PDF filename
    if not pdf_model or not pdf_manufacturer:
        pdf_filename = os.path.basename(manual.pdf_path)
        # Remove hash suffix if present (e.g., _2a126931)
        pdf_filename = re.sub(r'_[a-f0-9]{8}\.pdf$', '.pdf', pdf_filename, flags=re.IGNORECASE)
        parsed_from_filename = parse_make_model_modelnumber(pdf_filename)
        if not pdf_manufacturer and parsed_from_filename.get('make'):
            pdf_manufacturer = parsed_from_filename['make']
        if not pdf_model and parsed_from_filename.get('model'):
            pdf_model = parsed_from_filename['model']
        if not model_number and parsed_from_filename.get('model_number'):
            model_number = parsed_from_filename['model_number']
    
    # Clean up model if it contains multiple models separated by commas
    if pdf_model and ',' in pdf_model:
        # Take only the first model from comma-separated list
        pdf_model = pdf_model.split(',')[0].strip()
    
    # Clean up manufacturer if it contains "Co., Ltd." or similar
    if pdf_manufacturer:
        pdf_manufacturer = re.sub(r'\s+(Co\.|Inc\.|Ltd\.|Corporation|LLC).*$', '', pdf_manufacturer, flags=re.IGNORECASE).strip()
    
    print(f"[generate_resources_zip] Final metadata for zip filename:")
    print(f"  manufacturer: {pdf_manufacturer}")
    print(f"  model: {pdf_model}")
    print(f"  year: {pdf_year}")
    print(f"  model_number: {model_number}")
    
    # Generate meaningful zip filename
    zip_name = generate_safe_filename(
        manufacturer=pdf_manufacturer,
        model=pdf_model,
        year=pdf_year,
        title=manual.title or os.path.basename(manual.pdf_path)
    )
    zip_path = f"./data/{zip_name}_resources.zip"
    
    # Generate the PDF filename with the same pattern as images
    pdf_filename_in_zip = f"{zip_name}.pdf"
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add PDF with meaningful filename
        if os.path.exists(manual.pdf_path):
            zipf.write(manual.pdf_path, pdf_filename_in_zip)
        
        # Add generated images
        all_images = images.get('main', []) + images.get('additional', [])
        valid_images = [img for img in all_images if img is not None and os.path.exists(img)]
        
        for image_path in valid_images:
            zipf.write(image_path, os.path.basename(image_path))
        
        # Generate image base name
        image_base_name = generate_safe_filename(
            manufacturer=manual.manufacturer,
            model=pdf_model,
            year=pdf_year,
            title=manual.title
        )
        
        # Generate unified listing data file (replaces README and description.txt)
        listing_data_content = f"""# Listing Data for: {title}

## SEO Title
{title}

## Description
{description}

## Tags
{', '.join(tags) if tags else 'No tags generated'}

## Manual Information
- Manufacturer: {manual.manufacturer or 'N/A'}
- Model: {manual.model or 'N/A'}
- Year: {manual.year or 'N/A'}
- Pages: {page_count}
- PDF File: `{pdf_filename_in_zip}`

## Files Included in This Package

### 1. PDF Manual
- File: `{pdf_filename_in_zip}`
- This is the digital file that buyers will download
- Fully searchable PDF format

### 2. Listing Images
Use these images for your Etsy listing:

**Main Image (First Image):**
- Use: `{image_base_name}.jpg` (or .png)
- This is the cover/title page of the manual

**Additional Images:**
- Upload the remaining images: `{image_base_name}_*.jpg` (or .png)
- These show sample pages including the index/table of contents
- Upload up to 5 images total (1 main + 4 additional)

## Etsy Listing Instructions

### Step 1: Upload the PDF
1. Go to your Etsy shop manager
2. Click "Add a listing"
3. Upload the PDF file: `{pdf_filename_in_zip}`
4. This will be the digital file buyers download

### Step 2: Upload Images
1. Upload the main image first
2. Then upload additional images in order
3. Use all provided images for best results

### Step 3: Set Title
Copy and paste the SEO title from above:
```
{title}
```

### Step 4: Set Description
Copy and paste the description from above:
```
{description}
```

### Step 5: Set Tags
Copy and paste the tags from above:
```
{', '.join(tags) if tags else 'No tags generated'}
```

### Step 6: Pricing & Quantity
- Price: $4.99 (or adjust as needed)
- Quantity: 9999 (unlimited digital downloads)

### Step 7: Category & Shipping
- Category: Choose the most relevant equipment category (ATV, Lawn Mower, Generator, etc.)
- Shipping: Set to "Digital Item" or "No shipping required"
- Buyers will receive an instant download link after purchase

## Tips for Success

- Use high-quality images (already provided)
- Make sure the title includes manufacturer and model
- Include all relevant keywords in tags
- Respond quickly to buyer questions
- Consider creating variations for different models

## Generated
{datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
"""
        
        zipf.writestr('LISTING_DATA.txt', listing_data_content)
    
    return zip_path


def process_queue(log_callback=None):
    """
    Process manuals from the queue one at a time
    
    Args:
        log_callback: Optional callback function for logging
    """
    db = SessionLocal()
    
    def log(message):
        print(message)
        if log_callback:
            log_callback(message)
    
    try:
        queue_manager = ProcessingQueueManager(db)
        
        while True:
            # Get next manual in queue
            manual = queue_manager.get_next_in_queue()
            
            if not manual:
                log("Queue is empty, no more manuals to process")
                break
            
            log(f"Processing manual {manual.id} from queue (position {manual.queue_position})")
            
            # Process the manual
            success = process_single_manual(manual.id, log_callback)
            
            if not success:
                log(f"Failed to process manual {manual.id}, continuing to next")
        
        log("Queue processing completed")
        
    except Exception as e:
        log(f"Queue processing error: {e}")
    finally:
        db.close()
