#!/usr/bin/env python3
"""
Simple Analytics Stub - All analytics functionality removed
This stub prevents import errors while removing all tracking.
"""

class SimpleAnalyticsManagerStub:
    """Stub analytics manager - does nothing but prevents errors."""
    
    def __init__(self, data_file=None):
        pass
    
    def get_user_data(self, user_id):
        """Return empty user data."""
        return {
            'total_questions': 0,
            'correct_answers': 0,
            'accuracy': 0,
            'xp': 0,
            'level': 1,
            'study_streak': 0,
            'total_sessions': 0
        }
    
    def create_profile(self, user_id):
        """Stub - do nothing."""
        pass
    
    def get_dashboard_stats(self, user_id):
        """Return empty dashboard stats."""
        return {
            'level': 1,
            'xp': 0,
            'streak': 0,
            'total_correct': 0,
            'accuracy': 0,
            'total_questions': 0,
            'success': True
        }
    
    def get_analytics_stats(self, user_id):
        """Return empty analytics stats."""
        return {
            'total_questions': 0,
            'correct_answers': 0,
            'accuracy': 0,
            'success': True
        }
    
    def get_all_profiles(self):
        """Return empty profiles."""
        return {}
    
    def update_quiz_results(self, user_id, correct, topic=None, difficulty=None):
        """Stub - do nothing."""
        pass
    
    def update_session_with_actual_time(self, user_id, actual_duration, questions_answered=None):
        """Stub - do nothing."""
        pass
    
    def get_heatmap_data(self, user_id):
        """Return empty heatmap data."""
        return []
    
    def track_question_answer(self, user_id, correct, category):
        """Stub - do nothing."""
        pass
    
    def _update_user_data(self, user_id, user_data):
        """Stub - do nothing."""
        pass
    
    def _get_default_user_data(self):
        """Return default empty data."""
        return {
            'total_questions': 0,
            'correct_answers': 0,
            'accuracy': 0,
            'xp': 0,
            'level': 1,
            'study_streak': 0,
            'total_sessions': 0
        }
    
    def _save_data(self, data):
        """Stub - do nothing."""
        pass

# Global instance
_analytics_manager = SimpleAnalyticsManagerStub()

def get_analytics_manager():
    """Return stub analytics manager."""
    return _analytics_manager