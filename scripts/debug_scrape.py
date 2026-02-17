#!/usr/bin/env python3
"""
Debug script to trace what happens during a multi-site scrape
Run this on the Raspberry Pi to see exactly what's being saved
"""
import sys
from pathlib import Path

# Add the app directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.tasks.jobs import run_multi_site_scraping_job
from app.database import SessionLocal, Manual
from datetime import datetime

def debug_scrape():
    """Run a debug scrape with detailed logging"""
    print("=" * 60)
    print("Debug Multi-Site Scrape")
    print("=" * 60)
    print()
    
    # Check database before scrape
    print("1. Database State Before Scrape")
    print("-" * 60)
    db = SessionLocal()
    try:
        all_manuals = db.query(Manual).all()
        print(f"Total manuals: {len(all_manuals)}")
        
        pending_before = db.query(Manual).filter(Manual.status == 'pending').count()
        multi_site_before = db.query(Manual).filter(Manual.source_type == 'multi_site').count()
        print(f"Pending manuals: {pending_before}")
        print(f"Multi-site manuals: {multi_site_before}")
    finally:
        db.close()
    
    print()
    print("2. Running Scrape")
    print("-" * 60)
    
    def log_callback(message):
        print(f"[LOG] {message}")
    
    # Run a small test scrape
    try:
        run_multi_site_scraping_job(
            sites=[
                # Add a test site here
                # "https://example.com/manuals",
            ],
            search_terms=['manual', 'pdf'],
            exclude_terms=['preview', 'buy', 'cart'],
            max_results=5,
            max_depth=1,
            follow_links=False,
            log_callback=log_callback
        )
    except Exception as e:
        print(f"[ERROR] Scrape failed: {e}")
        import traceback
        traceback.print_exc()
    
    print()
    print("3. Database State After Scrape")
    print("-" * 60)
    db = SessionLocal()
    try:
        all_manuals = db.query(Manual).all()
        print(f"Total manuals: {len(all_manuals)}")
        
        pending_after = db.query(Manual).filter(Manual.status == 'pending').count()
        multi_site_after = db.query(Manual).filter(Manual.source_type == 'multi_site').count()
        print(f"Pending manuals: {pending_after}")
        print(f"Multi-site manuals: {multi_site_after}")
        
        # Check for recently added manuals
        recent_cutoff = datetime.utcnow()
        recent_manuals = db.query(Manual).filter(
            Manual.created_at >= recent_cutoff
        ).all()
        
        print(f"\nRecently added manuals: {len(recent_manuals)}")
        for manual in recent_manuals:
            print(f"  - ID: {manual.id}")
            print(f"    Status: '{manual.status}'")
            print(f"    Source Type: '{manual.source_type}'")
            print(f"    Title: {manual.title}")
            print(f"    URL: {manual.source_url}")
            print()
        
        # Check all multi-site manuals
        all_multi_site = db.query(Manual).filter(
            Manual.source_type == 'multi_site'
        ).all()
        
        print(f"\nAll multi-site manuals: {len(all_multi_site)}")
        for manual in all_multi_site:
            print(f"  - ID: {manual.id}, Status: '{manual.status}', Created: {manual.created_at}")
            print(f"    Title: {manual.title}")
        
    finally:
        db.close()
    
    print()
    print("=" * 60)
    print("Debug Complete")
    print("=" * 60)

if __name__ == "__main__":
    debug_scrape()
