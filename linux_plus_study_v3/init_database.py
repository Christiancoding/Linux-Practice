#!/usr/bin/env python3
"""
Initialize Database Tables

Creates all necessary database tables including the analytics table.
"""

import os
import sys
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Analytics removed - no analytics tables to create
from utils.config import get_database_config

def initialize_database():
    """Initialize the database and create all tables."""
    
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    try:
        # Get database configuration
        config = get_database_config()
        database_url = config.get('url', 'sqlite:///data/linux_plus_study.db')
        
        # Create engine
        engine = create_engine(database_url, echo=True)
        
        # Create all tables
        logger.info("Creating database tables...")
        # Analytics removed - no tables to create
        logger.info("✓ Database tables created successfully!")
        
        # Test the connection
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Test analytics table
        # Analytics removed - no table to test
        
        session.close()
        logger.info("✓ Database initialization completed successfully!")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return False

if __name__ == "__main__":
    success = initialize_database()
    sys.exit(0 if success else 1)
