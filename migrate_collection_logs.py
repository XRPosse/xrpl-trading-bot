"""
Migrate database to support real-time collection
"""

from sqlalchemy import create_engine, text
from src.config.settings import get_settings
from src.database.models import Base


def migrate_database():
    """Update database schema for real-time collection"""
    settings = get_settings()
    engine = create_engine(settings.database_url)
    
    print("Migrating database for real-time collection...")
    
    try:
        with engine.connect() as conn:
            # Add last_run column if it doesn't exist
            try:
                conn.execute(text("""
                    ALTER TABLE data_collection_logs 
                    ADD COLUMN IF NOT EXISTS last_run TIMESTAMP
                """))
                print("✓ Added last_run column")
            except Exception as e:
                print(f"  Column may already exist: {e}")
                
            # Add unique constraint if it doesn't exist
            try:
                conn.execute(text("""
                    ALTER TABLE data_collection_logs 
                    ADD CONSTRAINT _collection_target_uc 
                    UNIQUE (collection_type, target)
                """))
                print("✓ Added unique constraint")
            except Exception as e:
                print(f"  Constraint may already exist: {e}")
                
            # Update status column to have default
            try:
                conn.execute(text("""
                    ALTER TABLE data_collection_logs 
                    ALTER COLUMN status SET DEFAULT 'pending'
                """))
                print("✓ Updated status column default")
            except Exception as e:
                print(f"  Default may already be set: {e}")
                
            # Commit changes
            conn.commit()
            
        print("\n✓ Database migration complete!")
        
    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        print("\nYou may need to manually update the schema or drop/recreate the table")
        

if __name__ == "__main__":
    migrate_database()