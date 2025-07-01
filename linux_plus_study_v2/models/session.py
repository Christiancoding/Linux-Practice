"""
Session Model - Data Management

Enhanced model with SQLAlchemy ORM support and
backward compatibility with JSON-based storage.
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import logging

Base = declarative_base()
logger = logging.getLogger(__name__)

class Session(Base):
    """Enhanced session model with ORM support."""
    
    __tablename__ = 'sessions'
    
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Additional fields will be added during migration
    
    def __repr__(self):
        return f"<Session(id={self.id})>"
    
    def to_dict(self) -> dict:
        """Convert model to dictionary for JSON compatibility."""
        return {
            'id': self.id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
