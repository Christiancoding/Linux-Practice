#!/usr/bin/env python3
"""
Database-based Time Tracking Service for Linux+ Study Game
"""

import json
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, cast
from dateutil import parser
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from utils.database import get_db_session
from models.user_achievements import TimeTracking


class DBTimeTrackingService:
    """Database-based time tracking service that replaces JSON file storage."""
    
    def __init__(self, user_id: str = 'anonymous'):
        """
        Initialize the database time tracking service.
        
        Args:
            user_id: User identifier for time tracking
        """
        self.user_id = user_id
        self._time_tracking = None
    
    def _get_time_tracking_data(self) -> Dict[str, Any]:
        """Get time tracking data as dictionary to avoid session issues."""
        try:
            with get_db_session() as session:
                time_tracking = session.query(TimeTracking).filter_by(user_id=self.user_id).first()
                if not time_tracking:
                    # Create new record with defaults
                    time_tracking = TimeTracking(
                        user_id=self.user_id,
                        quiz_time_today=0.0,
                        last_quiz_reset=datetime.now(),
                        study_time_total=0.0,
                        daily_quiz_history={},
                        settings={
                            "reset_time": "00:59",
                            "timezone": "America/Chicago"
                        }
                    )
                    session.add(time_tracking)
                    session.commit()
                    session.refresh(time_tracking)
                
                return time_tracking.to_dict()
        except SQLAlchemyError as e:
            print(f"Database error in _get_time_tracking_data: {e}")
            return {
                "user_id": self.user_id,
                "quiz_time_today": 0.0,
                "last_quiz_reset": datetime.now(),
                "study_time_total": 0.0,
                "daily_quiz_history": {},
                "settings": {"reset_time": "00:59", "timezone": "America/Chicago"}
            }
    
    def _get_time_tracking(self) -> TimeTracking:
        """Get or create time tracking record within a session context."""
        try:
            with get_db_session() as session:
                time_tracking = session.query(TimeTracking).filter_by(user_id=self.user_id).first()
                if not time_tracking:
                    # Create new record with defaults
                    time_tracking = TimeTracking(
                        user_id=self.user_id,
                        quiz_time_today=0.0,
                        last_quiz_reset=datetime.now(),
                        study_time_total=0.0,
                        daily_quiz_history={},
                        settings={
                            "reset_time": "00:59",
                            "timezone": "America/Chicago"
                        }
                    )
                    session.add(time_tracking)
                    session.commit()
                    session.refresh(time_tracking)
                
                # Detach from session to avoid lazy loading issues
                session.expunge(time_tracking)
                return time_tracking
        except SQLAlchemyError as e:
            print(f"Database error in _get_time_tracking: {e}")
            # Return a default object
            return TimeTracking(
                user_id=self.user_id,
                quiz_time_today=0.0,
                last_quiz_reset=datetime.now(),
                study_time_total=0.0,
                daily_quiz_history={},
                settings={"reset_time": "00:59", "timezone": "America/Chicago"}
            )
    
    def _save_time_tracking(self, time_tracking: TimeTracking) -> None:
        """Save time tracking data to database."""
        try:
            with get_db_session() as session:
                session.merge(time_tracking)
                session.commit()
            
            # Update cached copy
            self._time_tracking = time_tracking
        except SQLAlchemyError as e:
            print(f"Database error in _save_time_tracking: {e}")
    
    def get_time_data(self) -> Dict[str, Any]:
        """Get current time tracking data."""
        return self._get_time_tracking_data()
    
    def add_quiz_time(self, minutes: float) -> None:
        """
        Add quiz time to today's total.
        
        Args:
            minutes: Time spent on quiz in minutes
        """
        try:
            with get_db_session() as session:
                time_tracking = session.query(TimeTracking).filter_by(user_id=self.user_id).first()
                if not time_tracking:
                    time_tracking = TimeTracking(
                        user_id=self.user_id,
                        quiz_time_today=0.0,
                        last_quiz_reset=datetime.now(),
                        study_time_total=0.0,
                        daily_quiz_history={},
                        settings={"reset_time": "00:59", "timezone": "America/Chicago"}
                    )
                    session.add(time_tracking)
                    session.flush()  # Ensure object is persisted before using
                
                # Check if we need to reset for a new day
                self._check_and_reset_daily_timer_in_session(time_tracking, session)
                
                # Add time to today's total with proper type conversion
                current_quiz_time = float(getattr(time_tracking, 'quiz_time_today', 0.0) or 0.0)
                current_study_time = float(getattr(time_tracking, 'study_time_total', 0.0) or 0.0)
                
                setattr(time_tracking, 'quiz_time_today', current_quiz_time + float(minutes))
                setattr(time_tracking, 'study_time_total', current_study_time + float(minutes))
                
                session.commit()
        except SQLAlchemyError as e:
            print(f"Database error in add_quiz_time: {e}")
        except (ValueError, TypeError) as e:
            print(f"Type conversion error in add_quiz_time: {e}")
    
    def get_quiz_time_today(self) -> float:
        """
        Get quiz time for today.
        
        Returns:
            float: Quiz time in minutes
        """
        try:
            with get_db_session() as session:
                time_tracking = session.query(TimeTracking).filter_by(user_id=self.user_id).first()
                if not time_tracking:
                    return 0.0
                
                self._check_and_reset_daily_timer_in_session(time_tracking, session)
                return float(getattr(time_tracking, 'quiz_time_today', 0.0) or 0.0)
        except SQLAlchemyError as e:
            print(f"Database error in get_quiz_time_today: {e}")
            return 0.0
        except (ValueError, TypeError) as e:
            print(f"Type conversion error in get_quiz_time_today: {e}")
            return 0.0
    
    def get_total_study_time(self) -> float:
        """
        Get total study time across all sessions.
        
        Returns:
            float: Total study time in minutes
        """
        try:
            with get_db_session() as session:
                time_tracking = session.query(TimeTracking).filter_by(user_id=self.user_id).first()
                if not time_tracking:
                    return 0.0
                return float(getattr(time_tracking, 'study_time_total', 0.0) or 0.0)
        except SQLAlchemyError as e:
            print(f"Database error in get_total_study_time: {e}")
            return 0.0
        except (ValueError, TypeError) as e:
            print(f"Type conversion error in get_total_study_time: {e}")
            return 0.0
    
    def _check_and_reset_daily_timer_in_session(self, time_tracking: TimeTracking, session: Session) -> None:
        """
        Check if daily timer needs to be reset and reset if necessary (within session).
        
        Args:
            time_tracking: TimeTracking record to check and potentially reset
            session: Active SQLAlchemy session
        """
        try:
            now = datetime.now()
            last_reset = getattr(time_tracking, 'last_quiz_reset', None)
            
            if last_reset is None:
                # First time setup
                setattr(time_tracking, 'last_quiz_reset', now)
                setattr(time_tracking, 'quiz_time_today', 0.0)
                return  # Don't commit here, let caller handle it
            
            # Check if we've passed the reset time
            settings = time_tracking.settings or {}
            reset_time_str = settings.get("reset_time", "00:59")
            
            try:
                reset_hour, reset_minute = map(int, reset_time_str.split(":"))
            except (ValueError, TypeError):
                reset_hour, reset_minute = 0, 59
            
            # Create reset time for today
            today_reset = now.replace(hour=reset_hour, minute=reset_minute, second=0, microsecond=0)
            
            # If last reset was before today's reset time and we're after reset time, reset
            if last_reset < today_reset <= now:
                # Save yesterday's quiz time to history
                yesterday_key = (now - timedelta(days=1)).strftime("%Y-%m-%d")
                
                # Ensure we have a proper Python dictionary
                raw_history = time_tracking.daily_quiz_history or {}
                if isinstance(raw_history, dict):
                    daily_history = dict(raw_history)
                else:
                    # Handle case where it might be stored as bytes or other format
                    daily_history = {}
                
                daily_history[yesterday_key] = float(getattr(time_tracking, 'quiz_time_today', 0.0) or 0.0)
                
                # Reset for new day
                setattr(time_tracking, 'quiz_time_today', 0.0)
                setattr(time_tracking, 'last_quiz_reset', now)
                setattr(time_tracking, 'daily_quiz_history', daily_history)
        except Exception as e:
            print(f"Error in _check_and_reset_daily_timer_in_session: {e}")
    
    def _check_and_reset_daily_timer(self, time_tracking: TimeTracking) -> None:
        """
        Check if daily timer needs to be reset and reset if necessary.
        
        Args:
            time_tracking: TimeTracking record to check and potentially reset
        """
        try:
            now = datetime.now()
            last_reset = getattr(time_tracking, 'last_quiz_reset', None)
            
            if last_reset is None:
                # First time setup
                setattr(time_tracking, 'last_quiz_reset', now)
                setattr(time_tracking, 'quiz_time_today', 0.0)
                self._save_time_tracking(time_tracking)
                return
            
            # Check if we've passed the reset time
            settings = time_tracking.settings or {}
            reset_time_str = settings.get("reset_time", "00:59")
            
            try:
                reset_hour, reset_minute = map(int, reset_time_str.split(":"))
            except (ValueError, TypeError):
                reset_hour, reset_minute = 0, 59
            
            # Create reset time for today
            today_reset = now.replace(hour=reset_hour, minute=reset_minute, second=0, microsecond=0)
            
            # If last reset was before today's reset time and we're after reset time, reset
            if last_reset < today_reset <= now:
                # Save yesterday's quiz time to history
                yesterday_key = (now - timedelta(days=1)).strftime("%Y-%m-%d")
                
                # Ensure we have a proper Python dictionary
                raw_history = time_tracking.daily_quiz_history or {}
                if isinstance(raw_history, dict):
                    daily_history = dict(raw_history)
                else:
                    # Handle case where it might be stored as bytes or other format
                    daily_history = {}
                
                daily_history[yesterday_key] = float(getattr(time_tracking, 'quiz_time_today', 0.0) or 0.0)
                
                # Reset for new day
                setattr(time_tracking, 'quiz_time_today', 0.0)
                setattr(time_tracking, 'last_quiz_reset', now)
                setattr(time_tracking, 'daily_quiz_history', daily_history)
                
                self._save_time_tracking(time_tracking)
        except Exception as e:
            print(f"Error in _check_and_reset_daily_timer: {e}")
    
    def get_daily_history(self) -> Dict[str, float]:
        """
        Get daily quiz time history.
        
        Returns:
            dict: Date strings mapped to quiz time in minutes
        """
        try:
            with get_db_session() as session:
                time_tracking = session.query(TimeTracking).filter_by(user_id=self.user_id).first()
                if not time_tracking:
                    return {}
                history = time_tracking.daily_quiz_history or {}
                # Ensure all values are floats
                return {k: float(v) for k, v in history.items() if v is not None}
        except SQLAlchemyError as e:
            print(f"Database error in get_daily_history: {e}")
            return {}
        except (ValueError, TypeError) as e:
            print(f"Type conversion error in get_daily_history: {e}")
            return {}
    
    def get_settings(self) -> Dict[str, Any]:
        """
        Get time tracking settings.
        
        Returns:
            dict: Settings dictionary
        """
        try:
            with get_db_session() as session:
                time_tracking = session.query(TimeTracking).filter_by(user_id=self.user_id).first()
                if not time_tracking:
                    return {"reset_time": "00:59", "timezone": "America/Chicago"}
                
                # Access the actual value, not the Column object
                settings_data = getattr(time_tracking, 'settings', None)
                
                # Handle None or empty settings
                if settings_data is None:
                    current_settings: Dict[str, Any] = {}
                elif isinstance(settings_data, dict):
                    current_settings = dict(cast(Dict[str, Any], settings_data))
                else:
                    # Handle other types (like JSON strings) by trying to convert
                    try:
                        if isinstance(settings_data, str):
                            current_settings = json.loads(settings_data)
                        else:
                            current_settings = {}
                    except (TypeError, ValueError, json.JSONDecodeError):
                        current_settings = {}
                
                return current_settings
        except SQLAlchemyError as e:
            print(f"Database error in get_settings: {e}")
            return {"reset_time": "00:59", "timezone": "America/Chicago"}
    
    def update_settings(self, settings: Dict[str, Any]) -> None:
        """
        Update time tracking settings.
        
        Args:
            settings: New settings to merge with existing ones
        """
        try:
            with get_db_session() as session:
                time_tracking = session.query(TimeTracking).filter_by(user_id=self.user_id).first()
                if not time_tracking:
                    time_tracking = TimeTracking(
                        user_id=self.user_id,
                        quiz_time_today=0.0,
                        last_quiz_reset=datetime.now(),
                        study_time_total=0.0,
                        daily_quiz_history={},
                        settings={"reset_time": "00:59", "timezone": "America/Chicago"}
                    )
                    session.add(time_tracking)
                    session.flush()
                
                # Get current settings using getattr to access actual value
                existing_settings = getattr(time_tracking, 'settings', None)
                if existing_settings is None:
                    current_settings: Dict[str, Any] = {}
                elif isinstance(existing_settings, dict):
                    current_settings = dict(cast(Dict[str, Any], existing_settings))
                else:
                    # Handle JSON string or other formats
                    try:
                        if isinstance(existing_settings, str):
                            current_settings = json.loads(existing_settings)
                        else:
                            current_settings = {}
                    except (TypeError, ValueError, json.JSONDecodeError):
                        current_settings = {}
                
                current_settings.update(settings)
                setattr(time_tracking, 'settings', current_settings)
                
                session.commit()
        except SQLAlchemyError as e:
            print(f"Database error in update_settings: {e}")
    
    def reset_all_data(self) -> None:
        """Reset all time tracking data."""
        try:
            with get_db_session() as session:
                time_tracking = session.query(TimeTracking).filter_by(user_id=self.user_id).first()
                if not time_tracking:
                    time_tracking = TimeTracking(
                        user_id=self.user_id,
                        quiz_time_today=0.0,
                        last_quiz_reset=datetime.now(),
                        study_time_total=0.0,
                        daily_quiz_history={},
                        settings={"reset_time": "00:59", "timezone": "America/Chicago"}
                    )
                    session.add(time_tracking)
                else:
                    setattr(time_tracking, 'quiz_time_today', 0.0)
                    setattr(time_tracking, 'study_time_total', 0.0)
                    setattr(time_tracking, 'daily_quiz_history', {})
                    setattr(time_tracking, 'last_quiz_reset', datetime.now())
                
                session.commit()
        except SQLAlchemyError as e:
            print(f"Database error in reset_all_data: {e}")
    
    def get_daily_summary(self) -> Dict[str, Any]:
        """
        Get daily time tracking summary.
        
        Returns:
            dict: Daily summary with quiz and study time
        """
        quiz_time_today = self.get_quiz_time_today()
        total_study_time = self.get_total_study_time()
        
        return {
            "quiz_time_today": quiz_time_today,
            "quiz_time_formatted": self._format_time(quiz_time_today),
            "total_study_time": total_study_time,
            "study_time_total": total_study_time,  # Alternative name
            "study_time_formatted": self._format_time(total_study_time),
            "daily_history": self.get_daily_history(),
            "settings": self.get_settings()
        }
    
    def _format_time(self, seconds: float) -> str:
        """Format seconds into readable time format (e.g., '2m 30.5s')"""
        if seconds < 60:
            return f"{seconds:.1f}s"
        
        minutes = int(seconds // 60)
        remaining_seconds = seconds % 60
        
        if remaining_seconds < 0.1:
            return f"{minutes}m"
        else:
            return f"{minutes}m {remaining_seconds:.1f}s"
    
    def get_weekly_summary(self) -> Dict[str, float]:
        """
        Get weekly time tracking summary.
        
        Returns:
            dict: Weekly summary with daily totals
        """
        daily_history = self.get_daily_history()
        today = datetime.now().strftime("%Y-%m-%d")
        today_time = self.get_quiz_time_today()
        
        # Add today's time if not in history yet
        if today not in daily_history and today_time > 0:
            daily_history[today] = today_time
        
        # Get last 7 days
        week_summary: Dict[str, float] = {}
        for i in range(7):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            week_summary[date] = daily_history.get(date, 0.0)
        
        return week_summary
    
    def export_data(self) -> Dict[str, Any]:
        """
        Export all time tracking data.
        
        Returns:
            dict: Complete time tracking data for export
        """
        try:
            time_tracking_data = self._get_time_tracking_data()
            return {
                "user_id": self.user_id,
                "current_data": time_tracking_data,
                "weekly_summary": self.get_weekly_summary(),
                "export_timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            print(f"Error in export_data: {e}")
            return {
                "user_id": self.user_id,
                "current_data": {},
                "weekly_summary": {},
                "export_timestamp": datetime.now().isoformat(),
                "error": str(e)
            }