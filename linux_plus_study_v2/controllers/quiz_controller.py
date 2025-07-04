#!/usr/bin/env python3
"""
Quiz Controller for Linux+ Study Game

Handles all quiz logic, question selection, session management,
and game mode implementations.
"""

import time
import random
import hashlib
from datetime import datetime
from typing import Optional, Dict, Any, Union, List, Tuple
from utils.config import *

class QuizController:
    """Handles quiz logic and session management."""

    points_per_question: int
    streak_bonus: int
    max_streak_bonus: int
    debug_mode: bool
    current_streak_bonus: int  # Only if used elsewhere
    session_answers: List[Tuple[Tuple[str, List[str], int, str, str], int, bool]]  # Add this type annotation

    def __init__(self, game_state: Any):
        """
        Initialize the quiz controller.
        
        Args:
            game_state: GameState instance for data access
        """
        self.game_state = game_state
        self.current_quiz_mode = QUIZ_MODE_STANDARD
        self.quiz_active = False
        self.current_streak = 0
        self.questions_since_break = 0
        
        # Initialize question cache
        self._current_question_cache = None
        
        # Quick Fire mode attributes
        self.quick_fire_active = False
        self.quick_fire_start_time = None
        self.quick_fire_questions_answered = 0
        
        # Session management
        self.session_score = 0
        self.session_total = 0
        self.session_answers = []  # For verify mode
        
        # Daily challenge
        self.daily_challenge_completed = False
        self.last_daily_challenge_date = None

        # Last session results
        self.last_session_results: Optional[Dict[str, Any]] = None

    def get_current_question(self) -> Optional[Dict[str, Any]]:
        """Get the current question without advancing."""
        if not self.quiz_active:
            return None
            
        # Return cached current question if available
        if hasattr(self, '_current_question_cache'):
            return self._current_question_cache
        
        return None

    def cache_current_question(self, question_data: Dict[str, Any]):
        """Cache the current question for repeated access."""
        self._current_question_cache = question_data
    def clear_current_question_cache(self):
        """Clear the cached current question."""
        if hasattr(self, '_current_question_cache'):
            delattr(self, '_current_question_cache')
    def has_cached_question(self):
        """Check if there's a cached current question."""
        return hasattr(self, '_current_question_cache') and self._current_question_cache is not None
    
    def start_quiz_session(self, mode: str = QUIZ_MODE_STANDARD, category_filter: Optional[str] = None) -> dict[str, Any]:
        """
        Start a new quiz session.
        
        Args:
            mode (str): Quiz mode (standard, verify, quick_fire, etc.)
            category_filter (str): Category to filter questions by
            
        Returns:
            dict: Session initialization data
        """
        self.current_quiz_mode = mode
        self.quiz_active = True
        self.session_score = 0
        self.session_total = 0
        self.session_answers = []
        self.current_streak = 0
        self.questions_since_break = 0
        
        # Reset session-specific counters in game state
        self.game_state.score = 0
        self.game_state.total_questions_session = 0
        self.game_state.answered_indices_session = []
        self.game_state.session_points = 0
        
        # Handle special modes
        if mode == "quick_fire":
            self.start_quick_fire_mode()
            total_questions = QUICK_FIRE_QUESTIONS
        elif mode == "mini_quiz":
            total_questions = min(MINI_QUIZ_QUESTIONS, self._get_available_questions_count(category_filter))
        else:
            total_questions = self._get_available_questions_count(category_filter)
        
        # Store category filter for later use
        self.category_filter = category_filter
        
        # Clear any stale question cache
        self.clear_current_question_cache()
        
        return {
            'mode': mode,
            'category_filter': category_filter,
            'total_questions': total_questions,
            'session_active': True,
            'quick_fire_active': self.quick_fire_active
        }
    
    def get_next_question(self, category_filter: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get the next question for the current session.
        
        Args:
            category_filter (str): Category to filter by
            
        Returns:
            dict: Question data or None if session complete
        """
        if not self.quiz_active:
            return None
        
        # Clear previous cache - check if it exists first
        if hasattr(self, '_current_question_cache'):
            delattr(self, '_current_question_cache')
        
        # Check Quick Fire time limit
        if self.quick_fire_active and not self.check_quick_fire_status():
            return None
        
        # Handle special question selection for daily challenge
        if self.current_quiz_mode == "daily_challenge":
            return self.get_daily_challenge_question()
        
        # Regular question selection
        question_data: tuple
        original_index: int
        question_data, original_index = self.game_state.select_question(category_filter)
        
        if question_data:
            result: Dict[str, Any] = {
                'question_data': question_data,
                'original_index': original_index,
                'question_number': self.session_total + 1,
                'streak': self.current_streak,
                'quick_fire_remaining': self._get_quick_fire_remaining() if self.quick_fire_active else None
            }
            # Cache the current question
            self.cache_current_question(result)
            return result
        
        # No more questions available
        self.quiz_active = False
        return None
    
    def get_session_status(self) -> Dict[str, Any]:
        """Get current session status information."""
        return {
            'quiz_active': self.quiz_active,
            'session_score': self.session_score,
            'session_total': self.session_total,
            'current_streak': self.current_streak,
            'mode': self.current_quiz_mode,
            'questions_since_break': self.questions_since_break
        }

    def force_end_session(self) -> Dict[str, Any]:
        """Force end session and return final results."""
        if not self.quiz_active:
            return {
                'session_score': 0,
                'session_total': 0,
                'accuracy': 0.0,
                'session_points': 0,
                'message': 'No active session to end'
            }
        
        # Calculate final results
        accuracy = (self.session_score / self.session_total * 100) if self.session_total > 0 else 0.0
        session_points = getattr(self.game_state, 'session_points', 0)
        
        # Store results before clearing
        results: Dict[str, Any] = {
            'session_score': self.session_score,
            'session_total': self.session_total,
            'accuracy': accuracy,
            'session_points': session_points,
            'quiz_mode': self.current_quiz_mode
        }
        # Save results for later retrieval
        self.last_session_results = results
        
        # Clear all session state
        self.quiz_active = False
        self.current_quiz_mode = QUIZ_MODE_STANDARD
        self.session_score = 0
        self.session_total = 0
        self.session_answers = []
        self.current_streak = 0
        self.questions_since_break = 0
        
        # Clear quick fire state
        if self.quick_fire_active:
            self.end_quick_fire_mode()
        
        # Clear question cache
        self.clear_current_question_cache()
        
        # Clear category filter
        if hasattr(self, 'category_filter'):
            delattr(self, 'category_filter')
        
        return results
    
    def validate_session_state(self) -> Dict[str, Any]:
        """Validate current session state and return status."""
        if not self.quiz_active:
            return {'valid': False, 'reason': 'No active session'}
        
        if not hasattr(self, 'current_quiz_mode'):
            return {'valid': False, 'reason': 'Invalid quiz mode'}
        
        return {'valid': True}
    def submit_answer(self, question_data: tuple[str, list[str], int, str, str], user_answer_index: int, original_index: int) -> dict[str, Any]:
        """
        Process a submitted answer.
        
        Args:
            question_data (tuple): Question data tuple
            user_answer_index (int): User's selected answer index
            original_index (int): Original question index in the question pool
            
        Returns:
            dict: Answer processing results
        """
        if not self.quiz_active or len(question_data) < 5:
            return {'error': 'Invalid quiz state or question data'}
        
        q_text, options, correct_answer_index, category, explanation = question_data
        is_correct = (user_answer_index == correct_answer_index)
        
        # Update streak
        if is_correct:
            self.current_streak += 1
            self.session_score += 1
        else:
            self.current_streak = 0
        
        self.session_total += 1
        self.questions_since_break += 1
        
        # Calculate points
        points_earned = self._calculate_points(is_correct, self.current_streak)
        
        # Update game state
        self.game_state.total_questions_session += 1
        if is_correct:
            self.game_state.score += 1
        
        self.game_state.update_points(points_earned)
        
        # Update history
        if 0 <= original_index < len(self.game_state.questions):
            original_question_text = self.game_state.questions[original_index][0]
            self.game_state.update_history(original_question_text, category, is_correct)
        
        # Check achievements
        new_badges = self.game_state.check_achievements(is_correct, self.current_streak)
        
        # Handle mode-specific logic
        result: Dict[str, Any] = {
            'is_correct': is_correct,
            'correct_answer_index': correct_answer_index,
            'user_answer_index': user_answer_index,
            'explanation': explanation,
            'points_earned': points_earned,
            'streak': self.current_streak,
            'new_badges': new_badges,
            'session_score': self.session_score,
            'session_total': self.session_total,
            'options': options
        }
        
        # Store answer for verify mode
        if self.current_quiz_mode == QUIZ_MODE_VERIFY:
            self.session_answers.append((question_data, user_answer_index, is_correct))
        
        # Update Quick Fire if active
        if self.quick_fire_active:
            self.quick_fire_questions_answered += 1
            result['quick_fire_questions_answered'] = self.quick_fire_questions_answered
            result['quick_fire_complete'] = self.quick_fire_questions_answered >= QUICK_FIRE_QUESTIONS
        
        # Check for session completion
        result['session_complete'] = self._check_session_complete()
        
        return result
    
    def skip_question(self) -> Dict[str, Any]:
        """
        Handle question skipping.
        
        Returns:
            dict: Skip processing results
        """
        self.questions_since_break += 1
        
        # For Quick Fire, count skip as an attempted slot
        if self.quick_fire_active:
            self.quick_fire_questions_answered += 1
        
        return {
            'skipped': True,
            'quick_fire_questions_answered': self.quick_fire_questions_answered if self.quick_fire_active else None,
            'session_complete': self._check_session_complete()
        }
    
    def end_session(self) -> Dict[str, Any]:
        """
        End the current quiz session.
        
        Returns:
            dict: Session summary data
        """
        if not self.quiz_active:
            return {'error': 'No active session'}
        
        self.quiz_active = False
        
        # Calculate final statistics
        accuracy = (self.session_score / self.session_total * 100) if self.session_total > 0 else 0
        
        # Update leaderboard using StatsController to avoid property issues
        if self.session_total > 0:
            try:
                from controllers.stats_controller import StatsController
                stats_controller = StatsController(self.game_state)
                stats_controller.update_leaderboard_entry(
                    self.session_score, 
                    self.session_total, 
                    self.game_state.session_points
                )
            except Exception as e:
                print(f"Warning: Could not update leaderboard: {e}")
        
        # Check for perfect session achievement
        if accuracy == 100 and self.session_total >= 3:
            if "perfect_session" not in self.game_state.achievements["badges"]:
                self.game_state.achievements["badges"].append("perfect_session")
        
        # End Quick Fire if active
        if self.quick_fire_active:
            self.quick_fire_active = False
        
        # Save progress
        self.game_state.save_history()
        self.game_state.save_achievements()
        
        session_results = {
            'session_score': self.session_score,
            'session_total': self.session_total,
            'accuracy': accuracy,
            'session_points': self.game_state.session_points,
            'total_points': self.game_state.achievements.get('points_earned', 0),
            'mode': self.current_quiz_mode,
            'verify_answers': self.session_answers if self.current_quiz_mode == QUIZ_MODE_VERIFY else None
        }
        self.last_session_results = session_results
        return session_results
    
    def start_quick_fire_mode(self) -> Dict[str, Any]:
        """Initialize Quick Fire mode."""
        self.quick_fire_active = True
        self.quick_fire_start_time = time.time()
        self.quick_fire_questions_answered = 0
        
        return {
            'quick_fire_active': True,
            'start_time': self.quick_fire_start_time,
            'time_limit': QUICK_FIRE_TIME_LIMIT,
            'question_limit': QUICK_FIRE_QUESTIONS
        }
    
    def check_quick_fire_status(self) -> Dict[str, Any]:
        """
        Check if Quick Fire mode should continue.
        
        Returns:
            dict: Quick Fire status information
        """
        if not self.quick_fire_active:
            return {'active': False}
        
        elapsed_time = time.time() - self.quick_fire_start_time
        time_remaining = max(0, QUICK_FIRE_TIME_LIMIT - elapsed_time)
        questions_remaining = max(0, QUICK_FIRE_QUESTIONS - self.quick_fire_questions_answered)
        
        # Check end conditions
        time_up = elapsed_time > QUICK_FIRE_TIME_LIMIT
        questions_complete = self.quick_fire_questions_answered >= QUICK_FIRE_QUESTIONS
        
        if time_up or questions_complete:
            result = self.end_quick_fire_mode(time_up=time_up)
            result['should_continue'] = False
            return result
        
        return {
            'active': True,
            'should_continue': True,
            'elapsed_time': elapsed_time,
            'time_remaining': time_remaining,
            'questions_answered': self.quick_fire_questions_answered,
            'questions_remaining': questions_remaining
        }
    
    def end_quick_fire_mode(self, time_up=False) -> dict[str, Any]:
        """
        End Quick Fire mode and return results.
        
        Args:
            time_up (bool): Whether time ran out
            
        Returns:
            dict: Quick Fire completion data
        """
        if not self.quick_fire_active:
            return {'error': 'Quick Fire not active'}
        
        self.quick_fire_active = False
        elapsed_time = time.time() - self.quick_fire_start_time
        
        # Award achievement if completed successfully
        achievement_earned = False
        if not time_up and self.quick_fire_questions_answered >= QUICK_FIRE_QUESTIONS:
            if "quick_fire_champion" not in self.game_state.achievements["badges"]:
                self.game_state.achievements["badges"].append("quick_fire_champion")
                achievement_earned = True
        
        return {
            'completed': not time_up,
            'time_up': time_up,
            'questions_answered': self.quick_fire_questions_answered,
            'target_questions': QUICK_FIRE_QUESTIONS,
            'elapsed_time': elapsed_time,
            'time_limit': QUICK_FIRE_TIME_LIMIT,
            'achievement_earned': achievement_earned
        }
    
    def get_daily_challenge_question(self) -> Optional[Dict[str, Any]]:
        """
        Get today's daily challenge question.
        
        Returns:
            dict: Daily challenge question data or None if unavailable
        """
        today = datetime.now().date().isoformat()
        
        # Check if already completed today
        if (self.last_daily_challenge_date == today and 
            self.daily_challenge_completed):
            return None
        
        # Use date as seed for consistent daily question
        date_hash = int(hashlib.md5(today.encode()).hexdigest()[:8], 16)
        if self.game_state.questions:
            question_index = date_hash % len(self.game_state.questions)
            self.last_daily_challenge_date = today
            
            return {
                'question_data': self.game_state.questions[question_index],
                'original_index': question_index,
                'is_daily_challenge': True,
                'date': today
            }
        
        return None
    
    def complete_daily_challenge(self, is_correct) -> Dict[str, Any]:
        """
        Mark daily challenge as complete and handle rewards.
        
        Args:
            is_correct (bool): Whether the challenge was answered correctly
            
        Returns:
            dict: Daily challenge completion data
        """
        today_iso = datetime.now().date().isoformat()
        self.daily_challenge_completed = True
        self.last_daily_challenge_date = today_iso
        
        achievement_earned = False
        if is_correct:
            # Update daily warrior achievement
            self.game_state.achievements.setdefault("daily_warrior_dates", [])
            
            # Ensure it's a list
            if isinstance(self.game_state.achievements["daily_warrior_dates"], set):
                self.game_state.achievements["daily_warrior_dates"] = list(
                    self.game_state.achievements["daily_warrior_dates"]
                )
            
            if today_iso not in self.game_state.achievements["daily_warrior_dates"]:
                self.game_state.achievements["daily_warrior_dates"].append(today_iso)
            
            # Award badge if criteria met
            if ("daily_warrior" not in self.game_state.achievements["badges"] and 
                len(self.game_state.achievements["daily_warrior_dates"]) >= 1):
                self.game_state.achievements["badges"].append("daily_warrior")
                achievement_earned = True
        
        return {
            'completed': True,
            'correct': is_correct,
            'achievement_earned': achievement_earned,
            'date': today_iso
        }
    
    def check_break_reminder(self, break_interval) -> bool:
        """
        Check if a break reminder should be shown.
        
        Args:
            break_interval (int): Number of questions before break reminder
            
        Returns:
            bool: True if break should be suggested
        """
        return self.questions_since_break >= break_interval
    
    def reset_break_counter(self):
        """Reset the break counter."""
        self.questions_since_break = 0
    
    def get_verify_mode_results(self) -> Dict[str, Any]:
        """
        Get results for verify mode session.
        
        Returns:
            dict: Verify mode results data
        """
        if self.current_quiz_mode != QUIZ_MODE_VERIFY:
            return {'error': 'Not in verify mode'}
        
        if not self.session_answers:
            return {'error': 'No answers recorded'}
        
        num_correct = sum(1 for _, _, is_correct in self.session_answers if is_correct)
        total_answered = len(self.session_answers)
        accuracy = (num_correct / total_answered * 100) if total_answered > 0 else 0
        
        return {
            'total_answered': total_answered,
            'num_correct': num_correct,
            'accuracy': accuracy,
            'detailed_answers': self.session_answers
        }
    
    def get_quiz_results(self) -> Optional[Dict[str, Any]]:
        """Get comprehensive results of the completed quiz session."""
        if not hasattr(self, 'last_session_results') or self.last_session_results is None:
            return None
        
        return self.last_session_results

    def get_session_summary(self) -> Optional[Dict[str, Any]]:
        """Get a summary of the current or last session."""
        try:
            status = self.get_session_status()
            
            return {
                'score': status['session_score'],
                'total': status['session_total'],
                'percentage': (status['session_score'] / status['session_total'] * 100) if status['session_total'] > 0 else 0,
                'streak': status['current_streak'],
                'points_earned': status.get('points_earned', 0),
                'mode': status['mode'],
                'quiz_active': status['quiz_active'],
                'categories_studied': getattr(self, 'categories_in_session', [])
            }
        except Exception as e:
            print(f"Error generating session summary: {e}")
            return None
    
    def _calculate_points(self, is_correct: bool, current_streak: int) -> int:
        """Calculate points earned for an answer."""
        if is_correct:
            points = POINTS_PER_CORRECT
            if current_streak >= STREAK_BONUS_THRESHOLD:
                points = int(points * STREAK_BONUS_MULTIPLIER)
            return points
        else:
            return POINTS_PER_INCORRECT
    
    def _get_available_questions_count(self, category_filter: Optional[str] = None) -> int:
        """Get count of available questions for the filter."""
        if category_filter is None:
            return len(self.game_state.questions)
        else:
            return sum(1 for q in self.game_state.questions 
                      if len(q) > 3 and q[3] == category_filter)
    
    def _get_quick_fire_remaining(self) -> Optional[Dict[str, Union[float, int]]]:
        """Get remaining Quick Fire questions and time."""
        if not self.quick_fire_active:
            return None
        
        elapsed = time.time() - self.quick_fire_start_time
        time_remaining = max(0, QUICK_FIRE_TIME_LIMIT - elapsed)
        questions_remaining = max(0, QUICK_FIRE_QUESTIONS - self.quick_fire_questions_answered)
        
        return {
            'time_remaining': time_remaining,
            'questions_remaining': questions_remaining
        }
    
    def _check_session_complete(self):
        """Check if the current session should end."""
        # Quick Fire completion
        if (self.quick_fire_active and 
            self.quick_fire_questions_answered >= QUICK_FIRE_QUESTIONS):
            return True
        
        # Mini quiz completion
        if (self.current_quiz_mode == "mini_quiz" and 
            self.session_total >= MINI_QUIZ_QUESTIONS):
            return True
        
        # Single question modes (daily challenge, pop quiz)
        if self.current_quiz_mode in ["daily_challenge", "pop_quiz"]:
            return self.session_total >= 1
        
        return False
    def update_settings(self, settings: Dict[str, Any]) -> None:
        """Update quiz controller with new settings."""
        self.points_per_question: int = settings.get('pointsPerQuestion', 10)
        self.streak_bonus: int = settings.get('streakBonus', 5)
        self.max_streak_bonus: int = settings.get('maxStreakBonus', 50)
        self.debug_mode: bool = settings.get('debugMode', False)
        
        # Update any active scoring calculations
        if hasattr(self, 'current_streak_bonus'):
            self.current_streak_bonus = min(
                int(self.current_streak_bonus), int(self.max_streak_bonus)
            )