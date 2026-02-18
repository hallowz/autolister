"""
Migration to add started_at and completed_at columns to scrape_jobs table
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import engine
from sqlalchemy import text

def migrate():
    """Add started_at and completed_at columns to scrape_jobs table"""
    try:
        with engine.connect() as conn:
            # Check which columns exist
            result = conn.execute(text("PRAGMA table_info(scrape_jobs)"))
            existing_columns = [row[1] for row in result]
            
            # Columns to add
            columns_to_add = {
                'started_at': 'DATETIME',
                'completed_at': 'DATETIME'
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
