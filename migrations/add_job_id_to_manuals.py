"""
Migration to add job_id column to manuals table
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.database import engine, SessionLocal

def migrate():
    """Add job_id column to manuals table"""
    print("Starting migration: Add job_id column to manuals table...")
    
    db = SessionLocal()
    try:
        # Check if column already exists
        inspector = text("PRAGMA table_info(manuals)")
        result = db.execute(inspector).fetchall()
        columns = [row[1] for row in result]
        
        if 'job_id' in columns:
            print("Column 'job_id' already exists in manuals table. Skipping migration.")
            return
        
        # Add job_id column
        print("Adding job_id column to manuals table...")
        db.execute(text("ALTER TABLE manuals ADD COLUMN job_id INTEGER"))
        db.commit()
        
        # Create index on job_id
        print("Creating index on job_id column...")
        db.execute(text("CREATE INDEX IF NOT EXISTS ix_manuals_job_id ON manuals (job_id)"))
        db.commit()
        
        print("Migration completed successfully!")
        
    except Exception as e:
        print(f"Migration failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    migrate()
