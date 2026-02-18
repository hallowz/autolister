"""
Migration to add multi-site scraping columns to scrape_jobs table
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import engine
from sqlalchemy import text

def migrate():
    """Add multi-site scraping columns to scrape_jobs table"""
    try:
        with engine.connect() as conn:
            # Check which columns exist
            result = conn.execute(text("PRAGMA table_info(scrape_jobs)"))
            existing_columns = [row[1] for row in result]
            
            # Columns to add
            columns_to_add = {
                'exclude_sites': 'TEXT',
                'search_terms': 'TEXT',
                'exclude_terms': 'TEXT',
                'min_pages': 'INTEGER',
                'max_pages': 'INTEGER',
                'min_file_size_mb': 'REAL',
                'max_file_size_mb': 'REAL',
                'follow_links': 'BOOLEAN DEFAULT 1',
                'max_depth': 'INTEGER DEFAULT 2',
                'extract_directories': 'BOOLEAN DEFAULT 1',
                'file_extensions': 'TEXT DEFAULT "pdf"',
                'skip_duplicates': 'BOOLEAN DEFAULT 1',
                'notes': 'TEXT',
                'queue_position': 'INTEGER'
            }
            
            for column_name, column_def in columns_to_add.items():
                if column_name not in existing_columns:
                    # Add the column
                    conn.execute(text(f"""
                        ALTER TABLE scrape_jobs 
                        ADD COLUMN {column_name} {column_def}
                    """))
                    conn.commit()
                    print(f"Successfully added {column_name} column to scrape_jobs table")
                else:
                    print(f"{column_name} column already exists in scrape_jobs table")
                
    except Exception as e:
        print(f"Error during migration: {e}")
        sys.exit(1)

if __name__ == "__main__":
    migrate()
