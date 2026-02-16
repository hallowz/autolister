"""
Database migration script to add description and tags fields to Manual table
Run this script to update your database schema
"""
import sqlite3
from pathlib import Path
from app.config import get_settings

settings = get_settings()

def migrate():
    """Add description and tags columns to manuals table"""
    db_path = Path(settings.database_path)
    
    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return False
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(manuals)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'description' in columns and 'tags' in columns:
            print("Columns 'description' and 'tags' already exist in manuals table")
            return True
        
        # Add description column
        if 'description' not in columns:
            print("Adding 'description' column to manuals table...")
            cursor.execute("ALTER TABLE manuals ADD COLUMN description TEXT")
        
        # Add tags column
        if 'tags' not in columns:
            print("Adding 'tags' column to manuals table...")
            cursor.execute("ALTER TABLE manuals ADD COLUMN tags TEXT")
        
        conn.commit()
        print("Migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
