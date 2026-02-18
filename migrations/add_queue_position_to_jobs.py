"""
Migration to add queue_position field to scrape_jobs table
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import engine
from sqlalchemy import text

def migrate():
    """Add queue_position column to scrape_jobs table"""
    try:
        with engine.connect() as conn:
            # Check if column already exists
            result = conn.execute(text("PRAGMA table_info(scrape_jobs)"))
            columns = [row[1] for row in result]
            
            if 'queue_position' not in columns:
                # Add the column
                conn.execute(text("""
                    ALTER TABLE scrape_jobs 
                    ADD COLUMN queue_position INTEGER
                """))
                conn.commit()
                print("Successfully added queue_position column to scrape_jobs table")
            else:
                print("queue_position column already exists in scrape_jobs table")
                
    except Exception as e:
        print(f"Error during migration: {e}")
        sys.exit(1)

if __name__ == "__main__":
    migrate()
