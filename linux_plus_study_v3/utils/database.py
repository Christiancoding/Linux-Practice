#!/usr/bin/env python3
"""
Database Connection Pool Manager

Handles database connections with pooling for optimal performance
in web mode while maintaining backward compatibility with JSON storage.
"""

import os
import sys
import logging
from contextlib import contextmanager
from typing import Optional, Dict, Any
from sqlalchemy import create_engine, MetaData, text
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import QueuePool, StaticPool

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.config import get_database_config

class DatabasePoolManager:
    """Manages database connections with pooling for web applications."""
    
    def __init__(self, db_type: str = "sqlite", enable_pooling: bool = True):
        """
        Initialize database connection pool manager.
        
        Args:
            db_type (str): Database type (sqlite, postgresql, mysql)
            enable_pooling (bool): Whether to enable connection pooling
        """
        self.db_type = db_type
        self.enable_pooling = enable_pooling
        self.engine = None
        self.session_factory = None
        self.scoped_session_factory = None
        self.metadata = None
        
        self._setup_logging()
        self._initialize_engine()
    
    def _setup_logging(self) -> None:
        """Configure logging for database operations."""
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s: %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def _initialize_engine(self) -> None:
        """Initialize SQLAlchemy engine with appropriate pooling configuration."""
        try:
            config = get_database_config(self.db_type)
            engine_kwargs = {"echo": config.get("echo", False)}
            
            if self.enable_pooling and config.get("pool_enabled", False):
                # Configure connection pooling for supported databases
                engine_kwargs.update({
                    "poolclass": QueuePool,
                    "pool_size": config.get("pool_size", 10),
                    "max_overflow": config.get("max_overflow", 20),
                    "pool_pre_ping": config.get("pool_pre_ping", True),
                    "pool_recycle": config.get("pool_recycle", 3600),
                    "pool_timeout": config.get("pool_timeout", 30),
                })
                self.logger.info(f"Initializing {self.db_type} with connection pooling")
            else:
                # SQLite or pooling disabled
                if self.db_type == "sqlite":
                    engine_kwargs["poolclass"] = StaticPool
                    engine_kwargs["connect_args"] = {"check_same_thread": False}
                self.logger.info(f"Initializing {self.db_type} without connection pooling")
            
            self.engine = create_engine(config["url"], **engine_kwargs)
            self.metadata = MetaData()
            
            # Create session factories
            self.session_factory = sessionmaker(bind=self.engine)
            self.scoped_session_factory = scoped_session(self.session_factory)
            
            # Test connection
            self._test_connection()
            
        except Exception as e:
            self.logger.error(f"Failed to initialize database engine: {e}")
            raise
    
    def _test_connection(self) -> None:
        """Test database connection to ensure it's working."""
        try:
            if self.engine is None:
                self.logger.error("Cannot test connection: database engine is not initialized")
                return
                
            with self.engine.connect() as conn:
                # Execute a simple query to test connection
                conn.execute(text("SELECT 1"))
            self.logger.info("Database connection test successful")
        except Exception as e:
            self.logger.error(f"Database connection test failed: {e}")
            raise
    
    @contextmanager
    def get_session(self):
        """
        Context manager for database sessions with automatic cleanup.
        
        Yields:
            SQLAlchemy Session: Database session for transactions
        """
        if self.session_factory is None:
            self.logger.error("Session factory is not initialized")
            raise RuntimeError("Database session factory is not initialized. Make sure the database engine was properly configured.")
            
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            self.logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    def get_scoped_session(self):
        """
        Get a thread-local scoped session for web applications.
        
        Returns:
            scoped_session: Thread-safe session factory
        """
        return self.scoped_session_factory
    
    def close_all_connections(self) -> None:
        """Close all database connections and clean up resources."""
        try:
            if self.scoped_session_factory:
                self.scoped_session_factory.remove()
            if self.engine:
                self.engine.dispose()
            self.logger.info("All database connections closed")
        except Exception as e:
            self.logger.error(f"Error closing database connections: {e}")
    
    def get_pool_status(self) -> Dict[str, Any]:
        """
        Get current connection pool status for monitoring.
        
        Returns:
            dict: Pool status information
        """
        if not self.enable_pooling or self.engine is None or not hasattr(self.engine, 'pool'):
            return {"pooling_enabled": False}
        
        pool = self.engine.pool
        
        return {
            "pooling_enabled": True,
            "pool_size": getattr(pool, 'size', 0),
            "checked_in": getattr(pool, 'checkedin', 0),
            "checked_out": getattr(pool, 'checkedout', 0),
            "overflow": getattr(pool, 'overflow', 0),
            "invalid": getattr(pool, 'invalid', 0),
        }

# Global database manager instance
_db_manager: Optional[DatabasePoolManager] = None

def initialize_database_pool(db_type: str = "sqlite", enable_pooling: bool = True) -> DatabasePoolManager:
    """
    Initialize global database connection pool.
    
    Args:
        db_type (str): Database type
        enable_pooling (bool): Whether to enable pooling
        
    Returns:
        DatabasePoolManager: Initialized database manager
    """
    global _db_manager
    
    if _db_manager is None:
        _db_manager = DatabasePoolManager(db_type, enable_pooling)
    
    return _db_manager

def get_database_manager() -> Optional[DatabasePoolManager]:
    """Get the global database manager instance."""
    return _db_manager

def get_db_session():
    """Get a database session for use with analytics and other features."""
    db_manager = get_database_manager()
    if db_manager is None:
        # Initialize database manager if not already done
        db_manager = initialize_database_pool()
    return db_manager.get_session()

def cleanup_database_connections() -> None:
    """Clean up all database connections."""
    global _db_manager
    
    if _db_manager:
        _db_manager.close_all_connections()
        _db_manager = None

# Keep existing JSON-based functions for backward compatibility
def load_json_file(file_path: str) -> Dict[str, Any]:
    """Load data from JSON file (backward compatibility)."""
    import json
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except FileNotFoundError:
        logging.warning(f"JSON file not found: {file_path}")
        return {}
    except json.JSONDecodeError as e:
        logging.error(f"Invalid JSON in file {file_path}: {e}")
        return {}

def save_json_file(file_path: str, data: Dict[str, Any]) -> bool:
    """Save data to JSON file (backward compatibility)."""
    import json
    import os
    
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(data, file, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logging.error(f"Failed to save JSON file {file_path}: {e}")
        return False

# Alias functions for compatibility
def get_session():
    """Alias for get_db_session for compatibility."""
    return get_db_session()

def get_db_connection():
    """Get a raw database connection for direct SQL operations."""
    import sqlite3
    
    # For now, return a direct SQLite connection to the data directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    db_path = os.path.join(project_root, 'data', 'linux_plus_study.db')
    
    # Ensure data directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    return sqlite3.connect(db_path)

def setup_database_for_web():
    """Set up database for web mode - alias for get_database_manager."""
    return get_database_manager() or initialize_database_pool()