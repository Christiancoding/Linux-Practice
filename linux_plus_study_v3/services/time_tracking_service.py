#!/usr/bin/env python3
"""
Time Tracking Service for Linux+ Study System

Provides unified time tracking with separate quiz time and study time.
Quiz time resets daily at 12:59 AM, study time is continuous.
"""

import os
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
from pathlib import Path
import zoneinfo


class TimeTrackingService:
    """Service for tracking quiz time and study time separately."""
    
    def __init__(self, data_file: Optional[Path] = None):
        """Initialize time tracking service."""
        self.data_file = data_file or Path("data/time_tracking.json")
        self.data = self._load_data()
        
    def _load_data(self) -> Dict[str, Any]:
        """Load time tracking data from file."""
        if self.data_file.exists():
            try:
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                    # Ensure all required fields exist
                    if not isinstance(data, dict):
                        return self._get_default_data()
                    
                    # Validate and migrate data structure
                    default_data = self._get_default_data()
                    for key in default_data:
                        if key not in data:
                            data[key] = default_data[key]
                    
                    return data
            except (json.JSONDecodeError, OSError) as e:
                print(f"Error loading time tracking data: {e}")
        
        return self._get_default_data()
    
    def _get_default_data(self) -> Dict[str, Any]:
        """Get default time tracking data structure."""
        return {
            "quiz_time_today": 0,  # Seconds spent on quizzes today
            "last_quiz_reset": None,  # ISO timestamp of last reset
            "daily_quiz_history": {},  # Date -> seconds mapping
            "settings": {
                "reset_time": "00:59",  # 12:59 AM
                "timezone": "America/Chicago"
            }
        }
    
    def _save_data(self) -> bool:
        """Save time tracking data to file."""
        try:
            self.data_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.data_file, 'w') as f:
                json.dump(self.data, f, indent=2)
            return True
        except OSError as e:
            print(f"Error saving time tracking data: {e}")
            return False
    
    def _should_reset_quiz_time(self) -> bool:
        """Check if quiz time should be reset (past 12:59 AM)."""
        now = datetime.now(zoneinfo.ZoneInfo("America/Chicago"))
        
        # Get last reset date
        last_reset_str = self.data.get("last_quiz_reset")
        if not last_reset_str:
            return True
        
        try:
            last_reset = datetime.fromisoformat(last_reset_str.replace('Z', '+00:00'))
            # Convert to local time if needed
            if last_reset.tzinfo:
                last_reset = last_reset.astimezone(zoneinfo.ZoneInfo("America/Chicago"))
            else:
                # If naive, assume it's in local timezone
                last_reset = last_reset.replace(tzinfo=zoneinfo.ZoneInfo("America/Chicago"))
        except (ValueError, AttributeError):
            return True
        
        # Check if we've passed the reset time (12:59 AM)
        reset_hour, reset_minute = 0, 59  # 12:59 AM
        
        # Get today's reset time
        today_reset = now.replace(
            hour=reset_hour, 
            minute=reset_minute, 
            second=0, 
            microsecond=0
        )
        
        # If it's before reset time today, use yesterday's reset time
        if now.time() < today_reset.time():
            today_reset = today_reset - timedelta(days=1)
        
        # Reset if last reset was before today's reset time
        return last_reset < today_reset
    
    def _reset_daily_quiz_time(self) -> None:
        """Reset quiz time for the day and save history."""
        # Save today's quiz time to history before resetting
        today_str = datetime.now(zoneinfo.ZoneInfo("America/Chicago")).strftime('%Y-%m-%d')
        current_quiz_time = self.data.get("quiz_time_today", 0)
        
        if current_quiz_time > 0:
            if "daily_quiz_history" not in self.data:
                self.data["daily_quiz_history"] = {}
            self.data["daily_quiz_history"][today_str] = current_quiz_time
        
        # Reset today's quiz time
        self.data["quiz_time_today"] = 0
        self.data["last_quiz_reset"] = datetime.now(zoneinfo.ZoneInfo("America/Chicago")).isoformat()
        
        self._save_data()
    
    def add_quiz_time(self, seconds: float) -> None:
        """Add time spent on quizzes."""
        if seconds <= 0:
            return
        
        # Check if we need to reset first
        if self._should_reset_quiz_time():
            self._reset_daily_quiz_time()
        
        self.data["quiz_time_today"] = self.data.get("quiz_time_today", 0) + seconds
        self._save_data()
    
    
    def get_quiz_time_today(self) -> int:
        """Get quiz time for today in seconds."""
        if self._should_reset_quiz_time():
            self._reset_daily_quiz_time()
        
        return self.data.get("quiz_time_today", 0)
    
    def get_quiz_time_formatted(self) -> str:
        """Get formatted quiz time for today."""
        seconds = self.get_quiz_time_today()
        return self._format_time(seconds)
    
    
    
    def get_quiz_history(self, days: int = 7) -> Dict[str, int]:
        """Get quiz time history for the last N days."""
        history = self.data.get("daily_quiz_history", {})
        today = datetime.now(zoneinfo.ZoneInfo("America/Chicago"))
        
        # Include today's current time
        result = {}
        for i in range(days):
            date = today - timedelta(days=i)
            date_str = date.strftime('%Y-%m-%d')
            
            if date_str == today.strftime('%Y-%m-%d'):
                # Today - use current time
                result[date_str] = self.get_quiz_time_today()
            else:
                # Historical data
                result[date_str] = history.get(date_str, 0)
        
        return result
    
    def get_daily_summary(self) -> Dict[str, Any]:
        """Get summary of today's time tracking."""
        return {
            "quiz_time_today": self.get_quiz_time_today(),
            "quiz_time_formatted": self.get_quiz_time_formatted(),
            "last_reset": self.data.get("last_quiz_reset"),
            "next_reset": self._get_next_reset_time()
        }
    
    def _get_next_reset_time(self) -> str:
        """Get the next reset time as ISO string."""
        now = datetime.now(zoneinfo.ZoneInfo("America/Chicago"))
        
        # Next reset is at 12:59 AM tomorrow or today if we haven't passed it
        reset_hour, reset_minute = 0, 59
        
        next_reset = now.replace(
            hour=reset_hour,
            minute=reset_minute, 
            second=0,
            microsecond=0
        )
        
        # If we've passed today's reset time, use tomorrow
        if now.time() >= next_reset.time():
            next_reset = next_reset + timedelta(days=1)
        
        return next_reset.isoformat()
    
    def _format_time(self, seconds: float) -> str:
        """Format seconds into human readable time with decimal precision."""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            remaining_seconds = seconds % 60
            if remaining_seconds < 0.1:
                return f"{minutes}m"
            else:
                return f"{minutes}m {remaining_seconds:.1f}s"
        else:
            hours = int(seconds // 3600)
            remaining_minutes = int((seconds % 3600) // 60)
            if remaining_minutes == 0:
                return f"{hours}h"
            else:
                return f"{hours}h {remaining_minutes}m"
    
    def reset_all_data(self) -> bool:
        """Reset all time tracking data (for testing/admin purposes)."""
        self.data = self._get_default_data()
        return self._save_data()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive time tracking statistics."""
        quiz_history = self.get_quiz_history(30)  # Last 30 days
        
        # Calculate averages
        total_quiz_days = sum(1 for time in quiz_history.values() if time > 0)
        total_quiz_time = sum(quiz_history.values())
        avg_quiz_time = total_quiz_time / total_quiz_days if total_quiz_days > 0 else 0
        
        return {
            "quiz_time_today": self.get_quiz_time_today(),
            "quiz_time_formatted": self.get_quiz_time_formatted(),
            "quiz_history_30_days": quiz_history,
            "total_quiz_days": total_quiz_days,
            "avg_daily_quiz_time": int(avg_quiz_time),
            "avg_daily_quiz_time_formatted": self._format_time(int(avg_quiz_time)),
            "next_reset": self._get_next_reset_time()
        }


# Global instance
_time_tracker = None

def get_time_tracker() -> TimeTrackingService:
    """Get the global time tracking service instance."""
    global _time_tracker
    if _time_tracker is None:
        _time_tracker = TimeTrackingService()
    return _time_tracker