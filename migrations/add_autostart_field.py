"""
Migration to add autostart_enabled field to scrape_jobs table
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import engine, Base
from sqlalchemy import text

def migrate():
    """Add autostart_enabled column to scrape_jobs table"""
    try:
        with engine.connect() as conn:
            # Check if column already exists
            result = conn.execute(text("PRAGMA table_info(scrape_jobs)"))
            columns = [row[1] for row in result]
            
            if 'autostart_enabled' not in columns:
                # Add the column
                conn.execute(text("""
                    ALTER TABLE scrape_jobs 
                    ADD COLUMN autostart_enabled BOOLEAN DEFAULT 0 NOT NULL
                """))
                conn.commit()
                print("Successfully added autostart_enabled column to scrape_jobs table")
            else:
                print("autostart_enabled column already exists in scrape_jobs table")
                
    except Exception as e:
        print(f"Error during migration: {e}")
        sys.exit(1)

if __name__ == "__main__":
    migrate()
