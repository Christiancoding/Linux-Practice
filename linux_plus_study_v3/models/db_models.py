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

# Analytics Database (main database)
class Analytics(Base):
    """Analytics model for main database."""
    
    __tablename__ = 'analytics'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(zoneinfo.ZoneInfo("America/Chicago")), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(zoneinfo.ZoneInfo("America/Chicago")), onupdate=lambda: datetime.now(zoneinfo.ZoneInfo("America/Chicago")), nullable=False)
    
    # Session tracking
    user_id: Mapped[Optional[str]] = mapped_column(String(255))
    session_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    session_start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    session_end: Mapped[Optional[datetime]] = mapped_column(DateTime)
    session_duration: Mapped[Optional[float]] = mapped_column(Float)
    
    # Activity tracking
    activity_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    activity_subtype: Mapped[Optional[str]] = mapped_column(String(100))
    topic_area: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    difficulty_level: Mapped[Optional[str]] = mapped_column(String(50))
    
    # Quiz performance metrics
    questions_attempted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    questions_correct: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    questions_incorrect: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    accuracy_percentage: Mapped[Optional[float]] = mapped_column(Float)
    completion_percentage: Mapped[Optional[float]] = mapped_column(Float)
    time_per_question: Mapped[Optional[float]] = mapped_column(Float)
    
    # Engagement metrics
    content_pages_viewed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    time_on_content: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    practice_commands_executed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    vm_sessions_started: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cli_playground_usage: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    
    # Progress tracking
    study_streak_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    return_sessions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    help_requests: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    hint_usage: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    review_sessions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    
    # JSON fields for complex data
    achievements_unlocked: Mapped[Optional[str]] = mapped_column(Text)
    skill_assessments: Mapped[Optional[str]] = mapped_column(JSON)
    
    # Additional metrics
    learning_goals_met: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    certification_progress: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    page_load_time: Mapped[Optional[float]] = mapped_column(Float)
    error_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    feature_usage: Mapped[Optional[str]] = mapped_column(JSON)
    browser_info: Mapped[Optional[str]] = mapped_column(String(255))
    device_type: Mapped[Optional[str]] = mapped_column(String(50))
    
    # VM specific metrics
    vm_uptime: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    vm_commands_executed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lab_exercises_completed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lab_exercises_attempted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    vm_errors_encountered: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    
    # Learning analytics
    concept_mastery_scores: Mapped[Optional[str]] = mapped_column(JSON)
    retention_test_scores: Mapped[Optional[str]] = mapped_column(JSON)
    practical_application_success: Mapped[Optional[float]] = mapped_column(Float)
    active_learning_time: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    interaction_frequency: Mapped[Optional[float]] = mapped_column(Float)
    focus_score: Mapped[Optional[float]] = mapped_column(Float)
    
    # Feedback and improvement
    user_feedback_rating: Mapped[Optional[float]] = mapped_column(Float)
    improvement_suggestions: Mapped[Optional[str]] = mapped_column(Text)
    difficulty_rating: Mapped[Optional[float]] = mapped_column(Float)
    preferred_learning_style: Mapped[Optional[str]] = mapped_column(String(100))
    most_effective_study_method: Mapped[Optional[str]] = mapped_column(String(100))
    least_effective_study_method: Mapped[Optional[str]] = mapped_column(String(100))
    
    # Additional fields
    notes: Mapped[Optional[str]] = mapped_column(Text)
    tags: Mapped[Optional[str]] = mapped_column(JSON)
    custom_metrics: Mapped[Optional[str]] = mapped_column(JSON)

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

class TimeTracking(Base):
    """Time tracking model for settings database."""
    
    __tablename__ = 'time_tracking'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    quiz_time_today: Mapped[float] = mapped_column(Float, nullable=False)
    last_quiz_reset: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    study_time_total: Mapped[float] = mapped_column(Float, nullable=False)
    daily_quiz_history: Mapped[str] = mapped_column(JSON, nullable=False)
    settings: Mapped[str] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)