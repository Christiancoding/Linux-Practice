#!/usr/bin/env python3
"""
Quiz Controller for Linux+ Study Game

Handles all quiz logic, question selection, session management,
and game mode implementations.
"""

import time
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
    quick_fire_start_time: Optional[float]  # Time when quick fire mode started
    quick_fire_end_time: Optional[float]    # Time when quick fire mode ended
    quick_fire_duration: Optional[float]    # Duration of quick fire mode session
    last_question: Optional[Dict[str, Any]]  # Cache for the last processed question

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
        
        # Last question cache
        self.last_question: Optional[Dict[str, Any]] = None
        
        # Initialize scoring settings with defaults
        self.points_per_question: int = 10
        self.points_per_incorrect: int = 0
        self.streak_bonus: int = 5
        self.max_streak_bonus: int = 50
        self.debug_mode: bool = False

    def get_current_question(self) -> Optional[Dict[str, Any]]:
        """Get the current question without advancing."""
        if not self.quiz_active:
            return None
            
        # Return cached current question if available
        if hasattr(self, '_current_question_cache'):
            return self._current_question_cache
        
        return None

    def cache_current_question(self, question_data: Dict[str, Any]) -> None:
        """Cache the current question for repeated access."""
        self._current_question_cache = question_data
    def clear_current_question_cache(self) -> None:
        """Clear the cached current question."""
        if hasattr(self, '_current_question_cache'):
            delattr(self, '_current_question_cache')
            
    def has_cached_question(self) -> bool:
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
        print(f"DEBUG: Starting quiz session with mode: '{mode}'")
        self.current_quiz_mode = mode
        self.quiz_active = True
        self.session_score = 0
        self.session_total = 0
        self.session_answers = []
        self.current_streak = 0
        self.questions_since_break = 0
        
        # Reset session-specific counters in game state
        self.game_state.reset_session()
        
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
        
        print(f"DEBUG: Quiz mode set to: '{self.current_quiz_mode}'")
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
        question_result = self.game_state.select_question(category_filter)
        question_data, original_index = question_result
        
        if question_data is not None:
            quick_fire_remaining = self._get_quick_fire_remaining() if self.quick_fire_active else None
            
            # Determine total questions for progress display
            total_questions = None
            if self.current_quiz_mode == "mini_quiz":
                total_questions = MINI_QUIZ_QUESTIONS
            elif self.current_quiz_mode == "quick_fire":
                total_questions = QUICK_FIRE_QUESTIONS
            elif self.current_quiz_mode in ["daily_challenge", "pop_quiz"]:
                total_questions = 1
            else:
                # For standard quiz and category quizzes, show total available questions
                total_questions = self._get_available_questions_count(self.category_filter)
            
            result: Dict[str, Any] = {
                'question_data': question_data,
                'original_index': original_index,
                'question_number': self.session_total + 1,
                'total_questions': total_questions,
                'streak': self.current_streak,
                'quick_fire_remaining': quick_fire_remaining
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
        
        _, options, correct_answer_index, category, explanation = question_data
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
        
        # If session is complete, automatically end the session
        if result['session_complete']:
            self.quiz_active = False
            # Save session results
            accuracy = (self.session_score / self.session_total * 100) if self.session_total > 0 else 0.0
            self.last_session_results = {
                'session_score': self.session_score,
                'session_total': self.session_total,
                'accuracy': accuracy,
                'session_points': getattr(self.game_state, 'session_points', 0),
                'mode': self.current_quiz_mode
            }
            # Add final results to the response
            result.update(self.last_session_results)
                
        # Ensure results are saved if session is complete
        if not self.quiz_active and self.session_total > 0 and not result['session_complete']:
            self.last_session_results = {
                'session_score': self.session_score,
                'session_total': self.session_total,
                'accuracy': (self.session_score / self.session_total * 100) if self.session_total > 0 else 0.0,
                'session_points': getattr(self.game_state, 'session_points', 0),
                'mode': self.current_quiz_mode
            }
        # Cache the current question
        self.last_question = {
            'question_data': question_data,
            'user_answer_index': user_answer_index,
            'is_correct': is_correct
        }
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
        
        session_results: Dict[str, Any] = {
            'session_score': self.session_score,
            'session_total': self.session_total,
            'accuracy': accuracy,
            'session_points': self.game_state.session_points,
            'total_points': self.game_state.achievements.get('points_earned', 0),
            'mode': self.current_quiz_mode,
            'verify_answers': self.session_answers if self.current_quiz_mode == QUIZ_MODE_VERIFY else None
        }
        
        # Save results for API retrieval
        self.last_session_results = session_results
        
        # Reset session variables
        self.session_score = 0
        self.session_total = 0
        self.session_answers = []
        self.current_streak = 0
        self.questions_since_break = 0
        self.current_quiz_mode = QUIZ_MODE_STANDARD
        
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
    def _end_quick_fire_mode_internal(self, time_up: bool) -> None:
        """
        End Quick Fire mode and save results (internal implementation).
        
        Args:
            time_up (bool): Whether time ran out
        """
        self.quick_fire_active = False
        self.quick_fire_end_time = time.time()
        
        # Check if quick_fire_start_time is not None before subtraction
        if self.quick_fire_start_time is not None:
            self.quick_fire_duration = self.quick_fire_end_time - self.quick_fire_start_time
        else:
            self.quick_fire_duration = 0.0  # Default value if start time was not set

        # Save Quick Fire results
        self.game_state.quick_fire_results.append({
            'questions_answered': self.quick_fire_questions_answered,
            'time_up': time_up,
            'duration': self.quick_fire_duration
        })

    def update_history(self, is_correct: bool) -> None:
        """
        Update the study history with the latest question result.
        
        Args:
            is_correct (bool): Whether the last question was answered correctly
        """
        self.game_state.study_history.append({
            'timestamp': time.time(),
            'correct': is_correct
        })

    def take_break(self, break_interval: int) -> None:
        """
        Take a break during the quiz session.
        
        Args:
            break_interval (int): Duration of the break in seconds
        """
        self.break_start_time = time.time()
        self.break_duration = break_interval

    def check_quick_fire_status(self) -> Dict[str, Any]:
        """
        Check if Quick Fire mode should continue.
        
        Returns:
            dict: Quick Fire status information
        """
        if not self.quick_fire_active:
            return {'active': False}
        
        # Add null check before performing arithmetic
        if self.quick_fire_start_time is not None:
            elapsed_time = time.time() - self.quick_fire_start_time
            time_remaining = max(0, QUICK_FIRE_TIME_LIMIT - elapsed_time)
            # Check end conditions
            time_up = elapsed_time > QUICK_FIRE_TIME_LIMIT
        else:
            # Handle case where start time wasn't properly set
            elapsed_time = 0.0
            time_remaining = 0.0
            time_up = False
            
        questions_remaining = max(0, QUICK_FIRE_QUESTIONS - self.quick_fire_questions_answered)
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
    
    def end_quick_fire_mode(self, time_up: bool = False) -> dict[str, Any]:
        """
        End Quick Fire mode and return results.
        
        Args:
            time_up (bool): Whether time ran out
            
        Returns:
            dict: Quick Fire completion data
        """
        if not self.quick_fire_active:
            return {'error': 'Quick Fire not active'}
        
        # First save results like the internal implementation did
        self.quick_fire_end_time = time.time()
        
        # Check if quick_fire_start_time is not None before subtraction
        if self.quick_fire_start_time is not None:
            self.quick_fire_duration = self.quick_fire_end_time - self.quick_fire_start_time
        else:
            self.quick_fire_duration = 0.0  # Default value if start time was not set

        # Save Quick Fire results
        self.game_state.quick_fire_results.append({
            'questions_answered': self.quick_fire_questions_answered,
            'time_up': time_up,
            'duration': self.quick_fire_duration
        })
        
        self.quick_fire_active = False
        
        # Check if quick_fire_start_time is not None before subtraction
        if self.quick_fire_start_time is not None:
            elapsed_time = time.time() - self.quick_fire_start_time
        else:
            elapsed_time = 0.0  # Default value if start time was not set
        
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
            
            question_data = self.game_state.questions[question_index]
            
            result: Dict[str, Any] = {
                'question_data': question_data,
                'original_index': question_index,
                'question_number': 1,
                'total_questions': 1,
                'streak': self.current_streak,
                'is_daily_challenge': True,
                'date': today
            }
            # Cache the current question
            self.cache_current_question(result)
            return result
        
        return None
    
    def complete_daily_challenge(self, is_correct: bool) -> Dict[str, Any]:
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
    
    def check_break_reminder(self, break_interval: int) -> bool:
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
            # Use quiz controller settings if available, otherwise fall back to constants
            base_points = getattr(self, 'points_per_question', POINTS_PER_CORRECT)
            streak_threshold = getattr(self, 'streak_bonus', STREAK_BONUS_THRESHOLD)
            streak_multiplier = getattr(self, 'max_streak_bonus', STREAK_BONUS_MULTIPLIER)
            
            points = base_points
            if current_streak >= streak_threshold:
                # Apply streak bonus (but cap it to reasonable limits)
                bonus_multiplier = min(2.0, 1.0 + (streak_multiplier / 100.0))
                points = int(points * bonus_multiplier)
            return points
        else:
            # For incorrect answers, use negative points or 0 based on settings
            return getattr(self, 'points_per_incorrect', POINTS_PER_INCORRECT)
    
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
        
        if self.quick_fire_start_time is not None:
            elapsed = time.time() - self.quick_fire_start_time
            time_remaining = max(0, QUICK_FIRE_TIME_LIMIT - elapsed)
        else:
            elapsed = 0.0
            time_remaining = 0.0
            
        questions_remaining = max(0, QUICK_FIRE_QUESTIONS - self.quick_fire_questions_answered)
        
        return {
            'time_remaining': time_remaining,
            'questions_remaining': questions_remaining
        }
    
    def _check_session_complete(self):
        """Check if the current session should end."""
        print(f"DEBUG: Checking session complete - mode: '{self.current_quiz_mode}', total: {self.session_total}")
        
        # Quick Fire completion
        if (self.quick_fire_active and 
            self.quick_fire_questions_answered >= QUICK_FIRE_QUESTIONS):
            print(f"DEBUG: Quick fire complete")
            return True
        
        # Mini quiz completion
        if (self.current_quiz_mode == "mini_quiz" and 
            self.session_total >= MINI_QUIZ_QUESTIONS):
            print(f"DEBUG: Mini quiz complete")
            return True
        
        # Single question modes (daily challenge, pop quiz)
        if self.current_quiz_mode in ["daily_challenge", "pop_quiz"]:
            complete = self.session_total >= 1
            print(f"DEBUG: Single question mode - complete: {complete}")
            return complete
        
        # For standard and verify quizzes, check if there are more questions available
        if self.current_quiz_mode in ["standard", "verify"]:
            # Try to see if we can get another question without actually selecting it
            try:
                # Check available questions count without modifying session state
                available_count = self._get_available_questions_count(self.category_filter)
                answered_count = len(self.game_state.question_manager.answered_indices_session)
                questions_remaining = available_count - answered_count
                
                print(f"DEBUG: Standard/verify quiz - available: {available_count}, answered: {answered_count}, remaining: {questions_remaining}")
                
                if questions_remaining <= 0:
                    print(f"DEBUG: No more questions available - completing session")
                    return True
            except Exception as e:
                print(f"DEBUG: Error checking remaining questions: {e}")
                # If we can't determine, assume quiz continues
                pass
        
        # Standard and verify quizzes continue until manually ended or no questions available
        print(f"DEBUG: Session not complete - continuing")
        return False
    def update_settings(self, settings: Dict[str, Any]) -> None:
        """Update quiz controller with new settings."""
        self.points_per_question = settings.get('pointsPerQuestion', 10)
        self.points_per_incorrect = settings.get('pointsPerIncorrect', 0)
        self.streak_bonus = settings.get('streakBonus', 5)
        self.max_streak_bonus = settings.get('maxStreakBonus', 50)
        self.debug_mode = settings.get('debugMode', False)
        
        if self.debug_mode:
            print(f"DEBUG: Updated quiz controller settings - points per question: {self.points_per_question}, streak bonus: {self.streak_bonus}")
        
        # Update any active scoring calculations
        if hasattr(self, 'current_streak_bonus'):
            self.current_streak_bonus = min(
                int(self.current_streak_bonus), int(self.max_streak_bonus)
            )