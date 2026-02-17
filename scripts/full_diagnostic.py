#!/usr/bin/env python3
"""
Full diagnostic script for pending PDFs issue
Run this on the Raspberry Pi to diagnose the complete system
"""
import sys
from pathlib import Path

# Add the app directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import SessionLocal, Manual, ScrapedSite
from app.config import get_settings
from datetime import datetime

def full_diagnostic():
    """Run full diagnostic of the system"""
    print("=" * 60)
    print("AutoLister Full Diagnostic Report")
    print("=" * 60)
    print()
    
    # 1. Check configuration
    print("1. Configuration Check")
    print("-" * 60)
    settings = get_settings()
    print(f"Database path: {settings.database_path}")
    print(f"Database exists: {Path(settings.database_path).exists()}")
    print(f"Dashboard host: {settings.dashboard_host}")
    print(f"Dashboard port: {settings.dashboard_port}")
    print()
    
    db = SessionLocal()
    try:
        # 2. Database statistics
        print("2. Database Statistics")
        print("-" * 60)
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
        print()
        
        # Count by source type
        source_counts = {}
        for manual in all_manuals:
            source = manual.source_type
            source_counts[source] = source_counts.get(source, 0) + 1
        
        print("\nManuals by source type:")
        for source, count in sorted(source_counts.items()):
            print(f"  - {source}: {count}")
        print()
        
        # 3. Pending manuals details
        print("3. Pending Manuals Details")
        print("-" * 60)
        pending = db.query(Manual).filter(Manual.status == 'pending').all()
        print(f"Total pending manuals: {len(pending)}")
        
        if pending:
            print("\nPending manual details:")
            for i, manual in enumerate(pending, 1):
                print(f"\n  {i}. ID: {manual.id}")
                print(f"     Title: {manual.title}")
                print(f"     Source URL: {manual.source_url}")
                print(f"     Source Type: {manual.source_type}")
                print(f"     Status: '{manual.status}'")
                print(f"     Created: {manual.created_at}")
                print(f"     PDF Path: {manual.pdf_path}")
                if manual.pdf_path:
                    print(f"     PDF Exists: {Path(manual.pdf_path).exists()}")
        else:
            print("\nNo pending manuals found!")
            print("\nRecent manuals (all statuses):")
            for manual in sorted(all_manuals, key=lambda m: m.created_at or '', reverse=True)[:5]:
                print(f"  - ID: {manual.id}, Status: '{manual.status}', Title: {manual.title}")
                print(f"    Created: {manual.created_at}, Source: {manual.source_type}")
        print()
        
        # 4. Multi-site scraper results
        print("4. Multi-Site Scraper Results")
        print("-" * 60)
        multi_site = db.query(Manual).filter(Manual.source_type == 'multi_site').all()
        print(f"Total multi-site scraper results: {len(multi_site)}")
        
        if multi_site:
            print("\nMulti-site manuals by status:")
            status_breakdown = {}
            for manual in multi_site:
                status = manual.status
                status_breakdown[status] = status_breakdown.get(status, 0) + 1
            for status, count in sorted(status_breakdown.items()):
                print(f"  - {status}: {count}")
            
            print("\nRecent multi-site manuals:")
            for manual in sorted(multi_site, key=lambda m: m.created_at or '', reverse=True)[:5]:
                print(f"  - ID: {manual.id}, Status: '{manual.status}', Title: {manual.title}")
                print(f"    URL: {manual.source_url}")
        print()
        
        # 5. Scraped sites tracking
        print("5. Scraped Sites Tracking")
        print("-" * 60)
        scraped_sites = db.query(ScrapedSite).all()
        print(f"Total scraped sites: {len(scraped_sites)}")
        
        if scraped_sites:
            print("\nScraped sites:")
            for site in sorted(scraped_sites, key=lambda s: s.last_scraped_at or '', reverse=True)[:10]:
                print(f"  - {site.domain}")
                print(f"    Status: {site.status}, Scrape count: {site.scrape_count}")
                print(f"    Last scraped: {site.last_scraped_at}")
        print()
        
        # 6. Check for potential issues
        print("6. Potential Issues")
        print("-" * 60)
        
        # Check for status value issues
        status_issues = []
        for manual in all_manuals:
            if manual.status and manual.status != manual.status.lower():
                status_issues.append((manual.id, manual.status))
        
        if status_issues:
            print("⚠️  Manuals with uppercase status values:")
            for manual_id, status in status_issues:
                print(f"  - ID {manual_id}: '{status}'")
        else:
            print("✓ All status values are lowercase")
        
        # Check for whitespace issues
        whitespace_issues = []
        for manual in all_manuals:
            if manual.status and manual.status != manual.status.strip():
                whitespace_issues.append((manual.id, repr(manual.status)))
        
        if whitespace_issues:
            print("\n⚠️  Manuals with whitespace in status:")
            for manual_id, status in whitespace_issues:
                print(f"  - ID {manual_id}: {status}")
        else:
            print("✓ No whitespace issues in status values")
        
        # Check for duplicate URLs with different statuses
        url_status_map = {}
        duplicate_urls = []
        for manual in all_manuals:
            if manual.source_url in url_status_map:
                if url_status_map[manual.source_url] != manual.status:
                    duplicate_urls.append((manual.source_url, url_status_map[manual.source_url], manual.status))
            else:
                url_status_map[manual.source_url] = manual.status
        
        if duplicate_urls:
            print("\n⚠️  Duplicate URLs with different statuses:")
            for url, status1, status2 in duplicate_urls[:5]:
                print(f"  - {url}")
                print(f"    Statuses: '{status1}' and '{status2}'")
        else:
            print("✓ No duplicate URL conflicts")
        
        print()
        
        # 7. Recommendations
        print("7. Recommendations")
        print("-" * 60)
        
        if len(pending) == 0:
            print("⚠️  No pending manuals found!")
            print()
            print("Possible causes:")
            print("  1. Multi-site scraper hasn't run yet")
            print("  2. Scraper found no matching PDFs")
            print("  3. All PDFs were skipped as duplicates")
            print("  4. Scraper encountered errors (check logs)")
            print()
            print("Next steps:")
            print("  1. Run the multi-site scraper manually")
            print("  2. Check application logs for errors")
            print("  3. Verify search terms match your target PDFs")
            print("  4. Check if URLs are being skipped as duplicates")
        else:
            print(f"✓ Found {len(pending)} pending manuals")
            print()
            print("Next steps:")
            print("  1. Check if these appear in the dashboard")
            print("  2. If not, test the API endpoint: python3 scripts/test_pending_api.py")
            print("  3. Check browser console for JavaScript errors")
            print("  4. Verify the application is running")
        
        print()
        print("=" * 60)
        print("Diagnostic Complete")
        print("=" * 60)
        
    finally:
        db.close()

if __name__ == "__main__":
    full_diagnostic()
