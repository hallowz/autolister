"""
Run all pending migrations
This script checks and runs all migrations that haven't been applied yet
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# List of all migrations in order
MIGRATIONS = [
    ('add_autostart_field', 'Add autostart_enabled field to scrape_jobs'),
    ('add_job_id_to_manuals', 'Add job_id to manuals table'),
    ('add_listing_fields', 'Add listing fields to manuals table'),
    ('add_multi_site_columns', 'Add multi-site scraping columns to scrape_jobs'),
    ('add_queue_position_to_jobs', 'Add queue_position to scrape_jobs'),
    ('add_multi_site_scraping_columns', 'Add all multi-site scraping columns'),
    ('create_niche_discoveries_table', 'Create niche_discoveries table'),
    ('create_market_research_table', 'Create market_research table'),
    ('add_job_timestamps', 'Add started_at and completed_at to scrape_jobs'),
]

def run_migration(migration_name, description):
    """Run a single migration"""
    try:
        module = __import__(f'migrations.{migration_name}', fromlist=[migration_name])
        if hasattr(module, 'migrate'):
            print(f"Running migration: {description}...")
            module.migrate()
            print(f"  ✓ Completed")
        else:
            print(f"  ✗ No migrate() function found in {migration_name}")
    except Exception as e:
        print(f"  ✗ Error running {migration_name}: {e}")
        return False
    return True

def main():
    print("=" * 60)
    print("Running AutoLister Migrations")
    print("=" * 60)
    print()
    
    success_count = 0
    for migration_name, description in MIGRATIONS:
        if run_migration(migration_name, description):
            success_count += 1
        print()
    
    print("=" * 60)
    print(f"Migrations completed: {success_count}/{len(MIGRATIONS)}")
    print("=" * 60)

if __name__ == "__main__":
    main()
