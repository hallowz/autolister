#!/usr/bin/env python3
"""
Diagnostic script to check pending manuals in the database
Run this on the Raspberry Pi to verify the database state
"""
import sys
from pathlib import Path

# Add the app directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import SessionLocal, Manual
from app.config import get_settings

def diagnose():
    """Diagnose pending manuals in the database"""
    settings = get_settings()
    print(f"Database path: {settings.database_path}")
    print(f"Database exists: {Path(settings.database_path).exists()}")
    print()
    
    db = SessionLocal()
    try:
        # Check all manuals
        all_manuals = db.query(Manual).all()
        print(f"Total manuals in database: {len(all_manuals)}")
        
        # Count by status
        status_counts = {}
        for manual in all_manuals:
            status = manual.status
            status_counts[status] = status_counts.get(status, 0) + 1
        
        print("\nManuals by status:")
        for status, count in status_counts.items():
            print(f"  - {status}: {count}")
        
        # Check pending manuals
        pending = db.query(Manual).filter(Manual.status == 'pending').all()
        print(f"\nPending manuals: {len(pending)}")
        
        if pending:
            print("\nPending manual details:")
            for manual in pending:
                print(f"  - ID: {manual.id}")
                print(f"    Title: {manual.title}")
                print(f"    Source URL: {manual.source_url}")
                print(f"    Source Type: {manual.source_type}")
                print(f"    Status: {manual.status}")
                print(f"    Created: {manual.created_at}")
                print(f"    PDF Path: {manual.pdf_path}")
                if manual.pdf_path:
                    print(f"    PDF Exists: {Path(manual.pdf_path).exists()}")
                print()
        else:
            print("\nNo pending manuals found in database")
            print("\nRecent manuals (all statuses):")
            for manual in sorted(all_manuals, key=lambda m: m.created_at or '', reverse=True)[:5]:
                print(f"  - ID: {manual.id}, Status: {manual.status}, Title: {manual.title}, Created: {manual.created_at}")
        
        # Check for multi-site scraper results
        multi_site = db.query(Manual).filter(Manual.source_type == 'multi_site').all()
        print(f"\nMulti-site scraper results: {len(multi_site)}")
        if multi_site:
            print("Multi-site manuals:")
            for manual in multi_site:
                print(f"  - ID: {manual.id}, Status: {manual.status}, Title: {manual.title}")
        
    finally:
        db.close()

if __name__ == "__main__":
    diagnose()
