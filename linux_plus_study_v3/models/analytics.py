"""
Analytics Model - Data Management

Enhanced model with SQLAlchemy ORM support and
backward compatibility with JSON-based storage.
"""

from sqlalchemy import Integer, DateTime, String, Float, Text, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import logging
import json
import zoneinfo

class Base(DeclarativeBase):
    pass

logger = logging.getLogger(__name__)

class Analytics(Base):
    """Enhanced analytics model with comprehensive tracking capabilities."""
    
    __tablename__ = 'analytics'
    
    # Primary key and timestamps
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(zoneinfo.ZoneInfo("America/Chicago")), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(zoneinfo.ZoneInfo("America/Chicago")), onupdate=lambda: datetime.now(zoneinfo.ZoneInfo("America/Chicago")), nullable=False)
    
    # User and Session Tracking
    user_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)  # Anonymous tracking support
    session_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    session_start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    session_end: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    session_duration: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # in seconds
    
    # Activity Type and Context
    activity_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)  # quiz, study, practice, vm_lab, cli_playground
    activity_subtype: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # specific quiz mode, topic area, etc.
    topic_area: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)  # Linux topic being studied
    difficulty_level: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # beginner, intermediate, advanced
    
    # Quiz and Learning Performance
    questions_attempted: Mapped[int] = mapped_column(Integer, default=0)
    questions_correct: Mapped[int] = mapped_column(Integer, default=0)
    questions_incorrect: Mapped[int] = mapped_column(Integer, default=0)
    accuracy_percentage: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    completion_percentage: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    time_per_question: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # average seconds per question
    
    # Study Progress and Engagement
    content_pages_viewed: Mapped[int] = mapped_column(Integer, default=0)
    practice_commands_executed: Mapped[int] = mapped_column(Integer, default=0)
    vm_sessions_started: Mapped[int] = mapped_column(Integer, default=0)
    cli_playground_usage: Mapped[int] = mapped_column(Integer, default=0)
    
    # Learning Patterns and Behavior
    study_streak_days: Mapped[int] = mapped_column(Integer, default=0)
    return_sessions: Mapped[int] = mapped_column(Integer, default=0)  # number of times returned to same topic
    help_requests: Mapped[int] = mapped_column(Integer, default=0)
    hint_usage: Mapped[int] = mapped_column(Integer, default=0)
    review_sessions: Mapped[int] = mapped_column(Integer, default=0)
    
    # Achievement and Progress Tracking
    achievements_unlocked: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string of achievement IDs list
    skill_assessments: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)  # Skill level assessments
    learning_goals_met: Mapped[int] = mapped_column(Integer, default=0)
    certification_progress: Mapped[float] = mapped_column(Float, default=0.0)  # percentage toward certification
    
    # Technical Performance Metrics
    page_load_time: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # milliseconds
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    feature_usage: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)  # Track which features are used
    browser_info: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    device_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # desktop, mobile, tablet
    
    # VM and Lab Environment
    vm_uptime: Mapped[float] = mapped_column(Float, default=0.0)  # total VM usage time in seconds
    vm_commands_executed: Mapped[int] = mapped_column(Integer, default=0)
    lab_exercises_completed: Mapped[int] = mapped_column(Integer, default=0)
    lab_exercises_attempted: Mapped[int] = mapped_column(Integer, default=0)
    vm_errors_encountered: Mapped[int] = mapped_column(Integer, default=0)
    
    # Learning Effectiveness
    concept_mastery_scores: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)  # Track mastery of different concepts
    retention_test_scores: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)  # Scores on retention tests
    practical_application_success: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Success rate in practical exercises
    
    # Engagement Quality Metrics
    interaction_frequency: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Interactions per minute
    focus_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Measure of sustained attention
    
    # Feedback and Improvement
    user_feedback_rating: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 1-5 rating if provided
    improvement_suggestions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    difficulty_rating: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # User's perception of difficulty
    
    # Study Method Effectiveness
    preferred_learning_style: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # visual, hands-on, reading, etc.
    most_effective_study_method: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    least_effective_study_method: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Additional metadata
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)  # Flexible tagging system
    custom_metrics: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)  # For future extensibility
    
    def __repr__(self):
        return f"<Analytics(id={self.id}, activity_type={self.activity_type}, session_id={self.session_id})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary for JSON compatibility."""
        # Helper function to safely convert datetime to isoformat
        def safe_isoformat(dt: Optional[datetime]) -> Optional[str]:
            return dt.isoformat() if dt else None
        
        # Helper function to parse achievements
        def parse_achievements() -> Optional[list[str]]:
            if self.achievements_unlocked:
                try:
                    return json.loads(self.achievements_unlocked)
                except (json.JSONDecodeError, TypeError):
                    return []
            return None
        
        result: Dict[str, Any] = {
            'id': self.id,
            'created_at': safe_isoformat(self.created_at),
            'updated_at': safe_isoformat(self.updated_at),
            'user_id': self.user_id,
            'session_id': self.session_id,
            'session_start': safe_isoformat(self.session_start),
            'session_end': safe_isoformat(self.session_end),
            'session_duration': self.session_duration,
            'activity_type': self.activity_type,
            'activity_subtype': self.activity_subtype,
            'topic_area': self.topic_area,
            'difficulty_level': self.difficulty_level,
            'questions_attempted': self.questions_attempted,
            'questions_correct': self.questions_correct,
            'questions_incorrect': self.questions_incorrect,
            'accuracy_percentage': self.accuracy_percentage,
            'completion_percentage': self.completion_percentage,
            'time_per_question': self.time_per_question,
            'content_pages_viewed': self.content_pages_viewed,
            'practice_commands_executed': self.practice_commands_executed,
            'vm_sessions_started': self.vm_sessions_started,
            'cli_playground_usage': self.cli_playground_usage,
            'study_streak_days': self.study_streak_days,
            'return_sessions': self.return_sessions,
            'help_requests': self.help_requests,
            'hint_usage': self.hint_usage,
            'review_sessions': self.review_sessions,
            'achievements_unlocked': parse_achievements(),
            'skill_assessments': self.skill_assessments,
            'learning_goals_met': self.learning_goals_met,
            'certification_progress': self.certification_progress,
            'page_load_time': self.page_load_time,
            'error_count': self.error_count,
            'feature_usage': self.feature_usage,
            'browser_info': self.browser_info,
            'device_type': self.device_type,
            'vm_uptime': self.vm_uptime,
            'vm_commands_executed': self.vm_commands_executed,
            'lab_exercises_completed': self.lab_exercises_completed,
            'lab_exercises_attempted': self.lab_exercises_attempted,
            'vm_errors_encountered': self.vm_errors_encountered,
            'concept_mastery_scores': self.concept_mastery_scores,
            'retention_test_scores': self.retention_test_scores,
            'practical_application_success': self.practical_application_success,
            'interaction_frequency': self.interaction_frequency,
            'focus_score': self.focus_score,
            'user_feedback_rating': self.user_feedback_rating,
            'improvement_suggestions': self.improvement_suggestions,
            'difficulty_rating': self.difficulty_rating,
            'preferred_learning_style': self.preferred_learning_style,
            'most_effective_study_method': self.most_effective_study_method,
            'least_effective_study_method': self.least_effective_study_method,
            'notes': self.notes,
            'tags': self.tags,
            'custom_metrics': self.custom_metrics
        }
        return result
    
    def calculate_performance_metrics(self) -> Dict[str, float]:
        """Calculate derived performance metrics."""
        metrics: Dict[str, float] = {}
        
        # Quiz performance
        if self.questions_attempted and self.questions_attempted > 0:
            metrics['accuracy_rate'] = (self.questions_correct or 0) / self.questions_attempted
            metrics['error_rate'] = (self.questions_incorrect or 0) / self.questions_attempted
        
        # Efficiency metrics
        if self.session_duration and self.session_duration > 0:
            metrics['questions_per_minute'] = (self.questions_attempted or 0) / (self.session_duration / 60)
            metrics['pages_per_minute'] = (self.content_pages_viewed or 0) / (self.session_duration / 60)
        
        
        # VM productivity
        if self.vm_uptime and self.vm_uptime > 0:
            metrics['vm_commands_per_minute'] = (self.vm_commands_executed or 0) / (self.vm_uptime / 60)
        
        # Lab success rate
        if self.lab_exercises_attempted and self.lab_exercises_attempted > 0:
            metrics['lab_success_rate'] = (self.lab_exercises_completed or 0) / self.lab_exercises_attempted
        
        return metrics
    
    def get_learning_insights(self) -> Dict[str, Any]:
        """Generate learning insights based on analytics data."""
        insights: Dict[str, list[str]] = {
            'strengths': [],
            'areas_for_improvement': [],
            'recommendations': []
        }
        
        # Analyze quiz performance
        if self.accuracy_percentage:
            if self.accuracy_percentage >= 0.8:
                insights['strengths'].append(f"Strong performance in {self.topic_area or 'current topic'}")
            elif self.accuracy_percentage < 0.6:
                insights['areas_for_improvement'].append(f"Need more practice with {self.topic_area or 'current topic'}")
        
        # Analyze engagement patterns
        if self.help_requests and self.hint_usage:
            if (self.help_requests + self.hint_usage) > 0:
                insights['recommendations'].append("Consider reviewing foundational concepts")
        
        # Analyze study consistency
        if self.study_streak_days and self.study_streak_days > 7:
            insights['strengths'].append("Excellent study consistency")
        elif self.study_streak_days and self.study_streak_days < 3:
            insights['recommendations'].append("Try to establish a more consistent study routine")
        
        # VM usage insights
        if self.vm_commands_executed and self.vm_commands_executed > 50:
            insights['strengths'].append("Good hands-on practice with command line")
        
        return insights
    
    def end_session(self):
        """Mark session as ended and calculate duration."""
        if self.session_end is None:
            end_time = datetime.now(zoneinfo.ZoneInfo("America/Chicago"))
            self.session_end = end_time
            if self.session_start:
                # Ensure both timestamps are timezone-aware
                if self.session_start.tzinfo is None:
                    # If session_start is naive, assume it's Chicago time
                    session_start_chicago = self.session_start.replace(tzinfo=zoneinfo.ZoneInfo("America/Chicago"))
                else:
                    session_start_chicago = self.session_start
                
                # Calculate duration using the local end_time variable
                self.session_duration = (end_time - session_start_chicago).total_seconds()
    
    @classmethod
    def create_session(cls, session_id: str, activity_type: str, **kwargs: Any) -> 'Analytics':
        """Create a new analytics session."""
        return cls(
            session_id=session_id,
            activity_type=activity_type,
            session_start=datetime.now(zoneinfo.ZoneInfo("America/Chicago")),
            **kwargs
        )
    
    def update_quiz_performance(self, correct: bool, time_taken: Optional[float] = None):
        """Update quiz performance metrics."""
        self.questions_attempted = (self.questions_attempted or 0) + 1
        if correct:
            self.questions_correct = (self.questions_correct or 0) + 1
        else:
            self.questions_incorrect = (self.questions_incorrect or 0) + 1
        
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
    
    def add_vm_command(self, execution_time: Optional[float] = None):
        """Track VM command execution."""
        self.vm_commands_executed = (self.vm_commands_executed or 0) + 1
        if execution_time:
            self.vm_uptime = (self.vm_uptime or 0) + execution_time
    
    def record_achievement(self, achievement_id: str):
        """Record a new achievement."""
        if not self.achievements_unlocked:
            self.achievements_unlocked = json.dumps([])
        
        # Parse existing achievements
        try:
            achievements_list: list[str] = json.loads(self.achievements_unlocked)
        except (json.JSONDecodeError, TypeError):
            achievements_list = []
        
        if achievement_id not in achievements_list:
            achievements_list.append(achievement_id)
            self.achievements_unlocked = json.dumps(achievements_list)
    
    def update_feature_usage(self, feature_name: str, usage_count: int = 1):
        """Track feature usage."""
        if not self.feature_usage:
            self.feature_usage = {}
        self.feature_usage[feature_name] = self.feature_usage.get(feature_name, 0) + usage_count
    
    def increment_page_view(self, page_name: Optional[str] = None):
        """Track content page views."""
        self.content_pages_viewed = (self.content_pages_viewed or 0) + 1
        if page_name:
            self.update_feature_usage(f"page_view_{page_name}")
    
    
    def record_help_request(self, help_type: Optional[str] = None):
        """Track help requests."""
        self.help_requests = (self.help_requests or 0) + 1
        if help_type:
            self.update_feature_usage(f"help_{help_type}")
    
    def record_hint_usage(self, hint_type: Optional[str] = None):
        """Track hint usage."""
        self.hint_usage = (self.hint_usage or 0) + 1
        if hint_type:
            self.update_feature_usage(f"hint_{hint_type}")
    
    def update_concept_mastery(self, concept: str, score: float):
        """Update mastery score for a specific concept."""
        if not self.concept_mastery_scores:
            self.concept_mastery_scores = {}
        self.concept_mastery_scores[concept] = score
    
    def record_error(self, error_type: Optional[str] = None):
        """Track errors encountered."""
        self.error_count = (self.error_count or 0) + 1
        if error_type:
            self.update_feature_usage(f"error_{error_type}")
    
    def start_vm_session(self):
        """Track VM session start."""
        self.vm_sessions_started = (self.vm_sessions_started or 0) + 1
    
    def complete_lab_exercise(self, success: bool = True):
        """Track lab exercise completion."""
        self.lab_exercises_attempted = (self.lab_exercises_attempted or 0) + 1
        if success:
            self.lab_exercises_completed = (self.lab_exercises_completed or 0) + 1
    
    def update_cli_usage(self):
        """Track CLI playground usage."""
        self.cli_playground_usage = (self.cli_playground_usage or 0) + 1
    
    def set_user_feedback(self, rating: float, suggestions: Optional[str] = None, difficulty: Optional[float] = None):
        """Record user feedback."""
        self.user_feedback_rating = rating
        if suggestions:
            self.improvement_suggestions = suggestions
        if difficulty:
            self.difficulty_rating = difficulty
    
    def update_learning_preferences(self, preferred_style: Optional[str] = None, 
                                  effective_method: Optional[str] = None, 
                                  ineffective_method: Optional[str] = None):
        """Update learning preference data."""
        if preferred_style:
            self.preferred_learning_style = preferred_style
        if effective_method:
            self.most_effective_study_method = effective_method
        if ineffective_method:
            self.least_effective_study_method = ineffective_method
    
    def get_custom_metrics(self) -> Dict[str, Any]:
        """Get custom metrics dictionary."""
        if self.custom_metrics is None:
            return {}
        return self.custom_metrics
    
    def set_custom_metrics(self, metrics: Dict[str, Any]) -> None:
        """Set custom metrics dictionary."""
        self.custom_metrics = metrics
        self.updated_at = datetime.now(zoneinfo.ZoneInfo("America/Chicago"))
    
    def update_custom_metric(self, key: str, value: Any) -> None:
        """Update a single custom metric."""
        if self.custom_metrics is None:
            self.custom_metrics = {}
        self.custom_metrics[key] = value
        self.updated_at = datetime.now(zoneinfo.ZoneInfo("America/Chicago"))
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """Get a summary of key statistics."""
        return {
            'total_questions': self.questions_attempted or 0,
            'accuracy': round((self.accuracy_percentage or 0) * 100, 1),
            'vm_commands': self.vm_commands_executed or 0,
            'pages_viewed': self.content_pages_viewed or 0,
            'achievements': len(json.loads(self.achievements_unlocked or "[]")),
            'session_duration_minutes': round((self.session_duration or 0) / 60, 1),
            'lab_success_rate': round(
                ((self.lab_exercises_completed or 0) / max(self.lab_exercises_attempted or 1, 1)) * 100, 1
            )
        }
    
    @staticmethod
    def get_activity_types():
        """Get list of valid activity types."""
        return [
            'quiz', 'study', 'practice', 'vm_lab', 'cli_playground',
            'review', 'assessment', 'tutorial', 'exploration'
        ]
    
    @staticmethod
    def get_difficulty_levels():
        """Get list of valid difficulty levels."""
        return ['beginner', 'intermediate', 'advanced', 'expert']
    
    @staticmethod
    def get_learning_styles():
        """Get list of learning styles."""
        return [
            'visual', 'auditory', 'kinesthetic', 'reading_writing',
            'hands_on', 'theoretical', 'practical', 'collaborative'
        ]


# Analytics Service Functions for Web Integration
class AnalyticsService:
    """Service class for analytics operations."""
    
    def __init__(self, db_session: Any):
        self.db = db_session
    
    def create_session_analytics(self, session_id: str, activity_type: str, 
                                user_id: Optional[str] = None, **kwargs: Any) -> Analytics:
        """Create a new analytics session."""
        analytics = Analytics.create_session(
            session_id=session_id,
            activity_type=activity_type,
            user_id=user_id,
            **kwargs
        )
        self.db.add(analytics)
        self.db.commit()
        return analytics
    
    def get_session_analytics(self, session_id: str) -> Optional[Analytics]:
        """Get analytics for a specific session."""
        return self.db.query(Analytics).filter_by(session_id=session_id).first()
    
    def get_user_analytics(self, user_id: str, limit: int = 100) -> list[Analytics]:
        """Get analytics for a specific user."""
        return self.db.query(Analytics).filter_by(user_id=user_id).limit(limit).all()
    
    def get_topic_analytics(self, topic_area: str, limit: int = 100) -> list[Analytics]:
        """Get analytics for a specific topic."""
        return self.db.query(Analytics).filter_by(topic_area=topic_area).limit(limit).all()
    
    def get_activity_analytics(self, activity_type: str, limit: int = 100) -> list[Analytics]:
        """Get analytics for a specific activity type."""
        return self.db.query(Analytics).filter_by(activity_type=activity_type).limit(limit).all()
    
    def end_session_analytics(self, session_id: str) -> Optional[Analytics]:
        """End an analytics session."""
        analytics = self.get_session_analytics(session_id)
        if analytics:
            analytics.end_session()
            self.db.commit()
        return analytics
    
    def update_session_analytics(self, session_id: str, **updates: Any) -> Optional[Analytics]:
        """Update analytics session with new data."""
        analytics = self.get_session_analytics(session_id)
        if analytics:
            for key, value in updates.items():
                if hasattr(analytics, key):
                    setattr(analytics, key, value)
            analytics.updated_at = datetime.now(zoneinfo.ZoneInfo("America/Chicago"))
            self.db.commit()
        return analytics
    
    def get_user_summary(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive user analytics summary."""
        user_sessions = self.get_user_analytics(user_id)
        
        if not user_sessions:
            return {'total_sessions': 0}
        
        # Get all achievements from all sessions
        all_achievements: set[str] = set()
        for session in user_sessions:
            if session.achievements_unlocked:
                try:
                    achievements_list = json.loads(session.achievements_unlocked)
                    all_achievements.update(achievements_list)
                except (json.JSONDecodeError, TypeError):
                    pass
        
        summary: Dict[str, Any] = {
            'total_sessions': len(user_sessions),
            'total_questions': sum(s.questions_attempted or 0 for s in user_sessions),
            'total_correct': sum(s.questions_correct or 0 for s in user_sessions),
            'overall_accuracy': 0,
            'total_vm_commands': sum(s.vm_commands_executed or 0 for s in user_sessions),
            'total_achievements': len(all_achievements),
            'activity_breakdown': {},
            'topic_breakdown': {},
            'recent_performance': [],
            'study_streak': self._calculate_study_streak(user_id),
            'return_sessions': sum(s.return_sessions or 0 for s in user_sessions),
            'help_requests': sum(s.help_requests or 0 for s in user_sessions),
            'hint_usage': sum(s.hint_usage or 0 for s in user_sessions),
            'review_sessions': sum(s.review_sessions or 0 for s in user_sessions),
            'average_session_duration': sum(s.session_duration or 0 for s in user_sessions) / len(user_sessions) if user_sessions else 0,
            'achievements_unlocked': list(all_achievements),
            'skill_assessments': {k: v for s in user_sessions for k, v in (s.skill_assessments or {}).items()},
            'learning_goals_met': sum(s.learning_goals_met or 0 for s in user_sessions),
            'certification_progress': sum(s.certification_progress or 0 for s in user_sessions) / len(user_sessions) if user_sessions else 0,
            'page_load_time': sum(s.page_load_time or 0 for s in user_sessions) / len(user_sessions) if user_sessions else 0,
            'error_count': sum(s.error_count or 0 for s in user_sessions),
            'feature_usage': {k: sum(s.feature_usage.get(k, 0) for s in user_sessions) for k in set(k for s in user_sessions for k in (s.feature_usage or {}).keys())},
            'browser_info': list({s.browser_info for s in user_sessions if s.browser_info}),
            'device_type': list({s.device_type for s in user_sessions if s.device_type}),
            'vm_uptime': sum(s.vm_uptime or 0 for s in user_sessions),
            'vm_commands_executed': sum(s.vm_commands_executed or 0 for s in user_sessions),
            'lab_exercises_completed': sum(s.lab_exercises_completed or 0 for s in user_sessions),
            'lab_exercises_attempted': sum(s.lab_exercises_attempted or 0 for s in user_sessions),
            'vm_errors_encountered': sum(s.vm_errors_encountered or 0 for s in user_sessions),
            'concept_mastery_scores': {k: v for s in user_sessions for k, v in (s.concept_mastery_scores or {}).items()},
            'retention_test_scores': {k: v for s in user_sessions for k, v in (s.retention_test_scores or {}).items()},
            'practical_application_success': sum(s.practical_application_success or 0 for s in user_sessions) / len(user_sessions) if user_sessions else 0,
            'interaction_frequency': sum(s.interaction_frequency or 0 for s in user_sessions),
            'focus_score': sum(s.focus_score or 0 for s in user_sessions) / len(user_sessions) if user_sessions else 0,
            'user_feedback_rating': sum(s.user_feedback_rating or 0 for s in user_sessions) / len(user_sessions) if user_sessions else 0,
            'improvement_suggestions': [s.improvement_suggestions for s in user_sessions if s.improvement_suggestions],
            'difficulty_rating': sum(s.difficulty_rating or 0 for s in user_sessions) / len(user_sessions) if user_sessions else 0,
            'preferred_learning_style': list({s.preferred_learning_style for s in user_sessions if s.preferred_learning_style}),
            'most_effective_study_method': list({s.most_effective_study_method for s in user_sessions if s.most_effective_study_method}),
            'least_effective_study_method': list({s.least_effective_study_method for s in user_sessions if s.least_effective_study_method}),
            'notes': [s.notes for s in user_sessions if s.notes],
            'tags': {k: v for s in user_sessions for k, v in (s.tags or {}).items()},
            'custom_metrics': {k: v for s in user_sessions for k, v in (s.custom_metrics or {}).items()}
        }
        
        # Calculate overall accuracy
        if summary['total_questions'] > 0:
            summary['overall_accuracy'] = (summary['total_correct'] / summary['total_questions']) * 100
        
        # Activity breakdown
        for session in user_sessions:
            activity = session.activity_type
            summary['activity_breakdown'][activity] = summary['activity_breakdown'].get(activity, 0) + 1
        
        # Topic breakdown
        for session in user_sessions:
            if session.topic_area:
                topic = session.topic_area
                summary['topic_breakdown'][topic] = summary['topic_breakdown'].get(topic, 0) + 1
        
        # Recent performance (last 10 sessions)
        recent_sessions = sorted(user_sessions, key=lambda x: x.created_at, reverse=True)[:10]
        summary['recent_performance'] = [
            {
                'date': s.created_at.isoformat(),
                'activity': s.activity_type,
                'accuracy': (s.accuracy_percentage or 0) * 100,
                'questions': s.questions_attempted or 0
            }
            for s in recent_sessions
        ]
        
        return summary
    
    def get_global_statistics(self) -> Dict[str, Any]:
        """Get global application statistics."""
        all_analytics = self.db.query(Analytics).all()
        
        if not all_analytics:
            return {'total_sessions': 0}
        
        stats: Dict[str, Any] = {
            'total_sessions': len(all_analytics),
            'total_users': len(set(s.user_id for s in all_analytics if s.user_id)),
            'total_questions_answered': sum(s.questions_attempted or 0 for s in all_analytics),
            'average_accuracy': 0,
            'most_popular_activities': {},
            'most_studied_topics': {},
            'average_session_duration': 0
        }
        
        # Calculate averages
        valid_accuracy_sessions = [s for s in all_analytics if s.accuracy_percentage is not None]
        if valid_accuracy_sessions:
            stats['average_accuracy'] = sum(s.accuracy_percentage for s in valid_accuracy_sessions) / len(valid_accuracy_sessions) * 100
        
        valid_duration_sessions = [s for s in all_analytics if s.session_duration is not None]
        if valid_duration_sessions:
            stats['average_session_duration'] = sum(s.session_duration for s in valid_duration_sessions) / len(valid_duration_sessions) / 60  # in minutes
        
        # Activity popularity
        for session in all_analytics:
            activity = session.activity_type
            stats['most_popular_activities'][activity] = stats['most_popular_activities'].get(activity, 0) + 1
        
        # Topic popularity
        for session in all_analytics:
            if session.topic_area:
                topic = session.topic_area
                stats['most_studied_topics'][topic] = stats['most_studied_topics'].get(topic, 0) + 1
        
        return stats
    
    def _calculate_study_streak(self, user_id: str) -> int:
        """Calculate the current study streak for a user."""
        try:
            from datetime import datetime, timedelta
            from sqlalchemy import func
            
            # Handle anonymous user lookup
            query_user_id = user_id
            if user_id == 'anonymous':
                # Check for demo user data first
                demo_sessions = self.db.query(
                    func.date(Analytics.session_start).label('session_date')
                ).filter(
                    Analytics.user_id == 'demo_user_001'
                ).distinct().order_by(func.date(Analytics.session_start).desc()).all()
                
                if demo_sessions:
                    query_user_id = 'demo_user_001'
                else:
                    query_user_id = None  # For anonymous users with no demo data
            
            # Get all session dates for the user (use session_start instead of created_at)
            if query_user_id:
                query_filter = Analytics.user_id == query_user_id
            else:
                query_filter = Analytics.user_id.is_(None)
                
            sessions = self.db.query(
                func.date(Analytics.session_start).label('session_date')
            ).filter(query_filter).distinct().order_by(func.date(Analytics.session_start).desc()).all()
            
            if not sessions:
                return 0
            
            streak = 0
            current_date = datetime.now().date()
            
            # Convert session results to date objects
            session_dates = []
            for session in sessions:
                session_date = session.session_date
                # Convert string date to date object if needed
                if isinstance(session_date, str):
                    session_date = datetime.strptime(session_date, '%Y-%m-%d').date()
                session_dates.append(session_date)
            
            # Check for streak starting from today or most recent session date
            most_recent_date = session_dates[0]  # Already sorted desc
            
            # If the most recent session is today or yesterday, start counting from the most recent
            if (current_date - most_recent_date).days <= 1:
                check_date = most_recent_date
                for session_date in session_dates:
                    if session_date == check_date:
                        streak += 1
                        check_date = check_date - timedelta(days=1)
                    elif session_date < check_date:
                        # Check if there's a gap of more than 1 day
                        days_gap = (check_date - session_date).days
                        if days_gap > 1:
                            break  # Gap found, stop counting
                        else:
                            # Continue the streak
                            check_date = session_date
                            streak += 1
                            check_date = check_date - timedelta(days=1)
            
            return streak
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error calculating study streak: {e}")
            return 0
