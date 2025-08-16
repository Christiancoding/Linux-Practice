"""
Learning Analytics Model - Educational Data Only

Privacy-focused model that tracks only learning progress and educational outcomes.
No user identification, device tracking, or behavioral surveillance.
"""

from sqlalchemy import Integer, DateTime, String, Float, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from datetime import datetime
from typing import Dict, Any, Optional
import logging
import zoneinfo

class Base(DeclarativeBase):
    pass

logger = logging.getLogger(__name__)

class LearningAnalytics(Base):
    """Privacy-focused learning analytics model for educational progress tracking."""
    
    __tablename__ = 'learning_analytics'
    
    # Primary key and timestamps
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(zoneinfo.ZoneInfo("America/Chicago")), nullable=False)
    
    # Learning Activity Context
    activity_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)  # quiz, study, practice
    topic_area: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)  # Linux topic being studied
    difficulty_level: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # beginner, intermediate, advanced
    
    # Educational Performance Metrics
    questions_attempted: Mapped[int] = mapped_column(Integer, default=0)
    questions_correct: Mapped[int] = mapped_column(Integer, default=0)
    accuracy_percentage: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    completion_percentage: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    time_per_question: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # average seconds per question
    
    # Study Progress and Learning Outcomes
    study_time_seconds: Mapped[float] = mapped_column(Float, default=0.0)  # time spent on educational content
    mastery_level: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 0-1 scale of topic mastery
    learning_objective_met: Mapped[bool] = mapped_column(Integer, default=0)  # SQLite boolean as integer
    
    # Achievement and Progress Tracking (Educational Only)
    achievement_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Educational achievement unlocked
    points_earned: Mapped[int] = mapped_column(Integer, default=0)  # Learning points
    skill_level: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # Current skill level in topic
    
    # Learning Method Effectiveness
    study_method: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # quiz, reading, practice, hands-on
    effectiveness_rating: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # How effective this method was
    
    # Additional educational metadata
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Learning notes or feedback
    
    def __repr__(self):
        return f"<LearningAnalytics(id={self.id}, activity_type={self.activity_type}, topic_area={self.topic_area})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary for JSON compatibility."""
        return {
            'id': self.id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'activity_type': self.activity_type,
            'topic_area': self.topic_area,
            'difficulty_level': self.difficulty_level,
            'questions_attempted': self.questions_attempted,
            'questions_correct': self.questions_correct,
            'accuracy_percentage': self.accuracy_percentage,
            'completion_percentage': self.completion_percentage,
            'time_per_question': self.time_per_question,
            'study_time_seconds': self.study_time_seconds,
            'mastery_level': self.mastery_level,
            'learning_objective_met': bool(self.learning_objective_met),
            'achievement_name': self.achievement_name,
            'points_earned': self.points_earned,
            'skill_level': self.skill_level,
            'study_method': self.study_method,
            'effectiveness_rating': self.effectiveness_rating,
            'notes': self.notes
        }
    
    def calculate_learning_metrics(self) -> Dict[str, float]:
        """Calculate educational performance metrics."""
        metrics: Dict[str, float] = {}
        
        # Quiz performance
        if self.questions_attempted and self.questions_attempted > 0:
            metrics['success_rate'] = (self.questions_correct or 0) / self.questions_attempted
            metrics['error_rate'] = ((self.questions_attempted - self.questions_correct) or 0) / self.questions_attempted
        
        # Learning efficiency
        if self.study_time_seconds and self.study_time_seconds > 0:
            metrics['questions_per_minute'] = (self.questions_attempted or 0) / (self.study_time_seconds / 60)
        
        # Mastery progression
        if self.mastery_level:
            metrics['mastery_level'] = self.mastery_level
        
        return metrics
    
    def update_quiz_performance(self, correct: bool, time_taken: Optional[float] = None):
        """Update educational quiz performance metrics."""
        self.questions_attempted = (self.questions_attempted or 0) + 1
        if correct:
            self.questions_correct = (self.questions_correct or 0) + 1
        
        # Update accuracy percentage
        if self.questions_attempted > 0:
            self.accuracy_percentage = (self.questions_correct or 0) / self.questions_attempted
        
        # Update average time per question
        if time_taken:
            if self.time_per_question is None:
                self.time_per_question = time_taken
            else:
                # Calculate running average
                total_time = self.time_per_question * (self.questions_attempted - 1) + time_taken
                self.time_per_question = total_time / self.questions_attempted
    
    def record_achievement(self, achievement_name: str, points: int = 0):
        """Record an educational achievement."""
        self.achievement_name = achievement_name
        self.points_earned = (self.points_earned or 0) + points
    
    def add_study_time(self, seconds: float):
        """Add to educational study time."""
        self.study_time_seconds = (self.study_time_seconds or 0) + seconds
    
    def update_mastery_level(self, level: float):
        """Update mastery level for a topic (0.0 to 1.0)."""
        self.mastery_level = max(0.0, min(1.0, level))
    
    def set_learning_objective_met(self, met: bool = True):
        """Mark learning objective as met."""
        self.learning_objective_met = 1 if met else 0
    
    def set_study_method_effectiveness(self, method: str, rating: float):
        """Record effectiveness of a study method."""
        self.study_method = method
        self.effectiveness_rating = max(0.0, min(5.0, rating))  # 0-5 scale
    
    def get_learning_summary(self) -> Dict[str, Any]:
        """Get a summary of learning progress."""
        return {
            'total_questions': self.questions_attempted or 0,
            'accuracy': round((self.accuracy_percentage or 0) * 100, 1),
            'study_time_minutes': round((self.study_time_seconds or 0) / 60, 1),
            'mastery_level': round((self.mastery_level or 0) * 100, 1),
            'points_earned': self.points_earned or 0,
            'objective_met': bool(self.learning_objective_met),
            'skill_level': self.skill_level,
            'effectiveness': self.effectiveness_rating
        }
    
    @staticmethod
    def get_activity_types():
        """Get list of valid learning activity types."""
        return ['quiz', 'study', 'practice', 'review', 'assessment']
    
    @staticmethod
    def get_difficulty_levels():
        """Get list of valid difficulty levels."""
        return ['beginner', 'intermediate', 'advanced', 'expert']
    
    @staticmethod
    def get_study_methods():
        """Get list of study methods."""
        return ['quiz', 'reading', 'practice', 'hands_on', 'video', 'tutorial']


# Learning Analytics Service Functions
class LearningAnalyticsService:
    """Service class for learning analytics operations."""
    
    def __init__(self, db_session: Any):
        self.db = db_session
    
    def create_learning_session(self, activity_type: str, **kwargs: Any) -> LearningAnalytics:
        """Create a new learning analytics session."""
        learning_session = LearningAnalytics(
            activity_type=activity_type,
            **kwargs
        )
        self.db.add(learning_session)
        self.db.commit()
        return learning_session
    
    def get_topic_progress(self, topic_area: str, limit: int = 100) -> list[LearningAnalytics]:
        """Get learning progress for a specific topic."""
        return self.db.query(LearningAnalytics).filter_by(topic_area=topic_area).limit(limit).all()
    
    def get_activity_progress(self, activity_type: str, limit: int = 100) -> list[LearningAnalytics]:
        """Get progress for a specific learning activity type."""
        return self.db.query(LearningAnalytics).filter_by(activity_type=activity_type).limit(limit).all()
    
    def update_learning_session(self, session_id: int, **updates: Any) -> Optional[LearningAnalytics]:
        """Update learning session with new educational data."""
        session = self.db.query(LearningAnalytics).filter_by(id=session_id).first()
        if session:
            for key, value in updates.items():
                if hasattr(session, key):
                    setattr(session, key, value)
            self.db.commit()
        return session
    
    def get_learning_summary(self) -> Dict[str, Any]:
        """Get overall learning progress summary."""
        all_sessions = self.db.query(LearningAnalytics).all()
        
        if not all_sessions:
            return {'total_sessions': 0}
        
        summary = {
            'total_sessions': len(all_sessions),
            'total_questions': sum(s.questions_attempted or 0 for s in all_sessions),
            'total_correct': sum(s.questions_correct or 0 for s in all_sessions),
            'total_study_time': sum(s.study_time_seconds or 0 for s in all_sessions),
            'total_points': sum(s.points_earned or 0 for s in all_sessions),
            'topics_studied': len(set(s.topic_area for s in all_sessions if s.topic_area)),
            'average_accuracy': 0,
            'objectives_met': sum(1 for s in all_sessions if s.learning_objective_met)
        }
        
        # Calculate overall accuracy
        if summary['total_questions'] > 0:
            summary['average_accuracy'] = (summary['total_correct'] / summary['total_questions']) * 100
        
        return summary