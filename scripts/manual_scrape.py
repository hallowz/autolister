#!/usr/bin/env python3
"""
Manual multi-site scraper test script
Run this on the Raspberry Pi to manually trigger a scrape and see results
"""
import sys
from pathlib import Path

# Add the app directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.scrapers.multi_site_scraper import MultiSiteScraper, ScraperConfig
from app.database import SessionLocal, Manual
from app.config import get_settings
from datetime import datetime

def manual_scrape():
    """Manually run a multi-site scrape"""
    print("=" * 60)
    print("Manual Multi-Site Scrape Test")
    print("=" * 60)
    print()
    
    settings = get_settings()
    
    # Configure scraper - adjust these values as needed
    scraper_config = ScraperConfig(
        sites=[
            # Add your target sites here
            # "https://example.com/manuals",
        ],
        search_terms=["manual", "pdf", "guide", "instructions"],
        exclude_terms=["price", "buy", "cart", "checkout"],
        max_results=10,
        max_depth=1,
        follow_links=False,
        min_file_size_mb=0.1,
        max_file_size_mb=50,
        timeout=30
    )
    
    print("Scraper Configuration:")
    print(f"  Sites: {scraper_config.sites or 'None (will use search engines)'}")
    print(f"  Search terms: {scraper_config.search_terms}")
    print(f"  Exclude terms: {scraper_config.exclude_terms}")
    print(f"  Max results: {scraper_config.max_results}")
    print(f"  Max depth: {scraper_config.max_depth}")
    print(f"  Follow links: {scraper_config.follow_links}")
    print(f"  File size range: {scraper_config.min_file_size_mb}MB - {scraper_config.max_file_size_mb}MB")
    print()
    
    # Initialize scraper
    scraper = MultiSiteScraper(scraper_config)
    
    # Run scrape
    print("Starting scrape...")
    print("-" * 60)
    
    def log_callback(message):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
    
    try:
        results = scraper.search(log_callback=log_callback)
        
        print()
        print("-" * 60)
        print(f"Scrape completed! Found {len(results)} PDFs")
        print()
        
        if results:
            print("Results:")
            for i, result in enumerate(results, 1):
                print(f"\n{i}. {result.title}")
                print(f"   URL: {result.url}")
                print(f"   Source Type: {result.source_type}")
                if result.equipment_type:
                    print(f"   Equipment Type: {result.equipment_type}")
                if result.manufacturer:
                    print(f"   Manufacturer: {result.manufacturer}")
                if result.model:
                    print(f"   Model: {result.model}")
        else:
            print("No PDFs found. This could be due to:")
            print("  - No matching search terms on the sites")
            print("  - All PDFs excluded by exclude terms")
            print("  - File size filters")
            print("  - Network issues")
            print()
            print("Try adjusting the scraper configuration above.")
        
        # Check database for duplicates
        print()
        print("-" * 60)
        print("Checking database for duplicates...")
        db = SessionLocal()
        try:
            new_count = 0
            duplicate_count = 0
            
            for result in results:
                existing = db.query(Manual).filter(
                    Manual.source_url == result.url
                ).first()
                
                if existing:
                    duplicate_count += 1
                    print(f"  Duplicate: {result.title}")
                    print(f"    Status: {existing.status}")
                    print(f"    Created: {existing.created_at}")
                else:
                    new_count += 1
                    print(f"  New: {result.title}")
            
            print()
            print(f"Summary:")
            print(f"  Total found: {len(results)}")
            print(f"  New (would be saved): {new_count}")
            print(f"  Duplicates (would be skipped): {duplicate_count}")
            
            if new_count > 0:
                print()
                print("To save these new manuals to the database, run:")
                print("  python3 -c \"from app.tasks.jobs import run_multi_site_scrape; run_multi_site_scrape()\"")
            
        finally:
            db.close()
        
    except Exception as e:
        print(f"\nError during scrape: {e}")
        import traceback
        traceback.print_exc()
    
    print()
    print("=" * 60)

if __name__ == "__main__":
    manual_scrape()
