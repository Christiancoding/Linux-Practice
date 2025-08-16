#!/usr/bin/env python3
"""
Analytics Database Setup Script

Creates the analytics table in the database if it doesn't exist.
Can be run standalone or imported as a module.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text
from models.analytics import Base, Analytics
from utils.database import get_database_manager, initialize_database_pool
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_analytics_table():
    """Create analytics table if it doesn't exist."""
    try:
        # Initialize database
        db_manager = initialize_database_pool()
        engine = db_manager.engine
        
        # Create all tables defined in the Analytics model
        logger.info("Creating analytics table...")
        Base.metadata.create_all(engine)
        
        # Verify table was created
        with engine.connect() as conn:
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='analytics'"))
            if result.fetchone():
                logger.info("✅ Analytics table created successfully!")
                return True
            else:
                logger.error("❌ Failed to create analytics table")
                return False
                
    except Exception as e:
        logger.error(f"Error creating analytics table: {e}")
        return False

def verify_analytics_table():
    """Verify analytics table exists and has expected structure."""
    try:
        db_manager = get_database_manager()
        if not db_manager:
            db_manager = initialize_database_pool()
            
        engine = db_manager.engine
        
        with engine.connect() as conn:
            # Check if table exists
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='analytics'"))
            if not result.fetchone():
                logger.info("Analytics table does not exist")
                return False
            
            # Check table structure
            result = conn.execute(text("PRAGMA table_info(analytics)"))
            columns = [row[1] for row in result.fetchall()]
            
            expected_columns = [
                'id', 'created_at', 'updated_at', 'user_id', 'session_id',
                'activity_type', 'questions_attempted', 'questions_correct',
                'vm_commands_executed', 'achievements_unlocked'
            ]
            
            missing_columns = [col for col in expected_columns if col not in columns]
            if missing_columns:
                logger.warning(f"Missing columns in analytics table: {missing_columns}")
                return False
            
            logger.info("✅ Analytics table structure verified")
            return True
            
    except Exception as e:
        logger.error(f"Error verifying analytics table: {e}")
        return False

def setup_analytics_database():
    """Main setup function - creates table if needed."""
    logger.info("Setting up analytics database...")
    
    if verify_analytics_table():
        logger.info("Analytics table already exists and is properly configured")
        return True
    
    logger.info("Analytics table needs to be created...")
    return create_analytics_table()

if __name__ == "__main__":
    print("🔧 Linux Plus Study Analytics Database Setup")
    print("=" * 50)
    
    if setup_analytics_database():
        print("✅ Analytics database setup completed successfully!")
        print("\nYou can now use the analytics features:")
        print("  • Quiz performance tracking")
        print("  • Study session analytics")
        print("  • VM usage statistics")
        print("  • Learning progress insights")
    else:
        print("❌ Analytics database setup failed!")
        print("Please check the error messages above and try again.")
        sys.exit(1)
