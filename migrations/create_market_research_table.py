"""
Migration to create market_research table
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import engine
from sqlalchemy import text

def migrate():
    """Create market_research table"""
    try:
        with engine.connect() as conn:
            # Check if table already exists
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='market_research'"))
            if result.fetchone():
                print("market_research table already exists")
                return
            
            # Create the table
            conn.execute(text("""
                CREATE TABLE market_research (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    manual_id INTEGER,
                    niche_id INTEGER,
                    search_query TEXT,
                    similar_listings TEXT,
                    competitor_prices TEXT,
                    average_price REAL,
                    price_range_low REAL,
                    price_range_high REAL,
                    demand_score REAL,
                    competition_score REAL,
                    recommendation TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (manual_id) REFERENCES manuals (id),
                    FOREIGN KEY (niche_id) REFERENCES niche_discoveries (id)
                )
            """))
            conn.commit()
            print("Successfully created market_research table")
                
    except Exception as e:
        print(f"Error during migration: {e}")
        sys.exit(1)

if __name__ == "__main__":
    migrate()
