#!/usr/bin/env python3
"""
Simple JSON-based Analytics Manager

Single source of truth for all user analytics data using a simple JSON file.
No more database complexity or conflicting data sources.
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class SimpleAnalyticsManager:
    """Simple analytics manager using JSON file storage"""
    
    def __init__(self, data_file: str = None):
        if data_file is None:
            # Default to data directory
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_dir)
            self.data_file = os.path.join(project_root, 'data', 'user_analytics.json')
        else:
            self.data_file = data_file
            
        self._ensure_data_file_exists()
    
    def _ensure_data_file_exists(self):
        """Create data file if it doesn't exist"""
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
        
        if not os.path.exists(self.data_file):
            default_data = {
                "anonymous": {
                    "total_questions": 0,
                    "correct_answers": 0,
                    "incorrect_answers": 0,
                    "accuracy": 0.0,
                    "total_study_time": 0,
                    "total_sessions": 0,
                    "study_streak": 0,
                    "questions_to_review": 0,
                    "level": 1,
                    "xp": 0,
                    "achievements": [],
                    "session_history": [],
                    "last_activity": None,
                    "topics_studied": {},
                    "difficulty_progress": {
                        "beginner": 0,
                        "intermediate": 0,
                        "advanced": 0
                    }
                }
            }
            self._save_data(default_data)
    
    def _load_data(self) -> Dict[str, Any]:
        """Load analytics data from JSON file"""
        try:
            with open(self.data_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading analytics data: {e}")
            return {"anonymous": self._get_default_user_data()}
    
    def _save_data(self, data: Dict[str, Any]):
        """Save analytics data to JSON file"""
        try:
            with open(self.data_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving analytics data: {e}")
    
    def _get_default_user_data(self) -> Dict[str, Any]:
        """Get default user data structure"""
        return {
            "total_questions": 0,
            "correct_answers": 0,
            "incorrect_answers": 0,
            "accuracy": 0.0,
            "total_study_time": 0,
            "total_sessions": 0,
            "study_streak": 0,
            "longest_streak": 0,
            "questions_to_review": 0,
            "level": 1,
            "xp": 0,
            "achievements": [],
            "session_history": [],
            "last_activity": None,
            "topics_studied": {},
            "difficulty_progress": {
                "beginner": 0,
                "intermediate": 0,
                "advanced": 0
            }
        }
    
    def get_user_data(self, user_id: str = "anonymous") -> Dict[str, Any]:
        """Get analytics data for a specific user"""
        data = self._load_data()
        
        if user_id not in data:
            data[user_id] = self._get_default_user_data()
            self._save_data(data)
        
        return data[user_id]
    
    def update_quiz_results(self, user_id: str, correct: bool, topic: str = None, difficulty: str = "beginner"):
        """Update analytics after a quiz question"""
        data = self._load_data()
        
        if user_id not in data:
            data[user_id] = self._get_default_user_data()
        
        user_data = data[user_id]
        
        # Update question counts
        user_data["total_questions"] += 1
        if correct:
            user_data["correct_answers"] += 1
        else:
            user_data["incorrect_answers"] += 1
            if user_data["questions_to_review"] < 10:  # Cap review questions
                user_data["questions_to_review"] += 1
        
        # Calculate accuracy
        if user_data["total_questions"] > 0:
            user_data["accuracy"] = round((user_data["correct_answers"] / user_data["total_questions"]) * 100, 2)
        
        # Update XP and level
        xp_gain = 10 if correct else 5  # 10 XP for correct, 5 for attempt
        user_data["xp"] += xp_gain
        user_data["level"] = max(1, (user_data["xp"] // 100) + 1)  # Level up every 100 XP
        
        # Add estimated study time per question (30-90 seconds depending on difficulty)
        if difficulty == "beginner":
            time_per_question = 45  # 45 seconds for beginner questions
        elif difficulty == "intermediate":
            time_per_question = 60  # 60 seconds for intermediate questions  
        else:  # advanced
            time_per_question = 75  # 75 seconds for advanced questions
            
        user_data["total_study_time"] += time_per_question
        
        # Track topics
        if topic:
            if topic not in user_data["topics_studied"]:
                user_data["topics_studied"][topic] = {"correct": 0, "total": 0}
            user_data["topics_studied"][topic]["total"] += 1
            if correct:
                user_data["topics_studied"][topic]["correct"] += 1
        
        # Track difficulty progress
        if difficulty in user_data["difficulty_progress"]:
            user_data["difficulty_progress"][difficulty] += 1
        
        # Update last activity and calculate streak
        current_time = datetime.now()
        last_activity = user_data.get("last_activity")
        
        if last_activity:
            try:
                if isinstance(last_activity, str):
                    last_date = datetime.fromisoformat(last_activity.replace('Z', '+00:00'))
                else:
                    last_date = last_activity
                    
                # Check if this is a new day
                if last_date.date() < current_time.date():
                    # New day - increment streak
                    days_diff = (current_time.date() - last_date.date()).days
                    if days_diff == 1:
                        # Consecutive day
                        user_data["study_streak"] += 1
                    else:
                        # Gap in days - reset streak
                        user_data["study_streak"] = 1
                    
                    # Update longest streak
                    if user_data["study_streak"] > user_data.get("longest_streak", 0):
                        user_data["longest_streak"] = user_data["study_streak"]
                # Same day - maintain streak
            except Exception:
                # Error parsing date, start new streak
                user_data["study_streak"] = 1
        else:
            # First activity
            user_data["study_streak"] = 1
            user_data["longest_streak"] = 1
        
        user_data["last_activity"] = current_time.isoformat()
        
        self._save_data(data)
        return user_data

    # Profile Management Methods
    def get_all_profiles(self) -> Dict[str, Any]:
        """Get all user profiles with their basic stats"""
        data = self._load_data()
        profiles = {}
        
        for user_id, user_data in data.items():
            profiles[user_id] = {
                "user_id": user_id,
                "display_name": user_data.get("display_name", user_id.replace("_", " ").title()),
                "total_questions": user_data.get("total_questions", 0),
                "accuracy": user_data.get("accuracy", 0.0),
                "level": user_data.get("level", 1),
                "study_streak": user_data.get("study_streak", 0),
                "total_study_time": user_data.get("total_study_time", 0),
                "last_activity": user_data.get("last_activity"),
                "created_date": user_data.get("created_date", datetime.now().isoformat())
            }
        
        return profiles
    
    def create_profile(self, user_id: str, display_name: str = None) -> bool:
        """Create a new user profile"""
        if not user_id or not user_id.strip():
            return False
            
        # Clean user_id (remove spaces, special chars, make lowercase)
        clean_user_id = user_id.strip().lower().replace(" ", "_")
        clean_user_id = "".join(c for c in clean_user_id if c.isalnum() or c == "_")
        
        data = self._load_data()
        
        if clean_user_id in data:
            return False  # Profile already exists
        
        # Create new profile
        new_profile = self._get_default_user_data()
        new_profile["display_name"] = display_name or clean_user_id.replace("_", " ").title()
        new_profile["created_date"] = datetime.now().isoformat()
        
        data[clean_user_id] = new_profile
        self._save_data(data)
        
        return True
    
    def delete_profile(self, user_id: str) -> bool:
        """Delete a user profile"""
        if user_id == "anonymous":
            return False  # Don't allow deleting anonymous profile
            
        data = self._load_data()
        
        if user_id in data:
            del data[user_id]
            self._save_data(data)
            return True
        
        return False
    
    def rename_profile(self, user_id: str, new_display_name: str) -> bool:
        """Rename a user profile display name"""
        data = self._load_data()
        
        if user_id in data:
            data[user_id]["display_name"] = new_display_name
            self._save_data(data)
            return True
        
        return False
    
    def reset_profile(self, user_id: str) -> bool:
        """Reset a user profile to default state"""
        data = self._load_data()
        
        if user_id in data:
            # Keep display name and created date
            display_name = data[user_id].get("display_name", user_id.replace("_", " ").title())
            created_date = data[user_id].get("created_date", datetime.now().isoformat())
            
            # Reset to default data
            data[user_id] = self._get_default_user_data()
            data[user_id]["display_name"] = display_name
            data[user_id]["created_date"] = created_date
            
            self._save_data(data)
            return True
        
        return False
    
    def track_question_answer(self, user_id: str = "anonymous", correct: bool = False, 
                            category: str = None, time_taken: float = None):
        """Track a question answer and update analytics"""
        data = self._load_data()
        
        if user_id not in data:
            data[user_id] = self._get_default_user_data()
        
        user_data = data[user_id]
        
        # Update question counts
        user_data["total_questions"] += 1
        
        if correct:
            user_data["correct_answers"] += 1
            # Update streak
            user_data["study_streak"] += 1
            if user_data["study_streak"] > user_data.get("longest_streak", 0):
                user_data["longest_streak"] = user_data["study_streak"]
        else:
            user_data["incorrect_answers"] += 1
            user_data["study_streak"] = 0  # Reset streak on incorrect answer
            user_data["questions_to_review"] += 1
        
        # Update accuracy
        if user_data["total_questions"] > 0:
            user_data["accuracy"] = (user_data["correct_answers"] / user_data["total_questions"]) * 100
        
        # Update category tracking
        if category:
            if "topics_studied" not in user_data:
                user_data["topics_studied"] = {}
            if category not in user_data["topics_studied"]:
                user_data["topics_studied"][category] = {"questions": 0, "correct": 0}
            
            user_data["topics_studied"][category]["questions"] += 1
            if correct:
                user_data["topics_studied"][category]["correct"] += 1
        
        # Update last activity
        user_data["last_activity"] = datetime.now().isoformat()
        
        # Save data
        self._save_data(data)
        
        return True

    def start_session(self, user_id: str = "anonymous"):
        """Start a new study session"""
        data = self._load_data()
        
        if user_id not in data:
            data[user_id] = self._get_default_user_data()
        
        user_data = data[user_id]
        user_data["total_sessions"] += 1
        
        # Add session to history
        session_info = {
            "start_time": datetime.now().isoformat(),
            "questions_answered": 0,
            "questions_correct": 0
        }
        user_data["session_history"].append(session_info)
        
        # Keep only last 10 sessions
        if len(user_data["session_history"]) > 10:
            user_data["session_history"] = user_data["session_history"][-10:]
        
        self._save_data(data)
        return session_info
    
    def add_study_time(self, user_id: str, seconds: int):
        """Add study time for a user"""
        data = self._load_data()
        
        if user_id not in data:
            data[user_id] = self._get_default_user_data()
        
        data[user_id]["total_study_time"] += seconds
        self._save_data(data)
    
    def get_dashboard_stats(self, user_id: str = "anonymous") -> Dict[str, Any]:
        """Get dashboard statistics"""
        user_data = self.get_user_data(user_id)
        
        # Calculate level progress
        current_level_xp = user_data["xp"] % 100
        level_progress = (current_level_xp / 100) * 100
        
        # Calculate study streak (days)
        study_streak = self._calculate_study_streak(user_data)
        
        # Get recent achievements
        recent_achievements = self._get_recent_achievements(user_data)
        
        # Get performance overview data
        performance_overview = self._get_performance_overview(user_data)
        
        # Get study activity data
        study_activity = self._get_study_activity(user_data)
        
        return {
            "level": user_data["level"],
            "xp": user_data["xp"],
            "level_progress": level_progress,
            "streak": study_streak,
            "total_correct": user_data["correct_answers"],
            "accuracy": user_data["accuracy"],
            "study_time": user_data["total_study_time"],
            "session_points": user_data["xp"],
            "total_points": user_data["xp"],
            "questions_answered": user_data["total_questions"],
            "days_studied": study_streak,
            "badges_earned": len(recent_achievements),
            "total_sessions": user_data["total_sessions"],
            
            # Enhanced dashboard sections
            "recent_achievements": recent_achievements,
            "performance_overview": performance_overview,
            "study_activity": study_activity,
            "study_streak_details": {
                "current_streak": study_streak,
                "longest_streak": user_data.get("longest_streak", study_streak),
                "last_activity": user_data.get("last_activity")
            }
        }
    
    def _calculate_study_streak(self, user_data: Dict[str, Any]) -> int:
        """Calculate current study streak in days"""
        from datetime import datetime, timedelta
        
        # Get last activity date
        last_activity = user_data.get("last_activity")
        if not last_activity:
            return 0
            
        try:
            # Parse the last activity date
            if isinstance(last_activity, str):
                last_date = datetime.fromisoformat(last_activity.replace('Z', '+00:00'))
            else:
                last_date = last_activity
                
            # Check if last activity was today or yesterday
            today = datetime.now()
            days_since = (today - last_date).days
            
            if days_since == 0:
                # Activity today - maintain or start streak
                return max(1, user_data.get("study_streak", 1))
            elif days_since == 1:
                # Activity yesterday - maintain streak
                return user_data.get("study_streak", 1)
            else:
                # No recent activity - reset streak
                return 0
                
        except Exception:
            return user_data.get("study_streak", 0)
    
    def _get_recent_achievements(self, user_data: Dict[str, Any]) -> list:
        """Get list of recent achievements"""
        achievements = []
        total_questions = user_data["total_questions"]
        correct_answers = user_data["correct_answers"]
        accuracy = user_data["accuracy"]
        
        # Achievement definitions with timestamps
        if total_questions >= 1:
            achievements.append({
                "name": "First Steps",
                "description": "Answered your first question",
                "icon": "🎯",
                "earned_date": user_data.get("last_activity"),
                "type": "milestone"
            })
        
        if total_questions >= 5:
            achievements.append({
                "name": "Getting Started", 
                "description": "Answered 5 questions",
                "icon": "📚",
                "earned_date": user_data.get("last_activity"),
                "type": "milestone"
            })
            
        if correct_answers >= 1:
            achievements.append({
                "name": "First Correct",
                "description": "Got your first answer right",
                "icon": "✅", 
                "earned_date": user_data.get("last_activity"),
                "type": "accuracy"
            })
            
        if accuracy >= 80 and total_questions >= 5:
            achievements.append({
                "name": "Accuracy Expert",
                "description": "Achieved 80% accuracy",
                "icon": "🎓",
                "earned_date": user_data.get("last_activity"),
                "type": "accuracy"
            })
            
        # Return only the most recent 3 achievements
        return achievements[-3:] if achievements else []
    
    def _get_performance_overview(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get performance overview data"""
        topics = user_data.get("topics_studied", {})
        
        # Calculate topic performance
        topic_performance = []
        for topic, stats in topics.items():
            if stats["total"] > 0:
                topic_accuracy = (stats["correct"] / stats["total"]) * 100
                topic_performance.append({
                    "topic": topic,
                    "accuracy": round(topic_accuracy, 1),
                    "questions": stats["total"],
                    "correct": stats["correct"]
                })
        
        # Sort by accuracy descending
        topic_performance.sort(key=lambda x: x["accuracy"], reverse=True)
        
        # Calculate difficulty breakdown
        difficulty_progress = user_data.get("difficulty_progress", {})
        total_difficulty_questions = sum(difficulty_progress.values())
        
        difficulty_breakdown = []
        for difficulty, count in difficulty_progress.items():
            if total_difficulty_questions > 0:
                percentage = (count / total_difficulty_questions) * 100
                difficulty_breakdown.append({
                    "difficulty": difficulty.title(),
                    "questions": count,
                    "percentage": round(percentage, 1)
                })
        
        return {
            "topics": topic_performance[:5],  # Top 5 topics
            "difficulty_breakdown": difficulty_breakdown,
            "overall_trend": "improving" if user_data["accuracy"] > 50 else "needs_improvement",
            "strongest_topic": topic_performance[0]["topic"] if topic_performance else "None",
            "weakest_topic": topic_performance[-1]["topic"] if len(topic_performance) > 1 else "None"
        }
    
    def _get_study_activity(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get study activity data"""
        from datetime import datetime, timedelta
        
        # Generate recent activity data (last 7 days)
        activity_data = []
        today = datetime.now()
        
        for i in range(7):
            date = today - timedelta(days=i)
            # For now, simulate activity based on current data
            # In a real implementation, you'd track daily activity
            if i == 0 and user_data["total_questions"] > 0:
                # Today has activity
                activity_data.append({
                    "date": date.strftime("%Y-%m-%d"),
                    "questions": user_data["total_questions"],
                    "study_time": user_data["total_study_time"],
                    "accuracy": user_data["accuracy"]
                })
            else:
                # No activity on other days
                activity_data.append({
                    "date": date.strftime("%Y-%m-%d"), 
                    "questions": 0,
                    "study_time": 0,
                    "accuracy": 0
                })
        
        # Calculate weekly stats
        total_weekly_questions = sum(day["questions"] for day in activity_data)
        total_weekly_time = sum(day["study_time"] for day in activity_data)
        
        return {
            "daily_activity": list(reversed(activity_data)),  # Oldest to newest
            "weekly_summary": {
                "total_questions": total_weekly_questions,
                "total_time": total_weekly_time,
                "active_days": len([day for day in activity_data if day["questions"] > 0]),
                "average_daily_questions": round(total_weekly_questions / 7, 1)
            },
            "session_history": user_data.get("session_history", [])
        }
    
    def get_analytics_stats(self, user_id: str = "anonymous") -> Dict[str, Any]:
        """Get analytics page statistics"""
        user_data = self.get_user_data(user_id)
        
        return {
            "total_questions": user_data["total_questions"],
            "correct_answers": user_data["correct_answers"],
            "accuracy": user_data["accuracy"],
            "total_study_time": user_data["total_study_time"],
            "study_streak": user_data["study_streak"],
            "total_sessions": user_data["total_sessions"],
            "questions_to_review": user_data["questions_to_review"],
            "topics_studied": user_data["topics_studied"],
            "difficulty_progress": user_data["difficulty_progress"]
        }
    
    def reset_user_data(self, user_id: str = "anonymous"):
        """Reset all data for a user"""
        data = self._load_data()
        data[user_id] = self._get_default_user_data()
        self._save_data(data)
        return data[user_id]
    
    def export_data(self) -> Dict[str, Any]:
        """Export all analytics data"""
        return self._load_data()


# Global instance
_analytics_manager = None

def get_analytics_manager() -> SimpleAnalyticsManager:
    """Get global analytics manager instance"""
    global _analytics_manager
    if _analytics_manager is None:
        _analytics_manager = SimpleAnalyticsManager()
    return _analytics_manager
