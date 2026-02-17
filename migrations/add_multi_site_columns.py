"""
Migration to add multi-site scraping columns to scrape_jobs table
and create scraped_sites table
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import engine, Base
from sqlalchemy import text

def migrate():
    """Add multi-site scraping columns to scrape_jobs table and create scraped_sites table"""
    try:
        # Create all tables first
        Base.metadata.create_all(bind=engine)
        print("Successfully created all tables including scraped_sites")
        
        with engine.connect() as conn:
            # Check if columns already exist in scrape_jobs
            result = conn.execute(text("PRAGMA table_info(scrape_jobs)"))
            columns = [row[1] for row in result]
            
            # Add advanced scraping settings columns if they don't exist
            columns_to_add = {
                'sites': 'TEXT',
                'search_terms': 'TEXT',
                'exclude_terms': 'TEXT',
                'min_pages': 'INTEGER DEFAULT 5',
                'max_pages': 'INTEGER',
                'min_file_size_mb': 'REAL',
                'max_file_size_mb': 'REAL',
                'follow_links': 'BOOLEAN DEFAULT 1',
                'max_depth': 'INTEGER DEFAULT 2',
                'extract_directories': 'BOOLEAN DEFAULT 1',
                'file_extensions': 'TEXT DEFAULT "pdf"',
                'skip_duplicates': 'BOOLEAN DEFAULT 1',
                'notes': 'TEXT'
            }
            
            for column, definition in columns_to_add.items():
                if column not in columns:
                    conn.execute(text(f"""
                        ALTER TABLE scrape_jobs 
                        ADD COLUMN {column} {definition}
                    """))
                    print(f"Successfully added {column} column to scrape_jobs table")
                else:
                    print(f"{column} column already exists in scrape_jobs table")
            
            conn.commit()
            print("Multi-site scraping columns migration completed successfully")
            
    except Exception as e:
        print(f"Error during migration: {e}")
        sys.exit(1)

if __name__ == "__main__":
    migrate()
