"""
Migration to create niche_discoveries table
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import engine, Base
from sqlalchemy import text

def migrate():
    """Create niche_discoveries table"""
    try:
        with engine.connect() as conn:
            # Check if table already exists
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='niche_discoveries'"))
            if result.fetchone():
                print("niche_discoveries table already exists")
                return
            
            # Create the table
            conn.execute(text("""
                CREATE TABLE niche_discoveries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    niche VARCHAR NOT NULL,
                    description TEXT,
                    search_query VARCHAR,
                    potential_price VARCHAR,
                    demand_level VARCHAR DEFAULT 'medium',
                    competition_level VARCHAR DEFAULT 'medium',
                    keywords TEXT,
                    sites_to_search TEXT,
                    reason TEXT,
                    status VARCHAR DEFAULT 'discovered',
                    scrape_job_id INTEGER,
                    manuals_found INTEGER DEFAULT 0,
                    manuals_listed INTEGER DEFAULT 0,
                    revenue_generated REAL DEFAULT 0.0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_scraped_at DATETIME,
                    FOREIGN KEY (scrape_job_id) REFERENCES scrape_jobs (id)
                )
            """))
            conn.commit()
            print("Successfully created niche_discoveries table")
                
    except Exception as e:
        print(f"Error during migration: {e}")
        sys.exit(1)

if __name__ == "__main__":
    migrate()
