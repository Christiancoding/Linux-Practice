#!/usr/bin/env python3
"""
Database Time Tracking Service Wrapper

Provides a drop-in replacement for the JSON-based time tracking service
that uses the database instead.
"""

from services.db_time_tracking_service import DBTimeTrackingService

_time_tracker = None

def get_time_tracker(user_id: str = 'anonymous') -> DBTimeTrackingService:
    """Get the global database time tracking service instance."""
    global _time_tracker
    if _time_tracker is None or _time_tracker.user_id != user_id:
        _time_tracker = DBTimeTrackingService(user_id)
    return _time_tracker

# For backward compatibility, also create a wrapper class that mimics the old interface
class TimeTrackingService:
    """Backward compatibility wrapper for DBTimeTrackingService."""
    
    def __init__(self, user_id: str = 'anonymous'):
        self.db_service = DBTimeTrackingService(user_id)
    
    def add_quiz_time(self, minutes: float) -> None:
        """Add quiz time to today's total."""
        self.db_service.add_quiz_time(minutes)
    
    def get_quiz_time_today(self) -> float:
        """Get quiz time for today."""
        return self.db_service.get_quiz_time_today()
    
    def get_total_study_time(self) -> float:
        """Get total study time."""
        return self.db_service.get_total_study_time()
    
    def get_daily_history(self) -> dict:
        """Get daily quiz time history."""
        return self.db_service.get_daily_history()
    
    def get_settings(self) -> dict:
        """Get time tracking settings."""
        return self.db_service.get_settings()
    
    def update_settings(self, settings: dict) -> None:
        """Update time tracking settings."""
        self.db_service.update_settings(settings)
    
    def reset_all_data(self) -> None:
        """Reset all time tracking data."""
        self.db_service.reset_all_data()
    
    def get_daily_summary(self) -> dict:
        """Get daily time tracking summary."""
        return self.db_service.get_daily_summary()