"""
Analytics Model - Data Management

Enhanced model with SQLAlchemy ORM support and
backward compatibility with JSON-based storage.
"""

from sqlalchemy import Column, Integer, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, timezone
from typing import Dict, Any
import logging

Base = declarative_base()
logger = logging.getLogger(__name__)

class Analytics(Base):
    """Enhanced analytics model with ORM support."""
    
    __tablename__ = 'analyticss'
    
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Additional fields will be added during migration
    
    def __repr__(self):
        return f"<Analytics(id={self.id})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary for JSON compatibility."""
        return {
            'id': self.id,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }
