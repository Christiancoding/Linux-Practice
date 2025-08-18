#!/usr/bin/env python3
"""
Simple JSON-based Analytics Manager

Single source of truth for all user analytics data using a simple JSON file.
No more database complexity or conflicting data sources.
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)

class SimpleAnalyticsManager:
    """Simple analytics manager using JSON file storage"""
    
    def __init__(self, data_file: Optional[str] = None):
        if data_file is None:
            # Default to data directory
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_dir)
            self.data_file = os.path.join(project_root, 'data', 'user_analytics.json')
        else:
            self.data_file = data_file
            
        self._ensure_data_file_exists()
    
    @staticmethod
    def _format_time(seconds: float) -> str:
        """Format seconds into readable time format (e.g., '2m 30.5s')"""
        if seconds < 60:
            return f"{seconds:.1f}s"
        
        minutes = int(seconds // 60)
        remaining_seconds = seconds % 60
        
        if remaining_seconds < 0.1:
            return f"{minutes}m"
        else:
            return f"{minutes}m {remaining_seconds:.1f}s"
    
    def _ensure_data_file_exists(self):
        """Create data file if it doesn't exist"""
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
        
        if not os.path.exists(self.data_file):
            default_data: Dict[str, Dict[str, Any]] = {
                "anonymous": {
                    "total_questions": 0,
                    "correct_answers": 0,
                    "incorrect_answers": 0,
                    "accuracy": 0.0,
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
        today_str = datetime.now().strftime("%Y-%m-%d")
        return {
            "total_questions": 0,
            "correct_answers": 0,
            "incorrect_answers": 0,
            "accuracy": 0.0,
            "total_sessions": 0,
            "study_streak": 0,
            "current_streak": 0,  # Current streak of correct answers
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
            },
            # Daily tracking data
            "daily_data": {
                "last_reset_date": today_str,
                "today": {
                    "date": today_str,
                    "correct_answers": 0,
                    "total_questions": 0,
                    "quiz_time": 0,
                    "study_time": 0
                },
                "yesterday": {
                    "date": "",
                    "correct_answers": 0,
                    "total_questions": 0,
                    "quiz_time": 0,
                    "study_time": 0
                },
                "daily_history": {}  # Keep track of past days
            }
        }
    
    def _check_and_reset_daily_data(self, user_data: Dict[str, Any]) -> None:
        """Check if we need to reset daily data (new day) and update accordingly"""
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        # Initialize daily_data if it doesn't exist (for backward compatibility)
        if "daily_data" not in user_data:
            user_data["daily_data"] = {
                "last_reset_date": today_str,
                "today": {
                    "date": today_str,
                    "correct_answers": 0,
                    "total_questions": 0,
                    "quiz_time": 0,
                    "study_time": 0
                },
                "yesterday": {
                    "date": "",
                    "correct_answers": 0,
                    "total_questions": 0,
                    "quiz_time": 0,
                    "study_time": 0
                },
                "daily_history": {}
            }
        
        daily_data = user_data["daily_data"]
        last_reset = daily_data.get("last_reset_date", "")
        
        # If it's a new day, reset daily counters
        if last_reset != today_str:
            # Move today's data to yesterday
            daily_data["yesterday"] = daily_data["today"].copy()
            
            # Save today's data to history
            if daily_data["today"]["date"]:
                daily_data["daily_history"][daily_data["today"]["date"]] = daily_data["today"].copy()
            
            # Reset today's counters
            daily_data["today"] = {
                "date": today_str,
                "correct_answers": 0,
                "total_questions": 0,
                "quiz_time": 0,
                "study_time": 0
            }
            daily_data["last_reset_date"] = today_str
            
            # Keep only last 30 days of history
            if len(daily_data["daily_history"]) > 30:
                sorted_dates = sorted(daily_data["daily_history"].keys())
                for old_date in sorted_dates[:-30]:
                    del daily_data["daily_history"][old_date]
    
    def get_user_data(self, user_id: str) -> dict:
        """Get or create user analytics data"""
        data = self._load_data()
        
        if user_id not in data:
            data[user_id] = self._create_default_user_data(user_id)
            self._save_data(data)
        
        # Ensure all calculated fields are up to date
        user_data = data[user_id]
        
        # Recalculate accuracy to ensure consistency
        if user_data.get("total_questions", 0) > 0:
            user_data["accuracy"] = (user_data.get("correct_answers", 0) / user_data["total_questions"]) * 100
        else:
            user_data["accuracy"] = 0
            
        # Ensure overall_accuracy matches accuracy for consistency
        user_data["overall_accuracy"] = user_data["accuracy"]
        
        # Calculate total study time from sessions if needed
        if "sessions" in user_data and user_data["sessions"]:
            total_time = sum(session.get("duration", 0) for session in user_data["sessions"])
            
        return user_data

    def update_quiz_results(self, user_id: str, correct: bool, topic: str = None, difficulty: str = "beginner"):
        """Update analytics after a quiz question"""
        data = self._load_data()
        
        if user_id not in data:
            data[user_id] = self._get_default_user_data()
        
        user_data = data[user_id]
        
        # Check and reset daily data if needed
        self._check_and_reset_daily_data(user_data)
        
        # Update question counts and current streak
        user_data["total_questions"] += 1
        if correct:
            user_data["correct_answers"] += 1
            # Update current streak
            user_data["current_streak"] = user_data.get("current_streak", 0) + 1
        else:
            user_data["incorrect_answers"] += 1
            # Reset current streak on incorrect answer
            user_data["current_streak"] = 0
            if user_data["questions_to_review"] < 10:  # Cap review questions
                user_data["questions_to_review"] += 1
        
        # Calculate accuracy
        if user_data["total_questions"] > 0:
            user_data["accuracy"] = round((user_data["correct_answers"] / user_data["total_questions"]) * 100, 2)
        
        # Update XP and level - ONLY give XP for correct answers
        if correct:
            base_xp = 10  # 10 XP per correct answer
            # Add small streak bonus (max 5 XP)
            streak_bonus = min(5, user_data.get("current_streak", 0) // 3)  # Bonus every 3 correct answers
            xp_gain = base_xp + streak_bonus
        else:
            xp_gain = 0   # NO XP for incorrect answers
            
        user_data["xp"] += xp_gain
        user_data["level"] = max(1, (user_data["xp"] // 100) + 1)  # Level up every 100 XP
        
        # Add realistic study time per question (faster estimates)
        if difficulty == "beginner":
            time_per_question = 8   # 8 seconds for beginner questions
        elif difficulty == "intermediate":
            time_per_question = 12  # 12 seconds for intermediate questions  
        else:  # advanced
            time_per_question = 15  # 15 seconds for advanced questions
            
        
        # Track topics with consistent structure
        if topic:
            if topic not in user_data["topics_studied"]:
                user_data["topics_studied"][topic] = {"correct": 0, "total": 0, "questions": 0}
            
            user_data["topics_studied"][topic]["total"] += 1
            user_data["topics_studied"][topic]["questions"] += 1  # Keep both for backward compatibility
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
        
        # Update session count - increment every 5 questions or after 10 minutes gap
        current_session = user_data.get("current_session", {"start": current_time.isoformat(), "questions": 0})
        
        # Check if this is a new session (more than 10 minutes since last question)
        try:
            last_session_time = datetime.fromisoformat(current_session.get("last_activity", current_time.isoformat()))
            time_diff = (current_time - last_session_time).total_seconds()
            
            if time_diff > 600:  # 10 minutes = new session
                user_data["total_sessions"] += 1
                current_session = {"start": current_time.isoformat(), "questions": 1}
            else:
                current_session["questions"] += 1
                # Also count as new session if we hit 5 questions
                if current_session["questions"] >= 5:
                    user_data["total_sessions"] += 1
                    current_session = {"start": current_time.isoformat(), "questions": 1}
                    
        except Exception:
            # Error parsing time, create new session
            user_data["total_sessions"] += 1
            current_session = {"start": current_time.isoformat(), "questions": 1}
        
        current_session["last_activity"] = current_time.isoformat()
        user_data["current_session"] = current_session
        
        # Ensure total_sessions is at least 1 if there are questions
        if user_data["total_questions"] > 0 and user_data["total_sessions"] == 0:
            user_data["total_sessions"] = 1
        
        # Update session history for real-time activity tracking
        self._update_session_history_for_question(user_data, correct)
        
        # Check and award achievements
        self._check_and_award_achievements(user_data)
        
        # Update daily tracking data
        daily_data = user_data["daily_data"]
        daily_data["today"]["total_questions"] += 1
        if correct:
            daily_data["today"]["correct_answers"] += 1
        
        self._save_data(data)
        return user_data
    
    def _update_session_history_for_question(self, user_data: dict, correct: bool):
        """Update session history for real-time calendar tracking"""
        current_time = datetime.now()
        today_str = current_time.strftime("%Y-%m-%d")
        session_history = user_data.get("session_history", [])
        
        # Check if there's already a session for today
        today_session = None
        for session in session_history:
            if session.get("start_time"):
                try:
                    session_dt = datetime.fromisoformat(session["start_time"].replace('Z', '+00:00'))
                    if session_dt.strftime("%Y-%m-%d") == today_str:
                        today_session = session
                        break
                except (ValueError, AttributeError):
                    continue
        
        if today_session:
            # Update existing today's session
            today_session["questions_answered"] = today_session.get("questions_answered", 0) + 1
            if correct:
                today_session["questions_correct"] = today_session.get("questions_correct", 0) + 1
        else:
            # Create new session for today
            new_session = {
                "start_time": current_time.isoformat(),
                "questions_answered": 1,
                "questions_correct": 1 if correct else 0
            }
            session_history.append(new_session)
            
            # Keep only last 15 sessions (increased from 10 for better history)
            if len(session_history) > 15:
                user_data["session_history"] = session_history[-15:]

    def update_session_with_actual_time(self, user_id: str, actual_duration: int, questions_answered: int) -> Dict[str, Any]:
        """
        Update the user's study time with actual session duration instead of estimated time.
        
        Args:
            user_id: User identifier
            actual_duration: Actual time spent in seconds
            questions_answered: Number of questions in the session
            
        Returns:
            Updated user data
        """
        data = self._load_data()
        
        if user_id not in data:
            data[user_id] = self._get_default_user_data()
            
        user_data = data[user_id]
        
        # Remove the estimated time that was added per question
        if questions_answered > 0:
            # Calculate estimated time that was already added (12s per intermediate question as default)
            estimated_time_added = questions_answered * 12
            
            # Subtract the estimated time and add the actual time
        
        data[user_id] = user_data
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
        """Track a question answer and update analytics - redirects to update_quiz_results for consistency"""
        return self.update_quiz_results(
            user_id=user_id,
            correct=correct,
            topic=category,
            difficulty="intermediate"  # Default difficulty
        )
    
    def _check_and_award_achievements(self, user_data: Dict[str, Any]) -> None:
        """Check and award achievements based on current user progress"""
        current_achievements = {a["id"] for a in user_data.get("achievements", [])}
        new_achievements = []
        
        total_questions = user_data.get("total_questions", 0)
        correct_answers = user_data.get("correct_answers", 0)
        accuracy = user_data.get("accuracy", 0)
        
        # Achievement definitions
        achievement_checks = [
            ("first_question", total_questions >= 1, "First Steps", "Answered your first question"),
            ("first_correct", correct_answers >= 1, "First Correct", "Got your first answer right"),
            ("five_questions", total_questions >= 5, "Getting Started", "Answered 5 questions"),
            ("ten_questions", total_questions >= 10, "Dedicated Student", "Answered 10 questions"),
            ("accuracy_80", accuracy >= 80 and total_questions >= 5, "Accuracy Expert", "Achieved 80% accuracy with 5+ questions"),
        ]
        
        for achievement_id, condition, name, description in achievement_checks:
            if condition and achievement_id not in current_achievements:
                new_achievement = {
                    "id": achievement_id,
                    "name": name,
                    "description": description,
                    "earned_date": datetime.now().isoformat(),
                    "icon": "🏆"
                }
                new_achievements.append(new_achievement)
        
        # Add new achievements to user data
        if new_achievements:
            if "achievements" not in user_data:
                user_data["achievements"] = []
            user_data["achievements"].extend(new_achievements)

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
    
    
    def _get_questions_per_topic(self, user_data: dict) -> dict:
        """Get question count per topic"""
        topics = user_data.get("topics_studied", {})
        result = {}
        for topic, data in topics.items():
            # Use 'questions' field if available, otherwise use 'total'
            result[topic] = data.get("questions", data.get("total", 0))
        return result

    def _calculate_topic_accuracy(self, topic_data: dict) -> float:
        """Calculate accuracy for a specific topic"""
        total = topic_data.get("total", topic_data.get("questions", 0))
        if total == 0:
            return 0.0
        correct = topic_data.get("correct", 0)
        return round((correct / total) * 100, 1)

    def get_dashboard_stats(self, user_id: str) -> dict:
        """Get dashboard statistics for a user - SINGLE SOURCE OF TRUTH"""
        user_data = self.get_user_data(user_id)
        
        # Check and reset daily data if needed
        self._check_and_reset_daily_data(user_data)
        
        # Core calculations - ensure consistency
        total_questions = user_data.get("total_questions", 0)
        correct_answers = user_data.get("correct_answers", 0)
        incorrect_answers = user_data.get("incorrect_answers", 0)
        
        # Ensure incorrect_answers is accurate
        if incorrect_answers == 0 and total_questions > 0:
            incorrect_answers = total_questions - correct_answers
            user_data["incorrect_answers"] = incorrect_answers
        
        # Calculate accuracy - single formula
        if total_questions > 0:
            accuracy = (correct_answers / total_questions) * 100
        else:
            accuracy = 0.0
        
        # Use actual XP earned from gameplay (don't recalculate)
        xp = user_data.get("xp", 0)
        
        level = max(1, (xp // 100) + 1)
        level_progress = xp % 100
        
        # Calculate topic breakdown with accuracies - return as list of tuples for sorting
        topic_breakdown = []
        topics_studied = user_data.get("topics_studied", {})
        for topic, data in topics_studied.items():
            accuracy_val = self._calculate_topic_accuracy(data)
            topic_breakdown.append((topic, accuracy_val))
        
        # Sort by accuracy descending
        topic_breakdown.sort(key=lambda x: x[1], reverse=True)
        
        # Also create dict version for compatibility
        topic_breakdown_dict = {topic: acc for topic, acc in topic_breakdown}
        
        # Calculate session statistics
        sessions = user_data.get("sessions", [])
        avg_questions_per_session = 0
        avg_session_duration = 0
        best_session_accuracy = 0
        
        if sessions:
            total_session_questions = sum(s.get("questions", 0) for s in sessions)
            total_session_duration = sum(s.get("duration", 0) for s in sessions)
            avg_questions_per_session = round(total_session_questions / len(sessions), 1) if sessions else 0
            avg_session_duration = round(total_session_duration / len(sessions), 1) if sessions else 0
            
            # Find best session accuracy
            for session in sessions:
                session_questions = session.get("questions", 0)
                session_correct = session.get("correct", 0)
                if session_questions > 0:
                    session_accuracy = (session_correct / session_questions) * 100
                    best_session_accuracy = max(best_session_accuracy, session_accuracy)
        
        # Build comprehensive stats object
        return {
            # Core stats - these are the TRUTH
            "total_questions": total_questions,
            "questions_answered": total_questions,  # Alias for compatibility
            "total_correct": correct_answers,
            "correct_answers": correct_answers,  # Alias for compatibility
            "incorrect_answers": incorrect_answers,
            "accuracy": round(accuracy, 1),
            "overall_accuracy": round(accuracy, 1),  # Alias for compatibility
            
            # Time and sessions
            "total_sessions": user_data.get("total_sessions", 0),
            
            # Streaks
            "streak": user_data.get("study_streak", 0),
            "study_streak": user_data.get("study_streak", 0),
            "study_streak_days": user_data.get("study_streak", 0),
            "current_streak": user_data.get("current_streak", 0),
            "longest_streak": user_data.get("longest_streak", 0),
            
            # XP and Level
            "level": level,
            "xp": xp,
            "level_progress": level_progress,
            
            # User info
            "display_name": user_data.get("display_name", "Anonymous"),
            
            # Topics and difficulty - provide both list and dict formats
            "topic_breakdown": topic_breakdown_dict,  # Dict for compatibility
            "topic_breakdown_list": topic_breakdown,  # List of tuples for sorting
            "topics_studied": topics_studied,
            "questions_per_topic": self._get_questions_per_topic(user_data),
            "difficulty_progress": user_data.get("difficulty_progress", {}),
            
            # VM and CLI stats
            "total_vm_commands": user_data.get("vm_commands_executed", 0),
            "vm_sessions": user_data.get("vm_sessions", 0),
            "cli_usage": user_data.get("cli_playground_usage", 0),
            "lab_exercises": user_data.get("lab_exercises_completed", 0),
            
            # Other stats
            "content_pages": user_data.get("content_pages_viewed", 0),
            "return_sessions": user_data.get("return_sessions", 0),
            "review_sessions": user_data.get("review_sessions", 0),
            "questions_to_review": user_data.get("questions_to_review", 0),
            
            # Session statistics
            "avg_questions_per_session": avg_questions_per_session,
            "avg_session_duration": avg_session_duration,
            "best_session_accuracy": round(best_session_accuracy, 1),
            
            # Lists
            "recent_sessions": self._get_recent_sessions(user_data),
            "recent_performance": self._get_recent_performance(user_data),
            "performance_overview": self._get_performance_overview(user_data),
            "study_activity": self._get_study_activity(user_data),
            "recent_achievements": self._get_recent_achievements(user_data),
            "achievements": user_data.get("achievements", []),
            
            # Daily comparison data
            "daily_data": self._get_daily_comparison_data(user_data)
        }

    def get_analytics_stats(self, user_id: str) -> dict:
        """Get detailed analytics statistics - ALWAYS uses dashboard stats for consistency"""
        # Get the single source of truth
        stats = self.get_dashboard_stats(user_id)
        
        # Return the same data with any additional fields needed for analytics page
        return stats

    def reset_user_data(self, user_id: str):
        """Reset all user data to initial state"""
        data = self._load_data()
        
        if user_id not in data:
            data[user_id] = self._get_default_user_data()
        else:
            # Preserve display name if it exists
            display_name = data[user_id].get("display_name", user_id.replace("_", " ").title())
            created_date = data[user_id].get("created_date", datetime.now().isoformat())
            
            # Reset to default
            data[user_id] = self._get_default_user_data()
            data[user_id]["display_name"] = display_name
            data[user_id]["created_date"] = created_date
        
        self._save_data(data)
        return data[user_id]

    def _create_default_user_data(self, user_id: str) -> Dict[str, Any]:
        """Create default user data with user-specific info"""
        data = self._get_default_user_data()
        data["display_name"] = user_id.replace("_", " ").title()
        data["created_date"] = datetime.now().isoformat()
        return data
    
    def _update_user_data(self, user_id: str, user_data: Dict[str, Any]):
        """Update user data in storage"""
        data = self._load_data()
        data[user_id] = user_data
        self._save_data(data)
    
    def _get_recent_sessions(self, user_data: dict) -> list:
        """Get recent session data for display"""
        sessions = []
        session_history = user_data.get("session_history", [])
        
        # Get last 5 sessions
        for session in session_history[-5:]:
            sessions.append({
                "date": session.get("start_time", ""),
                "questions": session.get("questions_answered", 0),
                "correct": session.get("questions_correct", 0),
                "accuracy": round((session.get("questions_correct", 0) / session.get("questions_answered", 1)) * 100, 1) if session.get("questions_answered", 0) > 0 else 0
            })
        
        return sessions
    
    def _get_recent_performance(self, user_data: dict) -> list:
        """Get recent performance metrics"""
        performance = []
        
        # Generate last 7 days of performance data
        for i in range(7):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            # For now, return sample data - you can enhance this with actual daily tracking
            performance.append({
                "date": date,
                "accuracy": user_data.get("accuracy", 0),
                "questions": 0  # Would need daily tracking to be accurate
            })
        
        return performance
    
    def _get_performance_overview(self, user_data: dict) -> dict:
        """Get performance overview statistics"""
        return {
            "total_questions": user_data.get("total_questions", 0),
            "correct_answers": user_data.get("correct_answers", 0),
            "accuracy": user_data.get("accuracy", 0),
            "avg_time_per_question": 30,  # Default average
            "topics_mastered": len([t for t, d in user_data.get("topics_studied", {}).items() if self._calculate_topic_accuracy(d) >= 80]),
            "improvement_rate": 0  # Would need historical tracking
        }
    
    def _get_study_activity(self, user_data: dict) -> list:
        """Get study activity data for charts"""
        activity = []
        
        # Generate last 30 days of activity
        for i in range(30):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            # For now, return sample data
            activity.append({
                "date": date,
                "minutes": 0,  # Would need daily tracking
                "questions": 0  # Would need daily tracking
            })
        
        return activity
    
    def _get_daily_comparison_data(self, user_data: dict) -> dict:
        """Get daily comparison data for today vs yesterday"""
        daily_data = user_data.get("daily_data", {})
        today_data = daily_data.get("today", {})
        yesterday_data = daily_data.get("yesterday", {})
        
        # Get data from time tracking service for quiz and study times
        try:
            from services.time_tracking_service import get_time_tracker
            time_tracker = get_time_tracker()
            time_summary = time_tracker.get_daily_summary()
            today_quiz_time = time_summary.get("quiz_time_today", 0)
        except ImportError:
            today_quiz_time = 0
            
        return {
            "today": {
                "correct_answers": today_data.get("correct_answers", 0),
                "total_questions": today_data.get("total_questions", 0),
                "quiz_time": today_quiz_time,
                "study_time": today_data.get("study_time", 0)
            },
            "yesterday": {
                "correct_answers": yesterday_data.get("correct_answers", 0),
                "total_questions": yesterday_data.get("total_questions", 0),
                "quiz_time": yesterday_data.get("quiz_time", 0),
                "study_time": yesterday_data.get("study_time", 0)
            }
        }
    
    def _get_recent_achievements(self, user_data: dict) -> list:
        """Get recently earned achievements"""
        achievements = user_data.get("achievements", [])
        
        # Sort by earned date and return last 5
        sorted_achievements = sorted(
            achievements, 
            key=lambda x: x.get("earned_date", ""), 
            reverse=True
        )
        
        return sorted_achievements[:5]
    
    def get_heatmap_data(self, user_id: str) -> list:
        """Get study activity heatmap data for the last year"""
        user_data = self.get_user_data(user_id)
        session_history = user_data.get("session_history", [])
        activity_map = {}
        
        # Create a map of dates to activity counts from actual session data
        for session in session_history:
            session_date = session.get("start_time")
            if session_date:
                try:
                    # Convert session date to date string
                    if isinstance(session_date, str):
                        # Try to parse ISO format date
                        session_dt = datetime.fromisoformat(session_date.replace('Z', '+00:00'))
                        date_str = session_dt.strftime("%Y-%m-%d")
                    else:
                        date_str = session_date.strftime("%Y-%m-%d")
                    
                    questions = session.get("questions_answered", 0)
                    if date_str not in activity_map:
                        activity_map[date_str] = 0
                    activity_map[date_str] += questions
                except (ValueError, AttributeError):
                    continue
        
        # Generate heatmap data for the past year
        today = datetime.now()
        heatmap_data = []
        
        for i in range(365):
            current_date = today - timedelta(days=i)
            date_str = current_date.strftime("%Y-%m-%d")
            questions_count = activity_map.get(date_str, 0)
            
            # Calculate activity level (0-4 scale for GitHub-style heatmap)
            level = 0
            if questions_count > 0:
                if questions_count >= 20:
                    level = 4  # Very high activity
                elif questions_count >= 15:
                    level = 3  # High activity
                elif questions_count >= 10:
                    level = 2  # Medium activity
                else:
                    level = 1  # Low activity
            
            heatmap_data.append({
                "date": date_str,
                "questions": questions_count,
                "level": level
            })
        
        # Sort by date (oldest first for proper display)
        heatmap_data.sort(key=lambda x: x["date"])
        return heatmap_data

# Global instance
_analytics_manager = None

def get_analytics_manager() -> SimpleAnalyticsManager:
    """Get global analytics manager instance"""
    global _analytics_manager
    if _analytics_manager is None:
        _analytics_manager = SimpleAnalyticsManager()
    return _analytics_manager
