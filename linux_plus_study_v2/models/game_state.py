#!/usr/bin/env python3
"""
Game State Model for Linux+ Study Game

Manages the overall game state, coordinates between different subsystems,
and handles persistence of game data and progress.
"""

import json
import os
import random
import time
from datetime import datetime
from typing import Optional, Dict, List, Tuple, Any

from utils.config import *
from models.question import QuestionManager
from models.achievements import AchievementSystem


class GameState:
    """
    Central game state manager that coordinates all game subsystems.
    
    This class serves as the main model that views and controllers interact with.
    It manages questions, achievements, history, and current session state.
    """
    
    def __init__(self, history_file: str = str(HISTORY_FILE)):
        """
        Initialize the game state.
        
        Args:
            history_file (str): Path to the history file
        """
        self.history_file = history_file
        
        # Initialize subsystems
        self.question_manager = QuestionManager()
        self.achievement_system = AchievementSystem()
        
        # Load game history
        self.study_history = self.load_history()
        
        # Current session state
        self.score = 0
        self.total_questions_session = 0
        self.answered_indices_session = []
        self.session_points = 0
        
        # Quick Fire mode state
        self.quick_fire_active = False
        self.quick_fire_start_time = None
        self.quick_fire_questions_answered = 0
        
        # Daily challenge state
        self.daily_challenge_completed = False
        self.last_daily_challenge_date = None
        
        # Verify mode session storage
        self.verify_session_answers = []
        
        # Sync achievement system with current session
        self.achievement_system.session_points = self.session_points
        
        # Ensure categories in history match loaded questions
        self._sync_categories_with_history()
    
    @property
    def questions(self) -> List[Tuple[str, List[str], int, str, str]]:
        """Get questions in tuple format for backwards compatibility."""
        return self.question_manager.get_question_tuples()
    
    @property
    def categories(self) -> set[str]:
        """Get set of question categories."""
        return self.question_manager.categories
    
    @property
    def achievements(self) -> Dict[str, Any]:
        """Get achievements data."""
        return self.achievement_system.achievements
    
    @property
    def leaderboard(self) -> List[Dict[str, Any]]:
        """Get leaderboard data."""
        return self.achievement_system.leaderboard
    
    def load_history(self) -> Dict[str, Any]:
        """
        Load study history from file.
        
        Returns:
            Dict: Study history data with default structure if file doesn't exist
        """
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
            
            # Ensure all default keys exist
            default = self._default_history()
            for key, default_value in default.items():
                history.setdefault(key, default_value)
            
            # Validate data types
            if not isinstance(history.get("questions"), dict):
                history["questions"] = {}
            if not isinstance(history.get("categories"), dict):
                history["categories"] = {}
            if not isinstance(history.get("sessions"), list):
                history["sessions"] = []
            if not isinstance(history.get("incorrect_review"), list):
                history["incorrect_review"] = []
            
            return history
            
        except (FileNotFoundError, json.JSONDecodeError):
            print(f"Info: History file not found or invalid. Starting fresh.")
            return self._default_history()
        except Exception as e:
            print(f"Error loading history file '{self.history_file}': {e}")
            print("Warning: Starting with empty history.")
            return self._default_history()
    
    def save_history(self):
        """Save study history to file."""
        try:
            # Update leaderboard in history before saving
            self.study_history["leaderboard"] = self.achievement_system.leaderboard
            
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.study_history, f, indent=2)
        except IOError as e:
            print(f"Error saving history: {e}")
        except Exception as e:
            print(f"An unexpected error occurred during history save: {e}")
    
    def save_achievements(self):
        """Save achievements data."""
        self.achievement_system.save_achievements()
    
    def update_history(self, question_text: str, category: str, is_correct: bool):
        """
        Update study history with the result of an answered question.
        
        Args:
            question_text (str): The question text
            category (str): Question category
            is_correct (bool): Whether the answer was correct
        """
        timestamp = datetime.now().isoformat()
        history = self.study_history
        
        # Overall totals
        history["total_attempts"] = history.get("total_attempts", 0) + 1
        if is_correct:
            history["total_correct"] = history.get("total_correct", 0) + 1
        
        # Question specific stats
        q_stats = history.setdefault("questions", {}).setdefault(
            question_text, {"correct": 0, "attempts": 0, "history": []}
        )
        q_stats["attempts"] += 1
        if is_correct:
            q_stats["correct"] += 1
            # Remove from review list if answered correctly
            if isinstance(history.get("incorrect_review"), list) and question_text in history["incorrect_review"]:
                try:
                    history["incorrect_review"].remove(question_text)
                except ValueError:
                    pass  # Ignore if somehow not present
        else:
            # Add to review list if incorrect and not already there
            if not isinstance(history.get("incorrect_review"), list):
                history["incorrect_review"] = []
            if question_text not in history["incorrect_review"]:
                history["incorrect_review"].append(question_text)
        
        # Ensure history list exists and add entry
        if not isinstance(q_stats.get("history"), list):
            q_stats["history"] = []
        q_stats["history"].append({"timestamp": timestamp, "correct": is_correct})
        
        # Category specific stats
        cat_stats = history.setdefault("categories", {}).setdefault(
            category, {"correct": 0, "attempts": 0}
        )
        cat_stats["attempts"] += 1
        if is_correct:
            cat_stats["correct"] += 1
    
    def select_question(self, category_filter: Optional[str] = None) -> Tuple[Optional[Tuple], int]:
        """
        Select a question using intelligent weighting based on performance history.
        
        Args:
            category_filter (str, optional): Category to filter questions by
            
        Returns:
            Tuple[Optional[Tuple], int]: (question_data, original_index) or (None, -1) if none available
        """
        question, index = self.question_manager.select_question(
            category_filter=category_filter,
            game_history=self.study_history
        )
        
        if question is None:
            return None, -1
        
        # Convert Question object back to tuple for backwards compatibility
        return question.to_tuple(), index
    
    def reset_session(self):
        """Reset session-specific data."""
        self.score = 0
        self.total_questions_session = 0
        self.answered_indices_session = []
        self.session_points = 0
        self.verify_session_answers = []
        self.question_manager.reset_session()
        self.achievement_system.reset_session_points()
    
    def start_quick_fire_mode(self) -> Dict[str, Any]:
        """
        Initialize Quick Fire mode.
        
        Returns:
            Dict: Quick Fire mode initialization data
        """
        self.quick_fire_active = True
        self.quick_fire_start_time = time.time()
        self.quick_fire_questions_answered = 0
        
        return {
            'active': True,
            'start_time': self.quick_fire_start_time,
            'time_limit': QUICK_FIRE_TIME_LIMIT,
            'question_limit': QUICK_FIRE_QUESTIONS
        }
    
    def check_quick_fire_status(self) -> bool:
        """
        Check if Quick Fire mode should continue.
        
        Returns:
            bool: True if should continue, False if should end
        """
        if not self.quick_fire_active:
            return False
        
        elapsed_time = time.time() - self.quick_fire_start_time
        
        # Check end conditions
        if elapsed_time > QUICK_FIRE_TIME_LIMIT:
            self.end_quick_fire_mode(time_up=True)
            return False
        elif self.quick_fire_questions_answered >= QUICK_FIRE_QUESTIONS:
            self.end_quick_fire_mode(time_up=False)
            return False
        
        return True
    
    def end_quick_fire_mode(self, time_up: bool = False) -> Dict[str, Any]:
        """
        End Quick Fire mode and return results.
        
        Args:
            time_up (bool): Whether time ran out
            
        Returns:
            Dict: Quick Fire completion data
        """
        if not self.quick_fire_active:
            return {'error': 'Quick Fire not active'}
        
        self.quick_fire_active = False
        elapsed_time = time.time() - self.quick_fire_start_time
        
        # Award achievement if completed successfully
        achievement_earned = False
        if not time_up and self.quick_fire_questions_answered >= QUICK_FIRE_QUESTIONS:
            achievement_earned = self.achievement_system.complete_quick_fire()
        
        return {
            'completed': not time_up,
            'time_up': time_up,
            'questions_answered': self.quick_fire_questions_answered,
            'target_questions': QUICK_FIRE_QUESTIONS,
            'elapsed_time': elapsed_time,
            'time_limit': QUICK_FIRE_TIME_LIMIT,
            'achievement_earned': achievement_earned
        }
    
    def get_daily_challenge_question(self) -> Tuple[Optional[Tuple], int]:
        """
        Get today's daily challenge question.
        
        Returns:
            Tuple[Optional[Tuple], int]: (question_data, index) or (None, -1) if unavailable
        """
        today = datetime.now().date().isoformat()
        
        # Check if already completed today
        if (self.last_daily_challenge_date == today and 
            self.daily_challenge_completed):
            return None, -1
        
        # Use date as seed for consistent daily question
        import hashlib
        date_hash = int(hashlib.md5(today.encode()).hexdigest()[:8], 16)
        
        if self.questions:
            question_index = date_hash % len(self.questions)
            self.last_daily_challenge_date = today
            return self.questions[question_index], question_index
        
        return None, -1
    
    def complete_daily_challenge(self, is_correct: bool) -> bool:
        """
        Mark daily challenge as complete and handle rewards.
        
        Args:
            is_correct (bool): Whether the challenge was answered correctly
            
        Returns:
            bool: True if daily warrior badge was awarded
        """
        today_iso = datetime.now().date().isoformat()
        self.daily_challenge_completed = True
        self.last_daily_challenge_date = today_iso
        
        if is_correct:
            return self.achievement_system.complete_daily_challenge()
        
        return False
    
    def update_points(self, points_change: int):
        """
        Update points in both session and achievement system.
        
        Args:
            points_change (int): Points to add (can be negative)
        """
        self.session_points += points_change
        self.achievement_system.update_points(points_change)
    
    def check_achievements(self, is_correct: bool, streak_count: int) -> List[str]:
        """
        Check and award achievements based on performance.
        
        Args:
            is_correct (bool): Whether the last question was correct
            streak_count (int): Current streak count
            
        Returns:
            List[str]: List of newly earned badge names
        """
        return self.achievement_system.check_achievements(
            is_correct, 
            streak_count, 
            self.total_questions_session
        )
    
    def get_achievement_description(self, badge_name: str) -> str:
        """
        Get description for achievement badge.
        
        Args:
            badge_name (str): Name of the badge
            
        Returns:
            str: Formatted description with emoji
        """
        return self.achievement_system.get_achievement_description(badge_name)
    
    def update_leaderboard(self, session_score: int, session_total: int, session_points: int):
        """
        Update leaderboard with session performance.
        
        Args:
            session_score (int): Number of correct answers
            session_total (int): Total questions answered
            session_points (int): Points earned in session
        """
        self.achievement_system.update_leaderboard(session_score, session_total, session_points)
    
    def get_question_count(self, category_filter: Optional[str] = None) -> int:
        """
        Get count of available questions.
        
        Args:
            category_filter (str, optional): Category to filter by
            
        Returns:
            int: Number of available questions
        """
        return self.question_manager.get_question_count(category_filter)
    
    def get_categories_list(self) -> List[str]:
        """
        Get sorted list of question categories.
        
        Returns:
            List[str]: Sorted category names
        """
        return self.question_manager.get_categories()
    
    def add_verify_answer(self, question_data: Tuple, user_answer: int, is_correct: bool):
        """
        Add an answer to the verify mode session.
        
        Args:
            question_data (Tuple): Question data tuple
            user_answer (int): User's answer index
            is_correct (bool): Whether the answer was correct
        """
        self.verify_session_answers.append((question_data, user_answer, is_correct))
    
    def get_verify_results(self) -> Dict[str, Any]:
        """
        Get verify mode session results.
        
        Returns:
            Dict: Verify mode results data
        """
        if not self.verify_session_answers:
            return {'error': 'No verify answers recorded'}
        
        num_correct = sum(1 for _, _, is_correct in self.verify_session_answers if is_correct)
        total_answered = len(self.verify_session_answers)
        accuracy = (num_correct / total_answered * 100) if total_answered > 0 else 0
        
        return {
            'total_answered': total_answered,
            'num_correct': num_correct,
            'accuracy': accuracy,
            'detailed_answers': self.verify_session_answers
        }
    
    def clear_verify_session(self):
        """Clear verify mode session data."""
        self.verify_session_answers = []
    
    def export_study_data(self, filename: str):
        """
        Export study history data to JSON file.
        
        Args:
            filename (str): Output filename
        """
        try:
            # Ensure we have the latest data
            export_data = self.study_history.copy()
            export_data["leaderboard"] = self.achievement_system.leaderboard
            export_data["achievements"] = self.achievement_system.achievements
            export_data["export_metadata"] = {
                "export_date": datetime.now().isoformat(),
                "total_questions_in_pool": len(self.questions),
                "categories_available": list(self.categories)
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2)
                
        except Exception as e:
            raise IOError(f"Failed to export study data: {e}")
    
    def export_questions(self, filename: str, format_type: str = "json"):
        """
        Export questions to file.
        
        Args:
            filename (str): Output filename
            format_type (str): Export format ("json", "md", or "csv")
        """
        self.question_manager.export_questions(filename, format_type)
    
    def get_statistics_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics summary.
        
        Returns:
            Dict: Statistics summary including history and achievements
        """
        history_stats = {
            'total_attempts': self.study_history.get('total_attempts', 0),
            'total_correct': self.study_history.get('total_correct', 0),
            'overall_accuracy': 0,
            'categories_attempted': 0,
            'questions_for_review': len(self.study_history.get('incorrect_review', []))
        }
        
        # Calculate overall accuracy
        if history_stats['total_attempts'] > 0:
            history_stats['overall_accuracy'] = (
                history_stats['total_correct'] / history_stats['total_attempts'] * 100
            )
        
        # Count categories with attempts
        categories_data = self.study_history.get('categories', {})
        history_stats['categories_attempted'] = sum(
            1 for stats in categories_data.values()
            if isinstance(stats, dict) and stats.get('attempts', 0) > 0
        )
        
        # Get achievement stats
        achievement_stats = self.achievement_system.get_statistics_summary()
        
        # Combine session stats
        session_stats = {
            'current_session_score': self.score,
            'current_session_total': self.total_questions_session,
            'current_session_points': self.session_points,
            'quick_fire_active': self.quick_fire_active
        }
        
        return {
            'history': history_stats,
            'achievements': achievement_stats,
            'session': session_stats,
            'question_pool': {
                'total_questions': len(self.questions),
                'categories_available': len(self.categories),
                'categories': list(self.categories)
            }
        }
    
    def _default_history(self) -> Dict[str, Any]:
        """
        Get the default structure for study history.
        
        Returns:
            Dict: Default history structure
        """
        return {
            "sessions": [],
            "questions": {},
            "categories": {},
            "total_correct": 0,
            "total_attempts": 0,
            "incorrect_review": [],
            "leaderboard": []
        }
    
    def _sync_categories_with_history(self):
        """Ensure all categories from questions exist in history."""
        for category in self.categories:
            self.study_history["categories"].setdefault(
                category, {"correct": 0, "attempts": 0}
            )
    
    def validate_state(self) -> List[str]:
        """
        Validate the current game state.
        
        Returns:
            List[str]: List of validation errors
        """
        errors = []
        
        # Validate questions
        question_errors = self.question_manager.validate_all_questions()
        errors.extend(question_errors)
        
        # Validate history structure
        if not isinstance(self.study_history, dict):
            errors.append("Study history is not a dictionary")
        
        required_history_keys = ["questions", "categories", "total_correct", "total_attempts", "incorrect_review"]
        for key in required_history_keys:
            if key not in self.study_history:
                errors.append(f"Missing required history key: {key}")
        
        # Validate achievements
        if not isinstance(self.achievements, dict):
            errors.append("Achievements data is not a dictionary")
        
        # Validate session state
        if self.score < 0:
            errors.append("Session score cannot be negative")
        
        if self.total_questions_session < 0:
            errors.append("Total questions session cannot be negative")
        
        return errors
    
    def reset_all_data(self):
        """Reset all game data to initial state."""
        self.study_history = self._default_history()
        self.achievement_system.clear_achievements()
        self.reset_session()
        self._sync_categories_with_history()
    def update_scoring_settings(self, points_per_question=10, streak_bonus=5, max_streak_bonus=50):
        """Update scoring settings for the game."""
        self.points_per_question = points_per_question
        self.streak_bonus = streak_bonus
        self.max_streak_bonus = max_streak_bonus
        
        # Save settings to prevent loss on restart
        self.save_settings()

    def save_settings(self):
        """Save current settings to game state."""
        try:
            settings = {
                'points_per_question': getattr(self, 'points_per_question', 10),
                'streak_bonus': getattr(self, 'streak_bonus', 5),
                'max_streak_bonus': getattr(self, 'max_streak_bonus', 50)
            }
            
            # Save to game state history
            self.study_history['settings'] = settings
            self.save_history()
        except Exception as e:
            print(f"Error saving settings to game state: {e}")