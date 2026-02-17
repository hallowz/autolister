"""
Celery tasks for AutoLister
"""
from typing import List, Callable, Optional
from datetime import datetime
from urllib.parse import urlparse
from celery import shared_task

from app.database import SessionLocal, Manual, ScrapedSite, ProcessingLog, ScrapeJob
from app.config import get_settings
from app.scrapers.multi_site_scraper import MultiSiteScraper
from app.processors.pdf_handler import PDFDownloader
from app.processors.pdf_processor import PDFProcessor

settings = get_settings()


@shared_task(name="app.tasks.jobs.run_search_job")
def run_search_job(
    query: str,
    source_type: str = 'search',
    max_results: int = 100,
    equipment_type: str = None,
    manufacturer: str = None,
    job_id: int = None
):
    """
    Run a search job to discover PDF manuals
    
    Args:
        query: Search query string
        source_type: Type of source ('search', 'forum', 'manual_site', 'gdrive')
        max_results: Maximum number of results to return
        equipment_type: Equipment type filter
        manufacturer: Manufacturer filter
        job_id: ID of the scrape job creating these manuals
    """
    from app.scrapers.search_engine import SearchEngineScraper
    from app.scrapers.forums import ForumScraper
    from app.scrapers.manual_sites import ManualSiteScraper
    from app.scrapers.gdrive import GoogleDriveScraper
    
    db = SessionLocal()
    
    try:
        # Initialize appropriate scraper based on source type
        if source_type == 'search':
            scraper = SearchEngineScraper(settings)
        elif source_type == 'forum':
            scraper = ForumScraper(settings)
        elif source_type == 'manual_site':
            scraper = ManualSiteScraper(settings)
        elif source_type == 'gdrive':
            scraper = GoogleDriveScraper(settings)
        else:
            raise ValueError(f"Unknown source type: {source_type}")
        
        # Run scraper
        results = scraper.search(query, max_results=max_results)
        
        # Save results to database
        new_count = 0
        for result in results:
            # Check if URL already exists
            existing = db.query(Manual).filter(
                Manual.source_url == result.url
            ).first()
            
            if existing:
                continue
            
            # Create manual record
            manual = Manual(
                job_id=job_id,
                source_url=result.url,
                source_type=source_type,
                title=result.title,
                equipment_type=equipment_type,
                manufacturer=manufacturer,
                status='pending'
            )
            db.add(manual)
            new_count += 1
        
        db.commit()
        print(f"[run_search_job] Saved {new_count} new manuals")
        
    except Exception as e:
        print(f"[run_search_job] Error: {e}")
        db.rollback()
    finally:
        db.close()


@shared_task(name="app.tasks.jobs.run_multi_site_scraping_job")
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
    log_callback: Callable = None,
    job_id: int = None
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
        job_id: ID of the scrape job creating these manuals
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
            'save_immediately': True,  # Save PDFs to DB immediately upon discovery
            'job_id': job_id,  # Pass job_id to the scraper
        }
        
        log(f"Starting multi-site scraping job (PDFs will be saved to database immediately)")
        
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
        
        # Run scraper
        results = multi_site_scraper.search(log_callback=log)
        
        # Save results to database
        new_count = 0
        
        # First, collect all domains to track
        domains_to_track = set()
        for result in results[:max_results] if max_results else results:
            parsed_url = urlparse(result.url)
            domain = parsed_url.netloc
            domains_to_track.add(domain)
        
        # Update or create scraped sites (separate transaction to avoid conflicts)
        for domain in domains_to_track:
            scraped_site = db.query(ScrapedSite).filter(
                ScrapedSite.url == domain
            ).first()
            
            if scraped_site:
                scraped_site.last_scraped_at = datetime.utcnow()
                scraped_site.scrape_count += 1
            else:
                try:
                    scraped_site = ScrapedSite(
                        url=domain,
                        domain=domain,
                        status='active'
                    )
                    db.add(scraped_site)
                    db.flush()  # Flush to catch unique constraint errors early
                except Exception as e:
                    # If there's a duplicate constraint error, rollback and continue
                    db.rollback()
                    log(f"Warning: Could not track domain {domain}: {e}")
                    # Try to get the existing one
                    scraped_site = db.query(ScrapedSite).filter(
                        ScrapedSite.url == domain
                    ).first()
        
        # Commit scraped sites first to release locks
        db.commit()
        log(f"Updated {len(domains_to_track)} scraped sites")
        
        # Note: PDFs are already saved to database immediately by the scraper
        # So we just need to count them for the final summary
        total_discovered = 0
        total_skipped = 0
        
        for result in results[:max_results] if max_results else results:
            # Check if URL exists (it should, since it was saved immediately)
            existing = db.query(Manual).filter(
                Manual.source_url == result.url
            ).first()
            
            if existing:
                total_discovered += 1
            else:
                # This shouldn't happen if save_immediately is enabled, but handle it
                total_skipped += 1
        
        log(f"Multi-site scraping job completed. Discovered {total_discovered} new manuals total.")
        log(f"Note: PDFs were saved to database immediately upon discovery for real-time UI display")
        
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


@shared_task(name="app.tasks.jobs.process_approved_manuals")
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
                
                # Update manual with PDF path
                manual.pdf_path = pdf_path
                manual.status = 'processing'
                manual.processing_started_at = datetime.utcnow()
                db.commit()
                
                # Process PDF
                print(f"[process_approved_manuals] Processing PDF: {pdf_path}")
                processor.process_pdf(
                    manual.id,
                    pdf_path,
                    manufacturer=manual.manufacturer,
                    model=manual.model,
                    year=manual.year
                )
                
                # Update manual as processed
                manual.status = 'processed'
                manual.processing_completed_at = datetime.utcnow()
                db.commit()
                
            except Exception as e:
                print(f"[process_approved_manuals] Error processing manual_id={manual.id}: {e}")
                manual.status = 'error'
                manual.error_message = str(e)
                db.commit()
    
    except Exception as e:
        print(f"[process_approved_manuals] Error: {e}")
    finally:
        db.close()


@shared_task(name="app.tasks.jobs.list_manual_on_etsy")
def list_manual_on_etsy(manual_id: int):
    """
    List a manual on Etsy
    
    Args:
        manual_id: ID of the manual to list
    """
    from app.etsy.client import EtsyClient
    from app.etsy.listing import EtsyListingCreator
    
    db = SessionLocal()
    
    try:
        # Get manual
        manual = db.query(Manual).filter(Manual.id == manual_id).first()
        
        if not manual:
            print(f"[list_manual_on_etsy] Manual not found: {manual_id}")
            return
        
        if not manual.pdf_path:
            print(f"[list_manual_on_etsy] No PDF path for manual_id={manual_id}")
            return
        
        print(f"[list_manual_on_etsy] Listing manual_id={manual_id} on Etsy")
        print(f"  title: {manual.title}")
        print(f"  pdf_path: {manual.pdf_path}")
        
        # Initialize Etsy client
        etsy_client = EtsyClient(settings)
        listing_creator = EtsyListingCreator(etsy_client)
        
        # Create listing
        listing_id = listing_creator.create_listing(manual)
        
        if listing_id:
            manual.status = 'listed'
            db.commit()
            print(f"[list_manual_on_etsy] Successfully listed manual_id={manual_id} as listing_id={listing_id}")
        else:
            print(f"[list_manual_on_etsy] Failed to list manual_id={manual_id}")
            
    except Exception as e:
        print(f"[list_manual_on_etsy] Error: {e}")
        manual.status = 'error'
        manual.error_message = str(e)
        db.commit()
    finally:
        db.close()


@shared_task(name="app.tasks.jobs.check_queue")
def check_queue():
    """
    Check the queue and process next job
    """
    db = SessionLocal()
    
    try:
        # Get next job in queue
        job = db.query(ScrapeJob).filter(
            ScrapeJob.status == 'queued'
        ).order_by(ScrapeJob.queue_position.asc()).first()
        
        if job:
            print(f"[check_queue] Processing job_id={job.id}: {job.name}")
            
            # Update job status
            job.status = 'running'
            job.started_at = datetime.utcnow()
            db.commit()
            
            # Run appropriate job based on source type
            if job.source_type == 'multi_site':
                # Parse sites from JSON
                import json
                sites = json.loads(job.sites) if job.sites else []
                search_terms = job.search_terms.split(',') if job.search_terms else []
                exclude_terms = job.exclude_terms.split(',') if job.exclude_terms else []
                
                run_multi_site_scraping_job(
                    sites=sites,
                    search_terms=search_terms,
                    exclude_terms=exclude_terms,
                    min_pages=job.min_pages,
                    max_pages=job.max_pages,
                    min_file_size_mb=job.min_file_size_mb,
                    max_file_size_mb=job.max_file_size_mb,
                    follow_links=job.follow_links,
                    max_depth=job.max_depth,
                    extract_directories=job.extract_directories,
                    file_extensions=job.file_extensions.split(',') if job.file_extensions else None,
                    skip_duplicates=job.skip_duplicates,
                    max_results=job.max_results
                )
            else:
                # Run search job
                run_search_job(
                    query=job.query,
                    source_type=job.source_type,
                    max_results=job.max_results,
                    equipment_type=job.equipment_type,
                    manufacturer=job.manufacturer
                )
            
            # Update job status
            job.status = 'completed'
            job.completed_at = datetime.utcnow()
            db.commit()
            
            # Check if autostart is enabled and start next job
            if job.autostart_enabled:
                print(f"[check_queue] Autostart enabled, checking for next job")
                check_queue()
        
    except Exception as e:
        print(f"[check_queue] Error: {e}")
        db.rollback()
    finally:
        db.close()
