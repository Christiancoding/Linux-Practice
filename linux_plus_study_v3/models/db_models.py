#!/usr/bin/env python3
"""
Database Models for Separate Database Files

Defines SQLAlchemy models for each database file as per CLAUDE.md specifications.
"""

from sqlalchemy import Integer, DateTime, String, Float, Text, JSON, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import logging
import json
import zoneinfo

logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

# Learning Analytics Database (main database) - Privacy Focused
# Note: Use learning_analytics.py for new learning-only tracking

# Achievements Database
class UserAchievement(Base):
    """User achievements model for achievements database."""
    
    __tablename__ = 'user_achievements'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    badges: Mapped[str] = mapped_column(JSON, nullable=False)
    points_earned: Mapped[int] = mapped_column(Integer, nullable=False)
    days_studied: Mapped[str] = mapped_column(JSON, nullable=False)
    questions_answered: Mapped[int] = mapped_column(Integer, nullable=False)
    streaks_achieved: Mapped[int] = mapped_column(Integer, nullable=False)
    perfect_sessions: Mapped[int] = mapped_column(Integer, nullable=False)
    daily_warrior_dates: Mapped[str] = mapped_column(JSON, nullable=False)
    leaderboard: Mapped[str] = mapped_column(JSON, nullable=False)
    survival_high_score: Mapped[int] = mapped_column(Integer, nullable=False)
    survival_high_score_xp: Mapped[int] = mapped_column(Integer, nullable=False)
    custom_achievements: Mapped[str] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert UserAchievement to dictionary format."""
        import json
        return {
            'badges': json.loads(self.badges) if isinstance(self.badges, str) else self.badges,
            'points_earned': self.points_earned,
            'days_studied': json.loads(self.days_studied) if isinstance(self.days_studied, str) else self.days_studied,
            'questions_answered': self.questions_answered,
            'streaks_achieved': self.streaks_achieved,
            'perfect_sessions': self.perfect_sessions,
            'daily_warrior_dates': json.loads(self.daily_warrior_dates) if isinstance(self.daily_warrior_dates, str) else self.daily_warrior_dates,
            'leaderboard': json.loads(self.leaderboard) if isinstance(self.leaderboard, str) else self.leaderboard,
            'survival_high_score': self.survival_high_score,
            'survival_high_score_xp': self.survival_high_score_xp,
            'custom_achievements': json.loads(self.custom_achievements) if isinstance(self.custom_achievements, str) else self.custom_achievements
        }

# History Database
class UserHistory(Base):
    """User history model for history database."""
    
    __tablename__ = 'user_history'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    session_id: Mapped[str] = mapped_column(String(255), nullable=False)
    activity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    question_id: Mapped[Optional[str]] = mapped_column(String(255))
    answer_given: Mapped[Optional[str]] = mapped_column(String(255))
    correct_answer: Mapped[Optional[str]] = mapped_column(String(255))
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    time_taken: Mapped[Optional[float]] = mapped_column(Float)
    points_earned: Mapped[int] = mapped_column(Integer, nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(255))
    difficulty: Mapped[Optional[str]] = mapped_column(String(50))
    session_data: Mapped[Optional[str]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

# Questions Database
class Question(Base):
    """Questions model for questions database."""
    
    __tablename__ = 'questions'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    question_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    category: Mapped[str] = mapped_column(String(255), nullable=False)
    subcategory: Mapped[Optional[str]] = mapped_column(String(255))
    difficulty: Mapped[str] = mapped_column(String(50), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[Optional[str]] = mapped_column(JSON)
    correct_answer: Mapped[str] = mapped_column(String(255), nullable=False)
    explanation: Mapped[Optional[str]] = mapped_column(Text)
    links: Mapped[Optional[str]] = mapped_column(JSON)
    tags: Mapped[Optional[str]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

# Settings Database
class AppSetting(Base):
    """App settings model for settings database."""
    
    __tablename__ = 'app_settings'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    setting_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    setting_value: Mapped[str] = mapped_column(JSON, nullable=False)
    setting_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

# TimeTracking removed - contained user identification and behavioral tracking