#!/usr/bin/env python3
"""
Statistics Controller for Linux+ Study Game

Handles all statistics calculations, leaderboard management,
and achievement tracking logic.
"""

from datetime import datetime
from typing import Dict, List, Union, Any, TypedDict, Optional, Literal, Tuple, cast
from utils.config import *


# Define a type for question data
QuestionData = Union[List[Any], Tuple[Any, ...]]  # Updated to support both list and tuple structures

class LeaderboardEntry(TypedDict):
    date: str
    score: int
    total: int
    accuracy: float
    points: int

class FormattedLeaderboardEntry(TypedDict):
    rank: int
    date: str
    score: int
    total: int
    score_display: str
    accuracy: float
    accuracy_display: str
    points: int
    accuracy_level: str

class AchievementDict(TypedDict):
    badge: str
    description: str

class ProgressItem(TypedDict):
    current: int
    target: int
    percentage: float

class OverallStats(TypedDict):
    total_attempts: int
    total_correct: int
    overall_accuracy: float
    accuracy_level: Literal['good', 'average', 'poor']

class CategoryStat(TypedDict):
    category: str
    attempts: int
    correct: int
    accuracy: float
    accuracy_level: Literal['good', 'average', 'poor']

class QuestionPerformance(TypedDict):
    rank: int
    question_text: str
    question_display: str
    attempts: int
    correct: int
    accuracy: float
    accuracy_level: Literal['good', 'average', 'poor']
    last_result: str
    last_result_correct: Optional[bool]

class DetailedStatistics(TypedDict):
    overall: OverallStats
    categories: List[CategoryStat]
    questions: List[QuestionPerformance]
    has_category_data: bool
    has_question_data: bool

class CategoryData(TypedDict):
    """Data structure for category statistics."""
    attempts: int
    correct: int

class ReviewQuestionsData(TypedDict):
    has_questions: bool
    questions: List[QuestionData]  # Updated to use QuestionData type
    missing_questions: List[str]

class StatsController:
    """Handles statistics calculations and data aggregation."""
    
    def __init__(self, game_state: Any):
        """
        Initialize the stats controller.
        
        Args:
            game_state: GameState instance for data access
        """
        self.game_state = game_state
        # Ensure leaderboard is initialized
        if not hasattr(self.game_state, 'leaderboard') or self.game_state.leaderboard is None:
            self.game_state.leaderboard = []
    
    def get_progress_summary(self) -> Dict[str, Union[int, List[str]]]:
        """
        Get current progress summary data.
        
        Returns:
            dict: Progress summary containing session and total stats
        """
        # Calculate current streak from study history
        current_streak = self.calculate_current_streak()
        
        return {
            'session_points': self.game_state.session_points,
            'total_points': self.game_state.achievements.get('points_earned', 0),
            'questions_answered': self.game_state.achievements.get('questions_answered', 0),
            'current_streak': current_streak,
            'badges': self.game_state.achievements.get('badges', []),
            'days_studied': len(self.game_state.achievements.get('days_studied', []))
        }
    
    def calculate_current_streak(self) -> int:
        """Calculate current study streak from study history."""
        try:
            from datetime import datetime, timedelta
            
            days_studied = self.game_state.achievements.get('days_studied', [])
            if not days_studied:
                return 0
            
            # Sort dates in descending order
            sorted_dates = sorted([datetime.fromisoformat(date).date() for date in days_studied], reverse=True)
            current_date = datetime.now().date()
            
            # Check if user studied today or yesterday
            if sorted_dates[0] not in [current_date, current_date - timedelta(days=1)]:
                return 0
            
            # Count consecutive days
            streak = 0
            expected_date = current_date
            
            for study_date in sorted_dates:
                if study_date == expected_date:
                    streak += 1
                    expected_date -= timedelta(days=1)
                elif study_date == expected_date + timedelta(days=1):
                    # Skip today if not studied yet, but count yesterday
                    expected_date = study_date - timedelta(days=1)
                    streak += 1
                else:
                    break
            
            return streak
        except Exception as e:
            print(f"Error calculating streak: {e}")
            return 0
    
    def get_leaderboard_data(self) -> List[FormattedLeaderboardEntry]:
        """
        Get formatted leaderboard data.
        
        Returns:
            list: List of leaderboard entries sorted by performance
        """
        if not hasattr(self.game_state, 'leaderboard') or not self.game_state.leaderboard:
            return []
        
        # Return sorted leaderboard with formatted data
        formatted_entries: List[FormattedLeaderboardEntry] = []
        for i, entry in enumerate(self.game_state.leaderboard, 1):
            formatted_entry: FormattedLeaderboardEntry = {
                'rank': i,
                'date': entry["date"][:10],  # Just the date part
                'score': entry['score'],
                'total': entry['total'],
                'score_display': f"{entry['score']}/{entry['total']}",
                'accuracy': entry['accuracy'],
                'accuracy_display': f"{entry['accuracy']:.1f}%",
                'points': entry['points'],
                'accuracy_level': self._get_accuracy_level(entry['accuracy'])
            }
            formatted_entries.append(formatted_entry)
        
        return formatted_entries
    
    def get_achievements_data(self) -> Dict[str, Union[List[AchievementDict], Dict[str, ProgressItem], int]]:
        """
        Get comprehensive achievements data.
        
        Returns:
            dict: Achievement data including unlocked, available, and progress
        """
        all_achievements = {
            "streak_master": "Answer 5 questions correctly in a row",
            "dedicated_learner": "Study for 3 different days", 
            "century_club": "Answer 100 questions total",
            "point_collector": "Earn 500 points",
            "quick_fire_champion": "Complete Quick Fire mode",
            "daily_warrior": "Complete a daily challenge",
            "perfect_session": "Get 100% accuracy in a session (3+ questions)"
        }
        
        unlocked_badges = self.game_state.achievements.get('badges', [])
        
        # Create unlocked achievements with descriptions
        unlocked_achievements: List[AchievementDict] = []
        for badge in unlocked_badges:
            unlocked_achievements.append({
                'badge': badge,
                'description': self.game_state.get_achievement_description(badge)
            })
        
        # Create available achievements
        available_achievements: List[AchievementDict] = []
        for badge, description in all_achievements.items():
            if badge not in unlocked_badges:
                available_achievements.append({
                    'badge': badge,
                    'description': description
                })
        
        # Calculate progress data
        questions_answered = self.game_state.achievements.get('questions_answered', 0)
        points_earned = self.game_state.achievements.get('points_earned', 0)
        days_studied = len(self.game_state.achievements.get('days_studied', []))
        
        progress_data: Dict[str, ProgressItem] = {
            'questions_progress': {
                'current': questions_answered,
                'target': 100,
                'percentage': min((questions_answered / 100) * 100, 100)
            },
            'points_progress': {
                'current': points_earned,
                'target': 500,
                'percentage': min((points_earned / 500) * 100, 100)
            },
            'days_progress': {
                'current': days_studied,
                'target': 3,
                'percentage': min((days_studied / 3) * 100, 100)
            }
        }
        
        return {
            'unlocked': unlocked_achievements,
            'available': available_achievements,
            'progress': progress_data,
            'total_points': points_earned,
            'questions_answered': questions_answered,
            'days_studied': days_studied
        }
    
    def get_detailed_statistics(self) -> DetailedStatistics:
        """
        Get comprehensive statistics data.
        
        Returns:
            dict: Detailed statistics including overall, category, and question-specific data
        """
        history = self.game_state.study_history
        
        # Overall performance calculations
        total_attempts = history.get("total_attempts", 0)
        total_correct = history.get("total_correct", 0)
        overall_accuracy = (total_correct / total_attempts * 100) if total_attempts > 0 else 0
        
        overall_stats: OverallStats = {
            'total_attempts': total_attempts,
            'total_correct': total_correct,
            'overall_accuracy': overall_accuracy,
            'accuracy_level': self._get_accuracy_level(overall_accuracy)
        }
        
        # Category performance calculations
        categories_data = history.get("categories", {})
        category_stats: List[CategoryStat] = []
        
        # Filter and sort categories with attempts
        categories_with_attempts: List[Tuple[str, CategoryData]] = [
            (cat, cast(CategoryData, stats)) for cat, stats in categories_data.items() 
            if isinstance(stats, dict) and "attempts" in stats and stats["attempts"] > 0
        ]
        
        for category, stats in sorted(categories_with_attempts, key=lambda x: x[0]):
            cat_attempts = stats.get("attempts", 0)
            cat_correct = stats.get("correct", 0)
            cat_accuracy = (cat_correct / cat_attempts * 100)
            
            category_stats.append({
                'category': category,
                'attempts': cat_attempts,
                'correct': cat_correct,
                'accuracy': cat_accuracy,
                'accuracy_level': self._get_accuracy_level(cat_accuracy)
            })
        
        # Question-specific performance calculations
        question_stats = history.get("questions", {})
        question_performance: List[QuestionPerformance] = []
        
        # Filter questions with attempts and sort by accuracy (lowest first)
        attempted_questions: Dict[str, Dict[str, Any]] = {
            q: stats for q, stats in question_stats.items() 
            if isinstance(stats, dict) and cast(Dict[str, Any], stats).get("attempts", 0) > 0
        }
        
        def sort_key(item: Tuple[str, Dict[str, Any]]) -> Tuple[float, int]:
            q_text, stats = item
            attempts = stats.get("attempts", 0)
            correct = stats.get("correct", 0)
            accuracy = correct / attempts
            return (accuracy, -attempts)  # Sort by accuracy ascending, then attempts descending
        
        sorted_questions = sorted(attempted_questions.items(), key=sort_key)
        
        for i, (q_text, stats) in enumerate(sorted_questions):
            attempts = stats.get("attempts", 0)
            correct = stats.get("correct", 0)
            accuracy = (correct / attempts * 100)
            
            # Get last result
            last_result = "N/A"
            last_result_correct = None
            if isinstance(stats.get("history"), list) and stats["history"]:
                last_entry = stats["history"][-1]
                if isinstance(last_entry, dict) and "correct" in last_entry:
                    last_result_correct = cast(Optional[bool], last_entry["correct"])
                else:
                    last_result_correct = None
            
            question_performance.append({
                'rank': i + 1,
                'question_text': q_text,
                'question_display': (q_text[:75] + '...') if len(q_text) > 75 else q_text,
                'attempts': attempts,
                'correct': correct,
                'accuracy': accuracy,
                'accuracy_level': self._get_accuracy_level(accuracy),
                'last_result': last_result,
                'last_result_correct': last_result_correct
            })
        
        return cast(DetailedStatistics, {
            'overall': overall_stats,
            'categories': category_stats,
            'questions': question_performance,
            'has_category_data': len(category_stats) > 0,
            'has_question_data': len(question_performance) > 0
        })
    
    def clear_statistics(self):
        """
        Clear all statistics data including analytics database records.
        
        Returns:
            bool: True if cleared successfully
        """
        try:
            print("Starting clear statistics...")
            
            # Reset to default history structure
            self.game_state.study_history = self.game_state._default_history()
            print("Reset study history")
            
            # Re-populate categories with 0 stats
            for category in self.game_state.categories:
                self.game_state.study_history["categories"].setdefault(
                    category, {"correct": 0, "attempts": 0}
                )
            print("Reset categories")
            
            # Reset session state (this was missing before!)
            self.game_state.reset_session()
            print("Reset session state")
            
            # Clear achievements properly and reset achievement system completely
            if hasattr(self.game_state, 'achievement_system') and self.game_state.achievement_system:
                print("Found achievement system, resetting...")
                # Use the clear_achievements method to properly reset everything
                self.game_state.achievement_system.clear_achievements()
                
                # Reset session points to 0
                self.game_state.achievement_system.reset_session_points()
                
                # Ensure all achievement-related attributes are reset
                self.game_state.achievement_system.achievements = self.game_state.achievement_system._get_default_achievements()
                
                # Clear leaderboard in achievement system
                if hasattr(self.game_state.achievement_system, 'achievements') and 'leaderboard' in self.game_state.achievement_system.achievements:
                    self.game_state.achievement_system.achievements['leaderboard'] = []
                    
                # Also clear leaderboard property if it exists
                if hasattr(self.game_state.achievement_system, 'leaderboard'):
                    self.game_state.achievement_system.leaderboard = []
                    
                print("Reset achievements and leaderboard")
            
            # Reset game state achievements if they exist separately
            if hasattr(self.game_state, 'achievements'):
                # Since achievements is a property without setter, we need to reset its contents
                # Reset achievements data if it's a direct dictionary
                if isinstance(self.game_state.achievements, dict):
                    self.game_state.achievements.clear()
                    self.game_state.achievements.update({
                        "badges": [],
                        "points_earned": 0,
                        "days_studied": set(),
                        "questions_answered": 0,
                        "streaks_achieved": 0,
                        "perfect_sessions": 0,
                        "daily_warrior_dates": [],
                        "leaderboard": []
                    })
                    print("Reset game state achievements")
                else:
                    # If achievements is managed by achievement_system, it's already reset above
                    print("Achievements managed by achievement system - already reset")
            
            # Ensure leaderboard is also cleared in study_history
            if 'leaderboard' in self.game_state.study_history:
                self.game_state.study_history['leaderboard'] = []
                print("Cleared leaderboard in study history")
            
            # Clear analytics data from database
            try:
                from utils.database import get_database_manager
                from models.analytics import Analytics
                import os
                
                db_manager = get_database_manager()
                if db_manager and db_manager.session_factory:
                    analytics_session = db_manager.session_factory()
                    try:
                        # Delete all analytics records (or optionally just current user's records)
                        deleted_count = analytics_session.query(Analytics).delete()
                        analytics_session.commit()
                        print(f"Cleared {deleted_count} analytics records from database")
                        
                        # Create reset marker file to signal analytics service
                        os.makedirs('data', exist_ok=True)
                        from datetime import datetime
                        with open('data/.analytics_reset_marker', 'w') as f:
                            f.write(f"Reset at {datetime.now().isoformat()}")
                        print("Created analytics reset marker")
                        
                    except Exception as analytics_error:
                        print(f"Error clearing analytics data: {analytics_error}")
                        analytics_session.rollback()
                    finally:
                        analytics_session.close()
                else:
                    print("Analytics database not available - skipping database cleanup")
            except ImportError:
                print("Analytics database dependencies not available - skipping database cleanup")
            except Exception as analytics_error:
                print(f"Warning: Could not clear analytics data: {analytics_error}")
            
            # Clear any analytics service cached data by clearing the cache directory
            try:
                import shutil
                import os
                cache_dirs = ['data/cache', 'data/.cache', '.cache']
                for cache_dir in cache_dirs:
                    if os.path.exists(cache_dir):
                        shutil.rmtree(cache_dir)
                        print(f"Cleared cache directory: {cache_dir}")
            except Exception as cache_error:
                print(f"Warning: Could not clear cache directories: {cache_error}")
            
            # Save the cleared history and achievements
            print("Saving history...")
            self.game_state.save_history()
            
            print("Saving achievements...")
            if hasattr(self.game_state, 'save_achievements') and callable(self.game_state.save_achievements):
                self.game_state.save_achievements()
            
            # Also save achievements through the achievement system
            if hasattr(self.game_state, 'achievement_system') and hasattr(self.game_state.achievement_system, 'save_achievements'):
                self.game_state.achievement_system.save_achievements()
                
            print("Clear statistics completed successfully")
            return True
            
        except Exception as e:
            print(f"Error clearing statistics: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def update_leaderboard_entry(self, session_score: int, session_total: int, session_points: int) -> None:
        """
        Update leaderboard with a new session entry.
        
        Args:
            session_score (int): Number of correct answers in session
            session_total (int): Total questions answered in session  
            session_points (int): Points earned in session
        """
        if session_total == 0:
            return
        
        accuracy = (session_score / session_total) * 100
        entry: LeaderboardEntry = {
            "date": datetime.now().isoformat(),
            "score": session_score,
            "total": session_total,
            "accuracy": accuracy,
            "points": session_points
        }
        
        # Use the achievement system's leaderboard instead of direct property access
        self.game_state.achievement_system.leaderboard.append(entry)
        
        # Keep only top 10 sessions, sorted by accuracy then points
        def sort_key(entry: LeaderboardEntry) -> Tuple[float, int]:
            return (float(entry["accuracy"]), int(entry["points"]))
            
        self.game_state.achievement_system.leaderboard.sort(
            key=sort_key, 
            reverse=True
        )
        self.game_state.achievement_system.leaderboard = self.game_state.achievement_system.leaderboard[:10]
        
        # Update in history
        self.game_state.study_history["leaderboard"] = self.game_state.achievement_system.leaderboard
    
    def get_review_questions_data(self) -> ReviewQuestionsData:
        """
        Get data for questions marked as incorrect for review.
        
        Returns:
            ReviewQuestionsData: Review questions data with found and missing questions
        """
        incorrect_list: List[str] = self.game_state.study_history.get("incorrect_review", [])

        if not incorrect_list:
            return {
                'has_questions': False,
                'questions': [],
                'missing_questions': []
            }
        
        # Find full question data for each incorrect question text
        questions_to_review: List[QuestionData] = []
        missing_questions: List[str] = []
        
        for incorrect_text in incorrect_list:
            found = False
            for q_data in self.game_state.questions:
                # Cast q_data to QuestionData to help type checker
                q_data_typed = cast(QuestionData, q_data)
                if (isinstance(q_data, (list, tuple)) and 
                    len(q_data_typed) > 0 and q_data_typed[0] == incorrect_text):
                    questions_to_review.append(q_data_typed)
                    found = True
                    break
            
            if not found:
                missing_questions.append(incorrect_text)
        
        return {
            'has_questions': len(questions_to_review) > 0,
            'questions': questions_to_review,
            'missing_questions': missing_questions
        }
    
    def remove_from_review_list(self, question_text: str):
        """
        Remove a question from the incorrect review list.
        
        Args:
            question_text (str): Text of the question to remove
            
        Returns:
            bool: True if removed successfully
        """
        try:
            incorrect_list = self.game_state.study_history.get("incorrect_review", [])
            
            if isinstance(incorrect_list, list) and question_text in incorrect_list:
                self.game_state.study_history["incorrect_review"].remove(question_text)
                return True
            return False
            
        except Exception as e:
            print(f"Error removing question from review list: {e}")
            return False
    
    def cleanup_missing_review_questions(self, missing_questions: List[str]) -> int:
        """
        Remove questions from review list that no longer exist in the question pool.
        
        Args:
            missing_questions (list): List of question texts that are missing
            
        Returns:
            int: Number of questions removed
        """
        try:
            original_len = len(self.game_state.study_history.get("incorrect_review", []))
            
            self.game_state.study_history["incorrect_review"] = [
                q_text for q_text in self.game_state.study_history.get("incorrect_review", [])
                if q_text not in missing_questions
            ]
            
            new_len = len(self.game_state.study_history.get("incorrect_review", []))
            return original_len - new_len
            
        except Exception as e:
            print(f"Error cleaning up review questions: {e}")
            return 0
    
    def _get_accuracy_level(self, accuracy: float) -> Literal['good', 'average', 'poor']:
        """
        Get accuracy level classification.
        
        Args:
            accuracy (float): Accuracy percentage
            
        Returns:
            str: 'good', 'average', or 'poor'
        """
        if accuracy >= 75:
            return 'good'
        elif accuracy >= 50:
            return 'average'
        else:
            return 'poor'