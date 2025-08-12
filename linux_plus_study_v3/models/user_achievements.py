#!/usr/bin/env python3
"""
Database model for user achievements data.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON, Boolean
from sqlalchemy.sql import func
from datetime import datetime
from typing import Dict, Any, List, Optional

# Import the shared Base class from analytics model
from .analytics import Base


class UserAchievement(Base):
    """Database model for user achievements."""
    
    __tablename__ = 'user_achievements'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(255), nullable=False, default='anonymous')
    badges = Column(JSON, nullable=False, default=list)
    points_earned = Column(Integer, nullable=False, default=0)
    days_studied = Column(JSON, nullable=False, default=list)  # Store as list for JSON compatibility
    questions_answered = Column(Integer, nullable=False, default=0)
    streaks_achieved = Column(Integer, nullable=False, default=0)
    perfect_sessions = Column(Integer, nullable=False, default=0)
    daily_warrior_dates = Column(JSON, nullable=False, default=list)
    leaderboard = Column(JSON, nullable=False, default=list)
    survival_high_score = Column(Integer, nullable=False, default=0)
    survival_high_score_xp = Column(Integer, nullable=False, default=0)
    custom_achievements = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        # Handle SQLAlchemy column for days_studied: ensure we always return a list
        ds = getattr(self, 'days_studied', [])
        if isinstance(ds, list):
            days_studied_list = ds
        else:
            days_studied_list = []
        return {
            'badges': self.badges or [],
            'points_earned': self.points_earned,
            'days_studied': days_studied_list,
            'questions_answered': self.questions_answered,
            'streaks_achieved': self.streaks_achieved,
            'perfect_sessions': self.perfect_sessions,
            'daily_warrior_dates': self.daily_warrior_dates or [],
            'leaderboard': self.leaderboard or [],
            'survival_high_score': self.survival_high_score,
            'survival_high_score_xp': self.survival_high_score_xp,
            'custom_achievements': self.custom_achievements or []
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], user_id: str = 'anonymous') -> 'UserAchievement':
        """Create instance from dictionary data."""
        # Convert set to list for JSON storage
        days_studied = data.get('days_studied', set())
        if isinstance(days_studied, set):
            days_studied = list(days_studied)
        
        return cls(
            user_id=user_id,
            badges=data.get('badges', []),
            points_earned=data.get('points_earned', 0),
            days_studied=days_studied,
            questions_answered=data.get('questions_answered', 0),
            streaks_achieved=data.get('streaks_achieved', 0),
            perfect_sessions=data.get('perfect_sessions', 0),
            daily_warrior_dates=data.get('daily_warrior_dates', []),
            leaderboard=data.get('leaderboard', []),
            survival_high_score=data.get('survival_high_score', 0),
            survival_high_score_xp=data.get('survival_high_score_xp', 0),
            custom_achievements=data.get('custom_achievements', [])
        )


class UserHistory(Base):
    """Database model for user history data."""
    
    __tablename__ = 'user_history'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(255), nullable=False, default='anonymous')
    session_id = Column(String(255), nullable=False)
    activity_type = Column(String(100), nullable=False)
    question_id = Column(String(255))
    answer_given = Column(String(255))
    correct_answer = Column(String(255))
    is_correct = Column(Boolean, nullable=False)
    time_taken = Column(Float)
    points_earned = Column(Integer, nullable=False, default=0)
    category = Column(String(255))
    difficulty = Column(String(50))
    session_data = Column(JSON)
    created_at = Column(DateTime, nullable=False, default=func.now())


class TimeTracking(Base):
    """Database model for time tracking data."""
    
    __tablename__ = 'time_tracking'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(255), nullable=False, default='anonymous')
    quiz_time_today = Column(Float, nullable=False, default=0)
    last_quiz_reset = Column(DateTime, nullable=False, default=func.now())
    study_time_total = Column(Float, nullable=False, default=0)
    daily_quiz_history = Column(JSON, nullable=False, default=dict)
    settings = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            'quiz_time_today': self.quiz_time_today,
            'last_quiz_reset': self.last_quiz_reset.isoformat() if self.last_quiz_reset else None,
            'study_time_total': self.study_time_total,
            'daily_quiz_history': self.daily_quiz_history or {},
            'settings': self.settings or {}
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], user_id: str = 'anonymous') -> 'TimeTracking':
        """Create instance from dictionary data."""
        last_quiz_reset = data.get('last_quiz_reset')
        if isinstance(last_quiz_reset, str):
            try:
                from dateutil import parser
                last_quiz_reset = parser.parse(last_quiz_reset)
            except (ValueError, TypeError, OverflowError) as ex:
                import logging
                logging.getLogger(__name__).warning(f"Failed to parse last_quiz_reset: {last_quiz_reset!r} ({ex})")
                last_quiz_reset = datetime.now()
        elif last_quiz_reset is None:
            last_quiz_reset = datetime.now()
        
        return cls(
            user_id=user_id,
            quiz_time_today=data.get('quiz_time_today', 0),
            last_quiz_reset=last_quiz_reset,
            study_time_total=data.get('study_time_total', 0),
            daily_quiz_history=data.get('daily_quiz_history', {}),
            settings=data.get('settings', {})
        )


class AppSettings(Base):
    """Database model for application settings."""
    
    __tablename__ = 'app_settings'
    
    id = Column(Integer, primary_key=True)
    setting_key = Column(String(255), nullable=False, unique=True)
    setting_value = Column(JSON, nullable=False)
    setting_type = Column(String(50), nullable=False, default='json')
    description = Column(Text)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())