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
from utils.game_values import get_game_value_manager
from services.simple_analytics import get_analytics_manager
from services.time_tracking_service import get_time_tracker

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
        
        # Custom question limit for web interface
        self.custom_question_limit: Optional[int] = None
        
        # Initialize scoring settings from game values
        game_values = get_game_value_manager()
        self.points_per_question: int = game_values.get_value('scoring', 'points_per_correct', 10)
        self.points_per_incorrect: int = game_values.get_value('scoring', 'points_per_incorrect', 0)
        self.streak_bonus: int = game_values.get_value('scoring', 'streak_bonus', 5)
        self.max_streak_bonus: int = game_values.get_value('scoring', 'max_streak_bonus', 50)
        self.hint_penalty: int = game_values.get_value('scoring', 'hint_penalty', 5)
        self.speed_bonus: int = game_values.get_value('scoring', 'speed_bonus', 5)
        self.debug_mode: bool = False
        
        # Timed mode attributes
        self.timed_mode_active = False
        self.timed_mode_start_time: Optional[float] = None
        self.time_per_question = TIMED_CHALLENGE_TIME_PER_QUESTION
        self.current_question_start_time: Optional[float] = None
        
        # Survival mode attributes
        self.survival_mode_active = False
        self.survival_lives = SURVIVAL_MODE_LIVES
        self.survival_high_score = 0
        
        # Exam mode attributes
        self.exam_mode_active = False
        self.exam_start_time: Optional[float] = None
        
        # Session timing
        self.session_start_time: Optional[float] = None

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
            mode (str): Quiz mode (standard, verify, quick_fire, timed, survival, category, exam)
            category_filter (str): Category to filter questions by
            
        Returns:
            dict: Session initialization data
        """
        print(f"DEBUG: Starting quiz session with mode: '{mode}'")
        if self.custom_question_limit:
            print(f"DEBUG: Custom question limit set to: {self.custom_question_limit}")
        self.current_quiz_mode = mode
        self.quiz_active = True
        self.session_score = 0
        self.session_total = 0
        self.session_answers = []
        self.current_streak = 0
        self.questions_since_break = 0
        
        # Track session start time for real duration measurement
        self.session_start_time = time.time()
        
        # Reset session-specific counters in game state
        self.game_state.reset_session()
        
        # Reset mode-specific flags
        self.quick_fire_active = False
        self.timed_mode_active = False
        self.survival_mode_active = False
        self.exam_mode_active = False
        
        # Handle special modes
        if mode == "quick_fire":
            self.start_quick_fire_mode()
            total_questions = QUICK_FIRE_QUESTIONS
        elif mode == "mini_quiz":
            total_questions = min(MINI_QUIZ_QUESTIONS, self._get_available_questions_count(category_filter))
        elif mode == QUIZ_MODE_TIMED:
            self.start_timed_mode()
            total_questions = self.custom_question_limit if self.custom_question_limit else TIMED_CHALLENGE_QUESTIONS
        elif mode == QUIZ_MODE_SURVIVAL:
            self.start_survival_mode()
            total_questions = float('inf')  # Unlimited questions until death
        elif mode == QUIZ_MODE_EXAM:
            self.start_exam_mode()
            total_questions = EXAM_MODE_QUESTIONS
        elif mode == QUIZ_MODE_CATEGORY_FOCUS:
            # Category focus mode - use all questions from selected category
            total_questions = self._get_available_questions_count(category_filter)
        else:
            # Standard mode - check for custom question limit first
            if self.custom_question_limit:
                total_questions = self.custom_question_limit
            else:
                total_questions = self._get_available_questions_count(category_filter)
        
        # Store category filter for later use
        self.category_filter = category_filter
        
        # Clear any stale question cache
        self.clear_current_question_cache()
        
        print(f"DEBUG: Quiz mode set to: '{self.current_quiz_mode}'")
        
        # Handle infinite total_questions for JSON serialization
        json_total_questions = None if total_questions == float('inf') else total_questions
        
        return {
            'mode': mode,
            'category_filter': category_filter,
            'total_questions': json_total_questions,
            'session_active': True,
            'quick_fire_active': self.quick_fire_active,
            'timed_mode_active': self.timed_mode_active,
            'survival_mode_active': self.survival_mode_active,
            'exam_mode_active': self.exam_mode_active,
            'survival_lives': getattr(self, 'survival_lives', SURVIVAL_MODE_LIVES) if mode == QUIZ_MODE_SURVIVAL else None,
            'time_per_question': self.time_per_question if mode == QUIZ_MODE_TIMED else None,
            'unlimited_questions': total_questions == float('inf')
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
            print(f"DEBUG: Normal question_data type: {type(question_data)}")
            print(f"DEBUG: Normal question_data: {question_data}")
            quick_fire_remaining = self._get_quick_fire_remaining() if self.quick_fire_active else None
            
            # Start timer for timed mode questions
            if self.timed_mode_active:
                self.current_question_start_time = time.time()
            
            # Determine total questions for progress display
            total_questions = None
            if self.current_quiz_mode == "mini_quiz":
                total_questions = MINI_QUIZ_QUESTIONS
            elif self.current_quiz_mode == "quick_fire":
                total_questions = QUICK_FIRE_QUESTIONS
            elif self.current_quiz_mode == QUIZ_MODE_TIMED:
                total_questions = self.custom_question_limit if self.custom_question_limit else TIMED_CHALLENGE_QUESTIONS
            elif self.current_quiz_mode == QUIZ_MODE_EXAM:
                total_questions = EXAM_MODE_QUESTIONS
            elif self.current_quiz_mode == QUIZ_MODE_SURVIVAL:
                total_questions = None  # Unlimited until death
            elif self.current_quiz_mode in ["daily_challenge", "pop_quiz"]:
                total_questions = 1
            else:
                # For standard quiz and category quizzes, use custom limit if set, otherwise show total available
                if self.custom_question_limit:
                    total_questions = self.custom_question_limit
                else:
                    total_questions = self._get_available_questions_count(self.category_filter)
            
            result: Dict[str, Any] = {
                'question_data': question_data,
                'original_index': original_index,
                'question_number': self.session_total + 1,
                'total_questions': total_questions,
                'streak': self.current_streak,
                'quick_fire_remaining': quick_fire_remaining,
                'timed_mode_active': self.timed_mode_active,
                'time_per_question': self.time_per_question if self.timed_mode_active else None,
                'survival_mode_active': self.survival_mode_active,
                'survival_lives': getattr(self, 'survival_lives', SURVIVAL_MODE_LIVES) if self.survival_mode_active else None,
                'exam_mode_active': self.exam_mode_active
            }
            # Cache the current question
            self.cache_current_question(result)
            return result
        
        # No more questions available
        # For survival mode, reset the answered list and try again
        if self.current_quiz_mode == QUIZ_MODE_SURVIVAL and self.survival_lives > 0:
            print("DEBUG: Survival mode - resetting answered questions to allow repetition")
            self.game_state.question_manager.reset_session()
            
            # Try to get a question again after reset
            question_result = self.game_state.select_question(category_filter)
            question_data, original_index = question_result
            
            if question_data is not None:
                print("DEBUG: Survival mode - got question after reset")
                print(f"DEBUG: Recycled question_data type: {type(question_data)}")
                print(f"DEBUG: Recycled question_data: {question_data}")
                # Use the same logic as the main path to ensure consistent data structure
                quick_fire_remaining = self._get_quick_fire_remaining() if self.quick_fire_active else None
                
                # Start timer for timed mode questions
                if self.timed_mode_active:
                    self.current_question_start_time = time.time()
                
                result: Dict[str, Any] = {
                    'question_data': question_data,
                    'original_index': original_index,
                    'question_number': self.session_total + 1,
                    'total_questions': None,  # Unlimited for survival
                    'streak': self.current_streak,
                    'quick_fire_remaining': quick_fire_remaining,
                    'timed_mode_active': self.timed_mode_active,
                    'time_per_question': self.time_per_question if self.timed_mode_active else None,
                    'survival_mode_active': self.survival_mode_active,
                    'survival_lives': getattr(self, 'survival_lives', SURVIVAL_MODE_LIVES) if self.survival_mode_active else None,
                    'exam_mode_active': self.exam_mode_active
                }
                # Cache the current question
                self.cache_current_question(result)
                return result
        
        # No more questions available and not survival mode (or survival with no lives)
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
        
        # Save progress before clearing session state
        if self.session_total > 0:  # Only save if there was actual activity
            try:
                # Use the new unified save method
                success = self.game_state.save_all_data()
                if not success:
                    print("Warning: Some data may not have been saved properly")
            except Exception as e:
                print(f"Warning: Failed to save progress during force end: {e}")
        
        # Calculate session duration if we have start time
        session_duration = 0
        if self.session_start_time:
            session_duration = time.time() - self.session_start_time
        
        # Track quiz time in the time tracking service
        try:
            time_tracker = get_time_tracker()
            time_tracker.add_quiz_time(session_duration)
        except Exception as e:
            print(f"Warning: Failed to track quiz time in force end: {e}")
        
        # Store results before clearing
        results: Dict[str, Any] = {
            'session_score': self.session_score,
            'session_total': self.session_total,
            'accuracy': accuracy,
            'session_points': session_points,
            'quiz_mode': self.current_quiz_mode,
            'session_duration': session_duration
        }
        
        # Add explicit logging to verify session-specific data
        print(f"DEBUG: End session - storing SESSION-SPECIFIC results:")
        print(f"  session_score: {self.session_score}")
        print(f"  session_total: {self.session_total}")
        print(f"  accuracy: {accuracy:.1f}%")
        print(f"  session_points: {session_points}")
        print(f"  quiz_mode: {self.current_quiz_mode}")
        
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
    def submit_answer(self, question_data: tuple[str, list[str], int, str, str], user_answer_index: Optional[int], original_index: int) -> dict[str, Any]:
        """
        Process a submitted answer.
        
        Args:
            question_data (tuple): Question data tuple
            user_answer_index (int, optional): User's selected answer index (None for timeout)
            original_index (int): Original question index in the question pool
            
        Returns:
            dict: Answer processing results
        """
        if not self.quiz_active or len(question_data) < 5:
            return {'error': 'Invalid quiz state or question data'}
        
        _, options, correct_answer_index, category, explanation = question_data
        
        # Handle timeout case (no answer selected)
        if user_answer_index is None:
            is_correct = False
            user_answer_index = -1  # Use -1 to indicate timeout/no answer
        else:
            is_correct = (user_answer_index == correct_answer_index)
        
        # Update streak and handle survival mode
        if is_correct:
            self.current_streak += 1
            self.session_score += 1
            print(f"DEBUG: Correct answer - session_score: {self.session_score}, session_total: {self.session_total + 1}")
        else:
            self.current_streak = 0
            print(f"DEBUG: Incorrect answer - session_score: {self.session_score}, session_total: {self.session_total + 1}")
            # Handle survival mode - lose a life on wrong answer
            if self.survival_mode_active:
                self.survival_lives -= 1
                print(f"DEBUG: Survival mode - lives remaining: {self.survival_lives}")
                if self.survival_lives <= 0:
                    # Game over in survival mode - but don't set quiz_active = False yet
                    # We'll handle the session end properly later in this method
                    print(f"DEBUG: Survival mode GAME OVER - lives exhausted")
        
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
        
        # Build the response - REPLACE THE OLD response DICTIONARY WITH THIS
        response: Dict[str, Union[bool, int, float, str, List[str], List[Dict[str, Any]], None]] = {
            'is_correct': is_correct,
            'correct_answer_index': correct_answer_index,
            'points_earned': points_earned,  # Note: changed from 'points' to 'points_earned'
            'session_score': self.session_score,
            'session_total': self.session_total,
            'session_points': self.game_state.session_points,  # Add this line
            'streak': self.current_streak,
            'session_complete': self._check_session_complete(),
            'accuracy': (self.session_score / self.session_total * 100) if self.session_total > 0 else 0,
            'user_answer_index': user_answer_index,
            'explanation': explanation,
            'new_badges': new_badges,
            'options': options,
            'mode': self.current_quiz_mode
        }
        
        # Add survival mode specific data
        if self.survival_mode_active:
            response['survival_lives'] = self.survival_lives
            response['survival_game_over'] = self.survival_lives <= 0
            if self.survival_lives <= 0:
                response['survival_final_score'] = self.session_score
                response['survival_high_score'] = getattr(self, 'survival_high_score', 0)
                print(f"DEBUG: Adding survival game over data to response")
        
        # Add mode-specific information (keep the existing timed mode logic)
        if self.timed_mode_active and self.current_question_start_time:
            # Calculate time taken for this question
            time_taken = time.time() - self.current_question_start_time
            response['time_taken'] = time_taken
            response['time_per_question'] = self.time_per_question
            # Award bonus points for fast answers in timed mode
            if time_taken < self.time_per_question / 2 and is_correct:
                bonus_points = 5
                response['points_earned'] += bonus_points
                response['speed_bonus'] = bonus_points
                # Update game state with the bonus points too
                self.game_state.update_points(bonus_points)
        
        # Store answer for verify mode
        if self.current_quiz_mode == QUIZ_MODE_VERIFY:
            self.session_answers.append((question_data, user_answer_index, is_correct))
        
        # Update Quick Fire if active
        if self.quick_fire_active:
            self.quick_fire_questions_answered += 1
            response['quick_fire_questions_answered'] = self.quick_fire_questions_answered
            response['quick_fire_complete'] = self.quick_fire_questions_answered >= QUICK_FIRE_QUESTIONS
        
        # Check for session completion
        response['session_complete'] = self._check_session_complete()
        
        # If session is complete, automatically end the session
        if response['session_complete']:
            # Call the proper end_session method to ensure data is saved
            session_results: Dict[str, Any] = self.end_session()
            self.last_session_results = session_results
            # Add final results to the response
            response.update(session_results)
                
        # Ensure results are saved if session is complete
        if not self.quiz_active and self.session_total > 0 and not response['session_complete']:
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
        
        return response
    
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
        # Allow ending session for survival mode game over even if quiz_active is False
        if not self.quiz_active and not (self.survival_mode_active and self.survival_lives <= 0):
            return {'error': 'No active session'}
        
        self.quiz_active = False
        
        # Calculate final statistics
        accuracy = (self.session_score / self.session_total * 100) if self.session_total > 0 else 0
        
        # Calculate actual session duration
        session_duration = 0
        if self.session_start_time:
            session_duration = time.time() - self.session_start_time
        
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
        
        # Track quiz time in the time tracking service
        try:
            time_tracker = get_time_tracker()
            time_tracker.add_quiz_time(session_duration)
        except Exception as e:
            print(f"Warning: Failed to track quiz time: {e}")
        
        # Sync total points to analytics to ensure consistency  
        try:
            from services.simple_analytics import get_analytics_manager
            analytics = get_analytics_manager()
            total_earned_points = self.game_state.achievements.get('points_earned', 0)
            if total_earned_points > 0:
                # Update analytics with actual earned points to maintain consistency
                user_data = analytics.get_user_data('anonymous')
                user_data['xp'] = total_earned_points
                analytics._update_user_data('anonymous', user_data)
        except Exception as e:
            print(f"Warning: Failed to sync points to analytics: {e}")
        
        # Save progress using unified save method
        try:
            success = self.game_state.save_all_data()
            if not success:
                print("Warning: Some data may not have been saved properly")
        except Exception as e:
            print(f"Warning: Failed to save progress during session end: {e}")
        
        session_results: Dict[str, Any] = {
            'session_score': self.session_score,
            'session_total': self.session_total,
            'accuracy': accuracy,
            'session_points': self.game_state.session_points,
            'total_points': self.game_state.achievements.get('points_earned', 0),
            'mode': self.current_quiz_mode,
            'session_duration': session_duration,  # Actual time spent in seconds
            'verify_answers': self.session_answers if self.current_quiz_mode == QUIZ_MODE_VERIFY else None
        }
        
        # Save results for API retrieval
        self.last_session_results = session_results
        
        # Reset session variables
        self.quiz_active = False
        self.session_score = 0
        self.session_total = 0
        self.session_answers = []
        self.current_streak = 0
        self.questions_since_break = 0
        self.current_quiz_mode = QUIZ_MODE_STANDARD
        self.custom_question_limit = None  # Reset custom limit
        self.session_start_time = None  # Reset session timing
        
        # Reset mode-specific flags
        self.survival_mode_active = False
        self.survival_lives = SURVIVAL_MODE_LIVES
        self.timed_mode_active = False
        self.exam_mode_active = False
        
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

    def start_timed_mode(self) -> Dict[str, Any]:
        """Initialize Timed Challenge mode."""
        self.timed_mode_active = True
        self.timed_mode_start_time = time.time()
        self.time_per_question = TIMED_CHALLENGE_TIME_PER_QUESTION
        
        return {
            'timed_mode_active': True,
            'start_time': self.timed_mode_start_time,
            'time_per_question': self.time_per_question,
            'total_questions': TIMED_CHALLENGE_QUESTIONS
        }

    def start_survival_mode(self) -> Dict[str, Any]:
        """Initialize Survival mode."""
        self.survival_mode_active = True
        self.survival_lives = SURVIVAL_MODE_LIVES
        
        return {
            'survival_mode_active': True,
            'lives': self.survival_lives,
            'high_score': getattr(self, 'survival_high_score', 0)
        }

    def start_exam_mode(self) -> Dict[str, Any]:
        """Initialize Exam Simulation mode."""
        self.exam_mode_active = True
        self.exam_start_time = time.time()
        
        return {
            'exam_mode_active': True,
            'start_time': self.exam_start_time,
            'time_limit': EXAM_MODE_TIME_LIMIT,
            'total_questions': EXAM_MODE_QUESTIONS
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
    
    def sync_analytics_after_answer(self, is_correct: bool, user_id: str = "anonymous"):
        """Sync analytics after answering a question"""
        try:
            analytics = get_analytics_manager()
            category_filter = getattr(self, 'category_filter', None)
            analytics.track_question_answer(
                user_id=user_id,
                correct=is_correct,
                category=category_filter or "All Categories"
            )
        except Exception as e:
            print(f"Error syncing analytics: {e}")

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
        
        # Survival mode - game over when lives reach 0
        if self.survival_mode_active and self.survival_lives <= 0:
            print(f"DEBUG: Survival mode game over - no lives remaining")
            return True
        
        # Quick Fire completion
        if (self.quick_fire_active and 
            self.quick_fire_questions_answered >= QUICK_FIRE_QUESTIONS):
            print(f"DEBUG: Quick fire complete")
            return True
        
        # Timed Challenge completion
        if (self.current_quiz_mode == QUIZ_MODE_TIMED and 
            self.session_total >= TIMED_CHALLENGE_QUESTIONS):
            print(f"DEBUG: Timed challenge complete")
            return True
        
        # Exam mode completion
        if (self.current_quiz_mode == QUIZ_MODE_EXAM and 
            self.session_total >= EXAM_MODE_QUESTIONS):
            print(f"DEBUG: Exam simulation complete")
            return True
        
        # Check exam mode time limit
        if (self.exam_mode_active and self.exam_start_time and 
            (time.time() - self.exam_start_time) >= EXAM_MODE_TIME_LIMIT):
            print(f"DEBUG: Exam time limit reached")
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
        
        # For standard, verify, and category focus quizzes, check if there are more questions available
        if self.current_quiz_mode in ["standard", "verify", QUIZ_MODE_CATEGORY_FOCUS]:
            # Check custom question limit first (for web interface)
            if self.custom_question_limit and self.session_total >= self.custom_question_limit:
                print(f"DEBUG: Custom question limit reached ({self.custom_question_limit}) - completing session")
                return True
            
            # Only check for completion after a reasonable number of questions (at least 5)
            # This prevents immediate completion for small question pools
            if self.session_total >= 5:
                try:
                    # Check available questions count without modifying session state
                    available_count = self._get_available_questions_count(self.category_filter)
                    answered_count = len(self.game_state.question_manager.answered_indices_session)
                    questions_remaining = available_count - answered_count
                    
                    print(f"DEBUG: Standard/verify/category quiz - available: {available_count}, answered: {answered_count}, remaining: {questions_remaining}")
                    
                    if questions_remaining <= 0:
                        print(f"DEBUG: No more questions available - completing session")
                        return True
                except Exception as e:
                    print(f"DEBUG: Error checking remaining questions: {e}")
                    # If we can't determine, assume quiz continues
                    pass
            else:
                print(f"DEBUG: Standard mode - only {self.session_total} questions answered, continuing")
                return False
        
        # Survival mode continues until death (lives handled at the top)
        if self.current_quiz_mode == QUIZ_MODE_SURVIVAL:
            print(f"DEBUG: Survival mode continuing - {self.survival_lives} lives remaining")
            return False
        
        # Standard, verify, and category focus quizzes continue until manually ended or no questions available
        print(f"DEBUG: Session not complete - continuing")
        return False
    def update_settings(self, settings: Dict[str, Any]) -> None:
        """Update quiz controller with new settings."""
        # Update legacy settings
        self.points_per_question = settings.get('pointsPerQuestion', 10)
        self.points_per_incorrect = settings.get('pointsPerIncorrect', 0)
        self.streak_bonus = settings.get('streakBonus', 5)
        self.max_streak_bonus = settings.get('maxStreakBonus', 50)
        self.debug_mode = settings.get('debugMode', False)
        
        # Also refresh from game values in case they've been updated
        self.refresh_game_values()
        
        # Update any active scoring calculations
        if hasattr(self, 'current_streak_bonus'):
            self.current_streak_bonus = min(
                int(self.current_streak_bonus), int(self.max_streak_bonus)
            )
    
    def refresh_game_values(self) -> None:
        """Refresh settings from the game values manager."""
        game_values = get_game_value_manager()
        self.points_per_question = game_values.get_value('scoring', 'points_per_correct', 10)
        self.points_per_incorrect = game_values.get_value('scoring', 'points_per_incorrect', 0)
        self.streak_bonus = game_values.get_value('scoring', 'streak_bonus', 5)
        self.max_streak_bonus = game_values.get_value('scoring', 'max_streak_bonus', 50)
        self.hint_penalty = game_values.get_value('scoring', 'hint_penalty', 5)
        self.speed_bonus = game_values.get_value('scoring', 'speed_bonus', 5)