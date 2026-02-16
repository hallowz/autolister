"""
Background job definitions for scraping and processing
"""
from typing import List
from app.database import SessionLocal, Manual, ProcessingLog
from app.scrapers import DuckDuckGoScraper
from app.processors import PDFDownloader, PDFProcessor, SummaryGenerator
from app.etsy import ListingManager
from app.config import get_settings

settings = get_settings()


def run_scraping_job(query: str = None, max_results: int = None):
    """
    Run a scraping job to discover PDF manuals
    
    Args:
        query: Optional specific query to search for
        max_results: Optional maximum results per search
    """
    db = SessionLocal()
    
    try:
        # Get search queries
        from app.config import get_search_config
        search_config = get_search_config()
        
        queries = [query] if query else search_config.get_search_queries()
        max_results = max_results or settings.max_results_per_search
        
        # Initialize scraper (only DuckDuckGo - free, no API key required)
        duckduckgo_scraper = DuckDuckGoScraper(settings.model_dump())
        
        total_discovered = 0
        
        for search_query in queries:
            print(f"Searching for: {search_query}")
            
            # Search using DuckDuckGo (free, no API key required)
            results = []
            try:
                ddg_results = duckduckgo_scraper.search(search_query)
                results.extend(ddg_results)
            except Exception as e:
                print(f"DuckDuckGo scraper error: {e}")
            
            # Save results to database
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
            
            db.commit()
        
        print(f"Scraping job completed. Discovered {total_discovered} new manuals.")
        
        # Log completion
        log = ProcessingLog(
            stage='scrape',
            status='completed',
            message=f'Discovered {total_discovered} new manuals'
        )
        db.add(log)
        db.commit()
        
    except Exception as e:
        print(f"Scraping job error: {e}")
        
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
        summary_gen = SummaryGenerator()
        
        for manual in processed_manuals:
            try:
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
                    manual.id,
                    manufacturer=manual.manufacturer,
                    model=manual.model,
                    year=manual.year
                )
                
                # Create Etsy listing
                listing_id = listing_manager.create_digital_listing(
                    title=title,
                    description=description,
                    pdf_path=manual.pdf_path,
                    image_paths=images['main'] + images['additional'],
                    price=settings.etsy_default_price
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
