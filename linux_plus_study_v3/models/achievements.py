#!/usr/bin/env python3
"""
Achievement System for Linux+ Study Game

Manages badges, progress tracking, and achievement calculations.
"""

import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Set, TypedDict, cast
from datetime import datetime, date
from utils.game_values import get_game_value_manager
from utils.config import ACHIEVEMENTS_FILE


class LeaderboardEntry(TypedDict):
    """Type definition for leaderboard entries."""
    date: str
    score: int
    total: int
    accuracy: float
    points: int


class AchievementData(TypedDict, total=False):
    """Type definition for achievement data structure."""
    badges: List[str]
    points_earned: int
    days_studied: Set[str]
    questions_answered: int
    streaks_achieved: int
    perfect_sessions: int
    daily_warrior_dates: List[str]
    leaderboard: List[LeaderboardEntry]


class AchievementSystem:
    """Manages achievements, badges, points, and leaderboard."""
    
    achievements: Dict[str, Any]
    leaderboard: List[Dict[str, Any]]
    session_points: int
    
    def __init__(self, achievements_file: Any = ACHIEVEMENTS_FILE):
        """
        Initialize the achievement system.
        
        Args:
            achievements_file: Path to achievements data file
        """
        self.achievements_file = str(achievements_file)
        self.achievements = self.load_achievements()
        self.leaderboard = self.load_leaderboard()
        self.session_points = 0
    
    def load_achievements(self) -> Dict[str, Any]:
        """
        Load achievements from file.
        
        Returns:
            dict: Achievement data with default structure if file doesn't exist
        """
        try:
            with open(self.achievements_file, 'r', encoding='utf-8') as f:
                achievements = json.load(f)
                
            # Ensure all required keys exist
            default_achievements = self._get_default_achievements()
            for key, default_value in default_achievements.items():
                achievements.setdefault(key, default_value)
            
            # Convert days_studied to set if it's a list (for backwards compatibility)
            if isinstance(achievements.get("days_studied"), list):
                achievements["days_studied"] = set(achievements["days_studied"])
            elif not isinstance(achievements.get("days_studied"), set):
                achievements["days_studied"] = set()
            
            return achievements
            
        except (FileNotFoundError, json.JSONDecodeError):
            return self._get_default_achievements()
        except Exception as e:
            print(f"Error loading achievements: {e}")
            return self._get_default_achievements()
    
    def save_achievements(self) -> None:
        """Save achievements to file."""
        try:
            # Convert set to list for JSON serialization
            achievements_copy = self.achievements.copy()
            if isinstance(achievements_copy.get("days_studied"), set):
                achievements_copy["days_studied"] = list(achievements_copy["days_studied"])
            
            with open(self.achievements_file, 'w', encoding='utf-8') as f:
                json.dump(achievements_copy, f, indent=2)
                
        except Exception as e:
            print(f"Error saving achievements: {e}")
    
    def load_leaderboard(self) -> List[Dict[str, Any]]:
        """
        Load leaderboard data.
        
        Returns:
            list: Leaderboard entries
        """
        # For now, leaderboard is stored within achievements or loaded separately
        # This can be modified to use a separate file if needed
        leaderboard_data = self.achievements.get("leaderboard", [])
        if isinstance(leaderboard_data, list):
            # Use cast to tell the type checker this is the correct type
            return cast(List[Dict[str, Any]], leaderboard_data)
        else:
            return []
    
    def update_points(self, points_change: int) -> None:
        """
        Update points and session points.
        
        Args:
            points_change (int): Points to add (can be negative)
        """
        self.session_points += points_change
        
        # Only add positive points to total earned
        if points_change > 0:
            self.achievements["points_earned"] = self.achievements.get("points_earned", 0) + points_change
    
    def check_achievements(self, is_correct: bool, streak_count: int, questions_answered: Optional[int] = None) -> List[str]:
        """
        Check and award achievements based on performance.
        
        Args:
            is_correct (bool): Whether the last question was answered correctly
            streak_count (int): Current streak count
            questions_answered (int): Total questions answered (optional)
            
        Returns:
            list: List of newly earned badge names
        """
        new_badges: List[str] = []
        today = datetime.now().date().isoformat()
        
        # Add today to days studied
        if not isinstance(self.achievements.get("days_studied"), set):
            self.achievements["days_studied"] = set()
        days_studied = cast(Set[str], self.achievements["days_studied"])
        days_studied.add(today)
        
        # Update questions answered
        if questions_answered is not None:
            self.achievements["questions_answered"] = questions_answered
        else:
            self.achievements["questions_answered"] = self.achievements.get("questions_answered", 0) + 1
        
        # Check for streak master achievement
        if (streak_count >= 5 and 
            "streak_master" not in self.achievements["badges"]):
            new_badges.append("streak_master")
            self.achievements["badges"].append("streak_master")
            self.achievements["streaks_achieved"] = self.achievements.get("streaks_achieved", 0) + 1
        
        # Check for dedicated learner achievement
        days_studied = cast(Set[str], self.achievements["days_studied"])
        game_values = get_game_value_manager()
        daily_streak_threshold = game_values.get_value('streaks', 'daily_streak_threshold', 3)
        
        if (len(days_studied) >= daily_streak_threshold and 
            "dedicated_learner" not in self.achievements["badges"]):
            new_badges.append("dedicated_learner")
            self.achievements["badges"].append("dedicated_learner")
        
        # Check for century club achievement (configurable question threshold)
        question_threshold = game_values.get_value('scoring', 'achievement_question_threshold', 100)
        if (self.achievements["questions_answered"] >= question_threshold and 
            "century_club" not in self.achievements["badges"]):
            new_badges.append("century_club")
            self.achievements["badges"].append("century_club")
        
        # Check for point collector achievement (configurable point threshold)
        point_threshold = game_values.get_value('scoring', 'achievement_point_threshold', 500)
        if (self.achievements["points_earned"] >= point_threshold and 
            "point_collector" not in self.achievements["badges"]):
            new_badges.append("point_collector")
            self.achievements["badges"].append("point_collector")
        
        return new_badges
    
    def award_badge(self, badge_name: str) -> bool:
        """
        Award a specific badge.
        
        Args:
            badge_name (str): Name of the badge to award
            
        Returns:
            bool: True if badge was newly awarded, False if already had it
        """
        if badge_name not in self.achievements["badges"]:
            self.achievements["badges"].append(badge_name)
            return True
        return False
    
    def check_perfect_session(self, session_score: int, session_total: int) -> bool:
        """
        Check and award perfect session achievement.
        
        Args:
            session_score (int): Number of correct answers
            session_total (int): Total questions in session
            
        Returns:
            bool: True if perfect session badge was awarded
        """
        if (session_total >= 3 and 
            session_score == session_total and 
            "perfect_session" not in self.achievements["badges"]):
            
            self.achievements["badges"].append("perfect_session")
            self.achievements["perfect_sessions"] = self.achievements.get("perfect_sessions", 0) + 1
            return True
        return False
    
    def complete_daily_challenge(self) -> bool:
        """
        Mark daily challenge completion and award badge if appropriate.
        
        Returns:
            bool: True if daily warrior badge was awarded
        """
        today_iso = datetime.now().date().isoformat()
        
        # Ensure daily_warrior_dates exists
        self.achievements.setdefault("daily_warrior_dates", [])
        
        # Convert set to list if needed
        if isinstance(self.achievements["daily_warrior_dates"], set):
            daily_dates_set = cast(Set[str], self.achievements["daily_warrior_dates"])
            self.achievements["daily_warrior_dates"] = list(daily_dates_set)
        
        # Add today's date if not already present
        daily_dates = cast(List[str], self.achievements["daily_warrior_dates"])
        if today_iso not in daily_dates:
            daily_dates.append(today_iso)
        
        # Award badge if criteria met
        if ("daily_warrior" not in self.achievements["badges"] and 
            len(daily_dates) >= 1):
            self.achievements["badges"].append("daily_warrior")
            return True
        
        return False
    
    def complete_quick_fire(self) -> bool:
        """
        Award Quick Fire champion badge.
        
        Returns:
            bool: True if badge was newly awarded
        """
        return self.award_badge("quick_fire_champion")
    
    def get_achievement_description(self, badge_name: str) -> str:
        """
        Get description for achievement badge with dynamic values.
        
        Args:
            badge_name (str): Name of the badge
            
        Returns:
            str: Formatted description with emoji
        """
        game_values = get_game_value_manager()
        question_threshold = game_values.get_value('scoring', 'achievement_question_threshold', 100)
        point_threshold = game_values.get_value('scoring', 'achievement_point_threshold', 500)
        daily_streak_threshold = game_values.get_value('streaks', 'daily_streak_threshold', 3)
        
        descriptions = {
            "streak_master": "🔥 Streak Master - Answered 5 questions in a row correctly!",
            "dedicated_learner": f"📚 Dedicated Learner - Studied {daily_streak_threshold} days in a row!",
            "century_club": f"💯 Century Club - Answered {question_threshold} questions!",
            "point_collector": f"⭐ Point Collector - Earned {point_threshold} points!",
            "quick_fire_champion": "⚡ Quick Fire Champion - Completed Quick Fire mode!",
            "daily_warrior": "🗓️ Daily Warrior - Completed daily challenge!",
            "perfect_session": "🎯 Perfect Session - 100% accuracy in a session!"
        }
        
        return descriptions.get(badge_name, f"🏆 Achievement: {badge_name}")
    
    def get_all_achievement_definitions(self) -> Dict[str, str]:
        """
        Get all available achievement definitions with dynamic values.
        
        Returns:
            dict: Achievement names mapped to requirements descriptions
        """
        game_values = get_game_value_manager()
        question_threshold = game_values.get_value('scoring', 'achievement_question_threshold', 100)
        point_threshold = game_values.get_value('scoring', 'achievement_point_threshold', 500)
        daily_streak_threshold = game_values.get_value('streaks', 'daily_streak_threshold', 3)
        
        return {
            "streak_master": "Answer 5 questions correctly in a row",
            "dedicated_learner": f"Study for {daily_streak_threshold} different days",
            "century_club": f"Answer {question_threshold} questions total",
            "point_collector": f"Earn {point_threshold} points",
            "quick_fire_champion": "Complete Quick Fire mode",
            "daily_warrior": "Complete a daily challenge",
            "perfect_session": "Get 100% accuracy in a session (3+ questions)"
        }
    
    def get_progress_toward_achievements(self) -> Dict[str, Dict[str, Any]]:
        """
        Get progress data toward unearned achievements.
        
        Returns:
            dict: Progress data for each unearned achievement
        """
        progress: Dict[str, Dict[str, Any]] = {}
        unlocked_badges = set(self.achievements.get("badges", []))
        
        # Questions progress (century club)
        if "century_club" not in unlocked_badges:
            questions = self.achievements.get("questions_answered", 0)
            progress["century_club"] = {
                "current": questions,
                "target": 100,
                "percentage": min((questions / 100) * 100, 100)
            }
        
        # Points progress (point collector)
        if "point_collector" not in unlocked_badges:
            points = self.achievements.get("points_earned", 0)
            progress["point_collector"] = {
                "current": points,
                "target": 500,
                "percentage": min((points / 500) * 100, 100)
            }
        
        # Days studied progress (dedicated learner)
        if "dedicated_learner" not in unlocked_badges:
            days = len(self.achievements.get("days_studied", []))
            progress["dedicated_learner"] = {
                "current": days,
                "target": 3,
                "percentage": min((days / 3) * 100, 100)
            }
        
        return progress
    
    def update_leaderboard(self, session_score: int, session_total: int, session_points: int) -> None:
        """
        Update leaderboard with session performance.
        
        Args:
            session_score (int): Number of correct answers
            session_total (int): Total questions answered
            session_points (int): Points earned in session
        """
        if session_total == 0:
            return
        
        accuracy = (session_score / session_total) * 100
        entry: Dict[str, Any] = {
            "date": datetime.now().isoformat(),
            "score": session_score,
            "total": session_total,
            "accuracy": accuracy,
            "points": session_points
        }
        
        self.leaderboard.append(entry)
        
        # Keep only top 10 sessions, sorted by accuracy then points
        self.leaderboard.sort(
            key=lambda x: (x["accuracy"], x["points"]), 
            reverse=True
        )
        self.leaderboard = self.leaderboard[:10]
        
        # Store in achievements for persistence
        self.achievements["leaderboard"] = self.leaderboard
    
    def get_leaderboard(self) -> List[Dict[str, Any]]:
        """
        Get current leaderboard data.
        
        Returns:
            list: Sorted leaderboard entries
        """
        return self.leaderboard.copy()
    
    def calculate_level_from_points(self, points: int) -> int:
        """
        Calculate level based on total points earned.
        
        Args:
            points (int): Total points earned
            
        Returns:
            int: Current level (starting from 1)
        """
        if points <= 0:
            return 1
            
        # Level progression: 100 points for level 2, 200 for level 3, etc.
        # Formula: level = floor(sqrt(points / 50)) + 1
        import math
        level = int(math.sqrt(points / 50)) + 1
        return max(1, level)
    
    def calculate_xp_for_level(self, level: int) -> int:
        """
        Calculate total XP required for a specific level.
        
        Args:
            level (int): Target level
            
        Returns:
            int: Total XP required for that level
        """
        if level <= 1:
            return 0
        return (level - 1) ** 2 * 50
    
    def get_level_progress(self) -> Dict[str, Any]:
        """
        Get current level and progress to next level.
        
        Returns:
            dict: Level information including current level, XP, and progress
        """
        total_points = self.achievements.get("points_earned", 0)
        current_level = self.calculate_level_from_points(total_points)
        current_level_xp = self.calculate_xp_for_level(current_level)
        next_level_xp = self.calculate_xp_for_level(current_level + 1)
        
        xp_in_current_level = total_points - current_level_xp
        xp_needed_for_next = next_level_xp - current_level_xp
        progress_percentage = (xp_in_current_level / xp_needed_for_next * 100) if xp_needed_for_next > 0 else 0
        
        return {
            "level": current_level,
            "total_xp": total_points,
            "current_level_xp": xp_in_current_level,
            "xp_for_next_level": xp_needed_for_next,
            "progress_percentage": min(100, max(0, progress_percentage))
        }

    def get_statistics_summary(self) -> Dict[str, Any]:
        """
        Get summary statistics for achievements.
        
        Returns:
            dict: Summary of achievement-related statistics
        """
        level_info = self.get_level_progress()
        
        return {
            "total_points": self.achievements.get("points_earned", 0),
            "session_points": self.session_points,
            "questions_answered": self.achievements.get("questions_answered", 0),
            "days_studied": len(self.achievements.get("days_studied", [])),
            "badges_earned": len(self.achievements.get("badges", [])),
            "streaks_achieved": self.achievements.get("streaks_achieved", 0),
            "perfect_sessions": self.achievements.get("perfect_sessions", 0),
            "daily_challenges": len(self.achievements.get("daily_warrior_dates", [])),
            "level": level_info["level"],
            "total_xp": level_info["total_xp"],
            "level_progress": level_info["progress_percentage"]
        }
    
    def reset_session_points(self) -> None:
        """Reset session points counter."""
        self.session_points = 0
    
    def has_badge(self, badge_name: str) -> bool:
        """
        Check if a specific badge has been earned.
        
        Args:
            badge_name (str): Name of the badge to check
            
        Returns:
            bool: True if badge has been earned
        """
        return badge_name in self.achievements.get("badges", [])
    
    def get_badges(self) -> List[str]:
        """
        Get list of earned badges.
        
        Returns:
            list: List of earned badge names
        """
        return self.achievements.get("badges", []).copy()
    
    def clear_achievements(self) -> None:
        """Clear all achievement data."""
        self.achievements = self._get_default_achievements()
        self.leaderboard = []
        self.session_points = 0
    
    def _get_default_achievements(self) -> Dict[str, Any]:
        """
        Get default achievement structure.
        
        Returns:
            dict: Default achievement data structure
        """
        return {
            "badges": [],
            "points_earned": 0,
            "days_studied": set(),
            "questions_answered": 0,
            "streaks_achieved": 0,
            "perfect_sessions": 0,
            "daily_warrior_dates": [],
            "leaderboard": []
        }