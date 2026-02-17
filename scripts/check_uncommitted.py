#!/usr/bin/env python3
"""
Check for manuals that might have been found but not committed due to database lock
Run this on the Raspberry Pi to check the database state
"""
import sys
from pathlib import Path

# Add the app directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import SessionLocal, Manual, ScrapedSite
from datetime import datetime, timedelta

def check_uncommitted():
    """Check for potential uncommitted data"""
    print("=" * 60)
    print("Checking for Uncommitted Data")
    print("=" * 60)
    print()
    
    db = SessionLocal()
    try:
        # Check total manuals
        all_manuals = db.query(Manual).all()
        print(f"Total manuals in database: {len(all_manuals)}")
        
        # Count by status
        status_counts = {}
        for manual in all_manuals:
            status = manual.status
            status_counts[status] = status_counts.get(status, 0) + 1
        
        print("\nManuals by status:")
        for status, count in sorted(status_counts.items()):
            print(f"  - {status}: {count}")
        
        # Check for multi-site results
        multi_site = db.query(Manual).filter(Manual.source_type == 'multi_site').all()
        print(f"\nMulti-site scraper results: {len(multi_site)}")
        
        if multi_site:
            print("\nMulti-site manuals by status:")
            status_breakdown = {}
            for manual in multi_site:
                status = manual.status
                status_breakdown[status] = status_breakdown.get(status, 0) + 1
            for status, count in sorted(status_breakdown.items()):
                print(f"  - {status}: {count}")
        
        # Check scraped sites
        scraped_sites = db.query(ScrapedSite).all()
        print(f"\nScraped sites tracked: {len(scraped_sites)}")
        
        if scraped_sites:
            print("\nRecently scraped sites:")
            for site in sorted(scraped_sites, key=lambda s: s.last_scraped_at or '', reverse=True)[:10]:
                print(f"  - {site.domain}")
                print(f"    Last scraped: {site.last_scraped_at}")
                print(f"    Scrape count: {site.scrape_count}")
        
        # Check for recent activity
        recent_cutoff = datetime.utcnow() - timedelta(minutes=10)
        recent_manuals = db.query(Manual).filter(
            Manual.created_at >= recent_cutoff
        ).all()
        
        print(f"\nManuals created in last 10 minutes: {len(recent_manuals)}")
        
        if recent_manuals:
            print("\nRecent manuals:")
            for manual in sorted(recent_manuals, key=lambda m: m.created_at or '', reverse=True):
                print(f"  - ID: {manual.id}, Status: '{manual.status}', Created: {manual.created_at}")
                print(f"    Title: {manual.title}")
        
        print()
        print("=" * 60)
        print("Analysis:")
        print("=" * 60)
        
        if len(multi_site) == 0:
            print("⚠️  No multi-site scraper results found in database.")
            print("   This suggests either:")
            print("   1. The scraper hasn't run yet")
            print("   2. The scraper found no PDFs")
            print("   3. The transaction was rolled back due to database lock")
            print()
            print("   Check the application logs for scraper activity.")
        elif len(multi_site) > 0:
            pending_multi_site = [m for m in multi_site if m.status == 'pending']
            if len(pending_multi_site) > 0:
                print(f"✓ Found {len(pending_multi_site)} pending multi-site manuals")
                print("  These should appear in the dashboard.")
            else:
                print("⚠️  Multi-site manuals exist but none are pending.")
                print("  Check if they have a different status.")
        
        print()
        print("Next steps:")
        print("1. If no manuals exist, run the scraper manually:")
        print("   python3 scripts/manual_scrape.py")
        print()
        print("2. If manuals exist but not pending, check their status.")
        print()
        print("3. Restart the application to ensure database changes are picked up:")
        print("   sudo systemctl restart autolister")
        print()
        print("4. Test the API endpoint:")
        print("   python3 scripts/test_pending_api.py")
        
    finally:
        db.close()

if __name__ == "__main__":
    check_uncommitted()
