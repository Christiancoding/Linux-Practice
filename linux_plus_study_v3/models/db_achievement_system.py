#!/usr/bin/env python3
"""
Database-based Achievement System for Linux+ Study Game (Fixed Version)

Manages badges, progress tracking, and achievement calculations using database storage.
Fixed to handle SQLAlchemy session management properly.
"""

from typing import Dict, Any, List, Optional, Tuple, Set, TypedDict, cast
from datetime import datetime, date
from contextlib import contextmanager
from utils.game_values import get_game_value_manager
from utils.database import get_db_session
from models.user_achievements import UserAchievement, UserHistory, TimeTracking


class LeaderboardEntry(TypedDict):
    """Type definition for leaderboard entries."""
    date: str
    score: int
    total: int
    accuracy: float
    points: int


class DBAchievementSystem:
    """Database-based achievement system that replaces JSON file storage."""
    
    def __init__(self, user_id: str = 'anonymous'):
        """
        Initialize the database achievement system.
        
        Args:
            user_id: User identifier for achievements
        """
        self.user_id = user_id
        self.session_points = 0
    
    @contextmanager
    def _get_user_achievement(self):
        """Context manager to get user achievement with proper session handling."""
        with get_db_session() as session:
            user_achievement = session.query(UserAchievement).filter_by(user_id=self.user_id).first()
            if not user_achievement:
                # Create new record with defaults
                user_achievement = UserAchievement(user_id=self.user_id)
                session.add(user_achievement)
                session.commit()
                session.refresh(user_achievement)
            yield user_achievement, session
    
    def _save_user_achievement_data(self, **updates) -> None:
        """Save user achievement data with updates."""
        with get_db_session() as session:
            user_achievement = session.query(UserAchievement).filter_by(user_id=self.user_id).first()
            if not user_achievement:
                user_achievement = UserAchievement(user_id=self.user_id)
                session.add(user_achievement)
            
            # Apply updates
            for field, value in updates.items():
                if hasattr(user_achievement, field):
                    setattr(user_achievement, field, value)
            
            session.commit()
    
    @property
    def achievements(self) -> Dict[str, Any]:
        """Get achievements in dictionary format for compatibility."""
        with self._get_user_achievement() as (user_achievement, session):
            return user_achievement.to_dict()
    
    @property 
    def leaderboard(self) -> List[Dict[str, Any]]:
        """Get leaderboard data."""
        with self._get_user_achievement() as (user_achievement, session):
            return user_achievement.leaderboard or []
    
    @leaderboard.setter
    def leaderboard(self, value: List[Dict[str, Any]]) -> None:
        """Set leaderboard data."""
        self._save_user_achievement_data(leaderboard=value)
    
    def load_achievements(self) -> Dict[str, Any]:
        """Load achievements from database."""
        return self.achievements
    
    def save_achievements(self) -> None:
        """Save achievements to database."""
        # This is handled automatically when we update the user_achievement record
        pass
    
    def load_leaderboard(self) -> List[Dict[str, Any]]:
        """Load leaderboard data."""
        return self.leaderboard
    
    def update_points(self, points_change: int, apply_multiplier: bool = True) -> None:
        """
        Update points and session points.
        
        Args:
            points_change (int): Points to add (can be negative)
            apply_multiplier (bool): Whether to apply XP multiplier (default True)
        """
        final_points = points_change
        if apply_multiplier and points_change > 0:
            final_points = self.apply_xp_multiplier(points_change)
        
        self.session_points += final_points
        
        # Only add positive points to total earned
        if final_points > 0:
            with self._get_user_achievement() as (user_achievement, session):
                current_points = user_achievement.points_earned or 0
                user_achievement.points_earned = current_points + final_points
                session.commit()
    
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
        
        with self._get_user_achievement() as (user_achievement, session):
            # Add today to days studied
            # Explicitly cast to List[str] so the set has a known element type for type checkers
            existing_days: List[str] = cast(List[str], user_achievement.days_studied or [])
            days_studied: Set[str] = set(existing_days)
            days_studied.add(today)
            user_achievement.days_studied = list(days_studied)
            
            # Update questions answered
            if questions_answered is not None:
                user_achievement.questions_answered = questions_answered
            else:
                user_achievement.questions_answered = (user_achievement.questions_answered or 0) + 1
            
            badges = user_achievement.badges or []
            
            # Check for streak master achievement
            if (streak_count >= 5 and "streak_master" not in badges):
                new_badges.append("streak_master")
                badges.append("streak_master")
                user_achievement.streaks_achieved = (user_achievement.streaks_achieved or 0) + 1
            
            # Check for dedicated learner achievement
            game_values = get_game_value_manager()
            daily_streak_threshold = game_values.get_value('streaks', 'daily_streak_threshold', 3)
            
            if (len(days_studied) >= daily_streak_threshold and "dedicated_learner" not in badges):
                new_badges.append("dedicated_learner")
                badges.append("dedicated_learner")
            
            # Check for century club achievement
            question_threshold = game_values.get_value('scoring', 'achievement_question_threshold', 100)
            if (user_achievement.questions_answered >= question_threshold and "century_club" not in badges):
                new_badges.append("century_club")
                badges.append("century_club")
            
            # Check for point collector achievement
            point_threshold = game_values.get_value('scoring', 'achievement_point_threshold', 500)
            if (user_achievement.points_earned >= point_threshold and "point_collector" not in badges):
                new_badges.append("point_collector")
                badges.append("point_collector")
            
            user_achievement.badges = badges
            session.commit()
        
        return new_badges
    
    def award_badge(self, badge_name: str) -> bool:
        """
        Award a specific badge.
        
        Args:
            badge_name (str): Name of the badge to award
            
        Returns:
            bool: True if badge was newly awarded, False if already had it
        """
        with self._get_user_achievement() as (user_achievement, session):
            badges = user_achievement.badges or []
            
            if badge_name not in badges:
                badges.append(badge_name)
                user_achievement.badges = badges
                session.commit()
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
        with self._get_user_achievement() as (user_achievement, session):
            badges = user_achievement.badges or []
            
            if (session_total >= 3 and 
                session_score == session_total and 
                "perfect_session" not in badges):
                
                badges.append("perfect_session")
                user_achievement.badges = badges
                user_achievement.perfect_sessions = (user_achievement.perfect_sessions or 0) + 1
                session.commit()
                return True
        return False
    
    def complete_daily_challenge(self) -> bool:
        """
        Mark daily challenge completion and award badge if appropriate.
        
        Returns:
            bool: True if daily warrior badge was awarded
        """
        today_iso = datetime.now().date().isoformat()
        
        with self._get_user_achievement() as (user_achievement, session):
            daily_dates = user_achievement.daily_warrior_dates or []
            badges = user_achievement.badges or []
            
            # Add today's date if not already present
            if today_iso not in daily_dates:
                daily_dates.append(today_iso)
                user_achievement.daily_warrior_dates = daily_dates
            
            # Award badge if criteria met
            if ("daily_warrior" not in badges and len(daily_dates) >= 1):
                badges.append("daily_warrior")
                user_achievement.badges = badges
                session.commit()
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
        
        with self._get_user_achievement() as (user_achievement, session):
            unlocked_badges = set(user_achievement.badges or [])
            
            game_values = get_game_value_manager()
            # Use public API only; do not reload or mutate private settings
            question_threshold = game_values.get_value('scoring', 'achievement_question_threshold', 100)
            point_threshold = game_values.get_value('scoring', 'achievement_point_threshold', 500)
            daily_streak_threshold = game_values.get_value('streaks', 'daily_streak_threshold', 3)
            
            # Questions progress (century club)
            if "century_club" not in unlocked_badges:
                questions = user_achievement.questions_answered or 0
                progress["century_club"] = {
                    "current": questions,
                    "target": question_threshold,
                    "percentage": min((questions / question_threshold) * 100, 100) if question_threshold > 0 else 100
                }
            
            # Points progress (point collector)
            if "point_collector" not in unlocked_badges:
                points = user_achievement.points_earned or 0
                progress["point_collector"] = {
                    "current": points,
                    "target": point_threshold,
                    "percentage": min((points / point_threshold) * 100, 100) if point_threshold > 0 else 100
                }
            
            # Days studied progress (dedicated learner)
            if "dedicated_learner" not in unlocked_badges:
                days = len(user_achievement.days_studied or [])
                progress["dedicated_learner"] = {
                    "current": days,
                    "target": daily_streak_threshold,
                    "percentage": min((days / daily_streak_threshold) * 100, 100) if daily_streak_threshold > 0 else 100
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
        
        with self._get_user_achievement() as (user_achievement, session):
            leaderboard = user_achievement.leaderboard or []
            leaderboard.append(entry)
            
            # Keep only top 10 sessions, sorted by accuracy then points
            leaderboard.sort(
                key=lambda x: (x["accuracy"], x["points"]), 
                reverse=True
            )
            leaderboard = leaderboard[:10]
            
            user_achievement.leaderboard = leaderboard
            session.commit()
    
    def get_leaderboard(self) -> List[Dict[str, Any]]:
        """
        Get current leaderboard data.
        
        Returns:
            list: Sorted leaderboard entries
        """
        with self._get_user_achievement() as (user_achievement, session):
            return (user_achievement.leaderboard or []).copy()
    
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
        with self._get_user_achievement() as (user_achievement, session):
            total_points = user_achievement.points_earned or 0
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
        with self._get_user_achievement() as (user_achievement, session):
            level_info = self.get_level_progress()
            
            return {
                "total_points": user_achievement.points_earned or 0,
                "session_points": self.session_points,
                "questions_answered": user_achievement.questions_answered or 0,
                "days_studied": len(user_achievement.days_studied or []),
                "badges_earned": len(user_achievement.badges or []),
                "streaks_achieved": user_achievement.streaks_achieved or 0,
                "perfect_sessions": user_achievement.perfect_sessions or 0,
                "daily_challenges": len(user_achievement.daily_warrior_dates or []),
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
        with self._get_user_achievement() as (user_achievement, session):
            return badge_name in (user_achievement.badges or [])
    
    def get_badges(self) -> List[str]:
        """
        Get list of earned badges.
        
        Returns:
            list: List of earned badge names
        """
        with self._get_user_achievement() as (user_achievement, session):
            return (user_achievement.badges or []).copy()
    
    def get_survival_high_score(self) -> int:
        """
        Get the current survival mode high score (questions correct).
        
        Returns:
            int: Current survival mode high score
        """
        with self._get_user_achievement() as (user_achievement, session):
            return user_achievement.survival_high_score or 0
    
    def get_survival_high_score_xp(self) -> int:
        """
        Get the current survival mode XP high score.
        
        Returns:
            int: Current survival mode XP high score
        """
        with self._get_user_achievement() as (user_achievement, session):
            return user_achievement.survival_high_score_xp or 0
    
    def update_survival_high_score(self, score: int) -> bool:
        """
        Update survival mode high score (questions correct) if the new score is higher.
        
        Args:
            score (int): New score to potentially set as high score
            
        Returns:
            bool: True if high score was updated, False otherwise
        """
        with self._get_user_achievement() as (user_achievement, session):
            current_high_score = user_achievement.survival_high_score or 0
            if score > current_high_score:
                user_achievement.survival_high_score = score
                session.commit()
                return True
        return False
    
    def update_survival_high_score_xp(self, xp: int) -> bool:
        """
        Update survival mode XP high score if the new XP is higher.
        
        Args:
            xp (int): New XP to potentially set as high score
            
        Returns:
            bool: True if XP high score was updated, False otherwise
        """
        with self._get_user_achievement() as (user_achievement, session):
            current_high_score_xp = user_achievement.survival_high_score_xp or 0
            if xp > current_high_score_xp:
                user_achievement.survival_high_score_xp = xp
                session.commit()
                return True
        return False
    
    def clear_achievements(self) -> None:
        """Clear all achievement data."""
        self._save_user_achievement_data(
            badges=[],
            points_earned=0,
            days_studied=[],
            questions_answered=0,
            streaks_achieved=0,
            perfect_sessions=0,
            daily_warrior_dates=[],
            leaderboard=[],
            survival_high_score=0,
            survival_high_score_xp=0,
            custom_achievements=[]
        )
        self.session_points = 0
    
    def apply_xp_multiplier(self, base_points: int) -> int:
        """
        Apply XP multiplier to base points.
        
        Args:
            base_points (int): Base points before multiplier
            
        Returns:
            int: Points after applying multiplier
        """
        from utils.game_values import get_game_value_manager
        game_values = get_game_value_manager()
        # Use public API only; do not reload or mutate private settings
        multiplier = game_values.get_value('scoring', 'xp_multiplier', 1.0)
        return int(base_points * multiplier)
    
    def _get_default_achievements(self) -> Dict[str, Any]:
        """
        Get default achievement structure for backward compatibility.
        
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
            "leaderboard": [],
            "survival_high_score": 0,
            "survival_high_score_xp": 0,
            "custom_achievements": []
        }