#!/usr/bin/env python3
"""
Statistics Controller for Linux+ Study Game

Handles all statistics calculations, leaderboard management,
and achievement tracking logic.
"""

from datetime import datetime
from utils.config import *


class StatsController:
    """Handles statistics calculations and data aggregation."""
    
    def __init__(self, game_state):
        """
        Initialize the stats controller.
        
        Args:
            game_state: GameState instance for data access
        """
        self.game_state = game_state
    
    def get_progress_summary(self):
        """
        Get current progress summary data.
        
        Returns:
            dict: Progress summary containing session and total stats
        """
        return {
            'session_points': self.game_state.session_points,
            'total_points': self.game_state.achievements.get('points_earned', 0),
            'questions_answered': self.game_state.achievements.get('questions_answered', 0),
            'current_streak': getattr(self.game_state, 'current_streak', 0),
            'badges': self.game_state.achievements.get('badges', []),
            'days_studied': len(self.game_state.achievements.get('days_studied', []))
        }
    
    def get_leaderboard_data(self):
        """
        Get formatted leaderboard data.
        
        Returns:
            list: List of leaderboard entries sorted by performance
        """
        if not self.game_state.leaderboard:
            return []
        
        # Return sorted leaderboard with formatted data
        formatted_entries = []
        for i, entry in enumerate(self.game_state.leaderboard, 1):
            formatted_entry = {
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
    
    def get_achievements_data(self):
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
        unlocked_achievements = []
        for badge in unlocked_badges:
            unlocked_achievements.append({
                'badge': badge,
                'description': self.game_state.get_achievement_description(badge)
            })
        
        # Create available achievements
        available_achievements = []
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
        
        progress_data = {
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
    
    def get_detailed_statistics(self):
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
        
        overall_stats = {
            'total_attempts': total_attempts,
            'total_correct': total_correct,
            'overall_accuracy': overall_accuracy,
            'accuracy_level': self._get_accuracy_level(overall_accuracy)
        }
        
        # Category performance calculations
        categories_data = history.get("categories", {})
        category_stats = []
        
        # Filter and sort categories with attempts
        categories_with_attempts = [
            (cat, stats) for cat, stats in categories_data.items() 
            if isinstance(stats, dict) and stats.get("attempts", 0) > 0
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
        question_performance = []
        
        # Filter questions with attempts and sort by accuracy (lowest first)
        attempted_questions = {
            q: stats for q, stats in question_stats.items() 
            if isinstance(stats, dict) and stats.get("attempts", 0) > 0
        }
        
        def sort_key(item):
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
                    last_result_correct = last_entry.get("correct")
                    last_result = "Correct" if last_result_correct else "Incorrect"
            
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
        
        return {
            'overall': overall_stats,
            'categories': category_stats,
            'questions': question_performance,
            'has_category_data': len(category_stats) > 0,
            'has_question_data': len(question_performance) > 0
        }
    
    def clear_statistics(self):
        """
        Clear all statistics data.
        
        Returns:
            bool: True if cleared successfully
        """
        try:
            # Reset to default history structure
            self.game_state.study_history = self.game_state._default_history()
            
            # Re-populate categories with 0 stats
            for category in self.game_state.categories:
                self.game_state.study_history["categories"].setdefault(
                    category, {"correct": 0, "attempts": 0}
                )
            
            # Save the cleared history
            self.game_state.save_history()
            return True
            
        except Exception as e:
            print(f"Error clearing statistics: {e}")
            return False
    
    def update_leaderboard_entry(self, session_score, session_total, session_points):
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
        entry = {
            "date": datetime.now().isoformat(),
            "score": session_score,
            "total": session_total,
            "accuracy": accuracy,
            "points": session_points
        }
        
        self.game_state.leaderboard.append(entry)
        
        # Keep only top 10 sessions, sorted by accuracy then points
        self.game_state.leaderboard.sort(
            key=lambda x: (x["accuracy"], x["points"]), 
            reverse=True
        )
        self.game_state.leaderboard = self.game_state.leaderboard[:10]
        
        # Update in history
        self.game_state.study_history["leaderboard"] = self.game_state.leaderboard
    
    def get_review_questions_data(self):
        """
        Get data for questions marked as incorrect for review.
        
        Returns:
            dict: Review questions data with found and missing questions
        """
        incorrect_list = self.game_state.study_history.get("incorrect_review", [])
        
        # Ensure it's a list
        if not isinstance(incorrect_list, list):
            incorrect_list = []
            self.game_state.study_history["incorrect_review"] = []
        
        if not incorrect_list:
            return {
                'has_questions': False,
                'questions': [],
                'missing_questions': []
            }
        
        # Find full question data for each incorrect question text
        questions_to_review = []
        missing_questions = []
        
        for incorrect_text in incorrect_list:
            found = False
            for q_data in self.game_state.questions:
                if (isinstance(q_data, (list, tuple)) and 
                    len(q_data) > 0 and q_data[0] == incorrect_text):
                    questions_to_review.append(q_data)
                    found = True
                    break
            
            if not found:
                missing_questions.append(incorrect_text)
        
        return {
            'has_questions': len(questions_to_review) > 0,
            'questions': questions_to_review,
            'missing_questions': missing_questions
        }
    
    def remove_from_review_list(self, question_text):
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
    
    def cleanup_missing_review_questions(self, missing_questions):
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
    
    def _get_accuracy_level(self, accuracy):
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