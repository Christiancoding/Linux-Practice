#!/usr/bin/env python3
"""
Database Connection Manager for Separate Database Files

Manages connections to different database files as per CLAUDE.md specifications.
"""

import os
import sqlite3
import logging
from contextlib import contextmanager
from typing import Dict, Any, Optional, Union, Generator
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import StaticPool

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages connections to multiple database files."""
    
    def __init__(self):
        """Initialize database manager."""
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        self.project_root = os.path.dirname(self.current_dir)
        self.data_dir = os.path.join(self.project_root, 'data')
        
        # Ensure data directory exists
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Database file mapping
        self.db_files = {
            "analytics": "linux_plus_study.db",
            "achievements": "linux_plus_study_achievements.db", 
            "history": "linux_plus_study_history.db",
            "questions": "linux_plus_study_questions.db",
            "settings": "linux_plus_study_settings.db"
        }
        
        # SQLAlchemy engines
        self.engines = {}
        self.session_factories = {}
        self._initialize_engines()
    
    def _initialize_engines(self) -> None:
        """Initialize SQLAlchemy engines for each database."""
        for db_name, db_file in self.db_files.items():
            db_path = os.path.join(self.data_dir, db_file)
            engine = create_engine(
                f"sqlite:///{db_path}",
                poolclass=StaticPool,
                connect_args={"check_same_thread": False},
                echo=False
            )
            self.engines[db_name] = engine
            self.session_factories[db_name] = sessionmaker(bind=engine)
    
    def get_connection(self, db_name: str = "analytics") -> sqlite3.Connection:
        """Get a raw SQLite connection."""
        db_file = self.db_files.get(db_name, "linux_plus_study.db")
        db_path = os.path.join(self.data_dir, db_file)
        return sqlite3.connect(db_path)
    
    @contextmanager
    def get_session(self, db_name: str = "analytics") -> Generator:
        """Get a SQLAlchemy session with context management."""
        if db_name not in self.session_factories:
            raise ValueError(f"Unknown database: {db_name}")
        
        session = self.session_factories[db_name]()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error for {db_name}: {e}")
            raise
        finally:
            session.close()
    
    def get_engine(self, db_name: str = "analytics"):
        """Get SQLAlchemy engine for a specific database."""
        return self.engines.get(db_name)
    
    def close_all_connections(self) -> None:
        """Close all database connections."""
        for engine in self.engines.values():
            engine.dispose()

# Global database manager instance
_db_manager: Optional[DatabaseManager] = None

def get_database_manager() -> DatabaseManager:
    """Get the global database manager instance."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager

def get_db_connection(db_name: str = "analytics") -> sqlite3.Connection:
    """Get a database connection for a specific database."""
    return get_database_manager().get_connection(db_name)

def get_db_session(db_name: str = "analytics"):
    """Get a database session for a specific database."""
    return get_database_manager().get_session(db_name)

def get_db_engine(db_name: str = "analytics"):
    """Get a database engine for a specific database.""" 
    return get_database_manager().get_engine(db_name)

def cleanup_database_connections() -> None:
    """Clean up all database connections."""
    global _db_manager
    if _db_manager:
        _db_manager.close_all_connections()
        _db_manager = None