#!/usr/bin/env python3
"""
Unified Analytics Provider - Single Source of Truth for Analytics Data

This module provides a unified interface to analytics data to prevent inconsistencies
across the application. It consolidates data from multiple sources into consistent
calculations.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from models.analytics import Analytics
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, func

logger = logging.getLogger(__name__)

class UnifiedAnalyticsProvider:
    """
    Single source of truth for all analytics data to prevent inconsistencies
    between different analytics systems (StatsController, AnalyticsService, etc.)
    """
    
    def __init__(self, user_id: str, db_session=None):
        self.user_id = user_id
        self.db_session = db_session
        self._cache = {}
        
    def _get_analytics_data(self) -> Dict[str, Any]:
        """Get analytics data from database or cache"""
        if 'analytics_data' in self._cache:
            return self._cache['analytics_data']
            
        try:
            if not self.db_session:
                # Create database session if not provided
                from utils.database import DatabasePoolManager
                db_manager = DatabasePoolManager()
                with db_manager.get_session() as session:
                    analytics = session.query(Analytics).filter_by(user_id=self.user_id).first()
            else:
                session = self.db_session
                analytics = session.query(Analytics).filter_by(user_id=self.user_id).first()
            
            if analytics:
                data = {
                    'total_questions': analytics.total_questions or 0,
                    'correct_answers': analytics.correct_answers or 0,
                    'accuracy': analytics.accuracy or 0,
                    'study_streak': analytics.study_streak or 0,
                    'total_sessions': analytics.total_sessions or 0,
                    'questions_to_review': analytics.questions_to_review or 0,
                    'mastery_score': analytics.mastery_score or 0,
                    'xp_earned': analytics.xp_earned or 0,
                    'level': analytics.level or 1,
                    'achievements_unlocked': analytics.achievements_unlocked or 0
                }
            else:
                # Return empty data if no analytics found
                data = {
                    'total_questions': 0,
                    'correct_answers': 0,
                    'accuracy': 0,
                    'study_streak': 0,
                    'total_sessions': 0,
                    'questions_to_review': 0,
                    'mastery_score': 0,
                    'xp_earned': 0,
                    'level': 1,
                    'achievements_unlocked': 0
                }
                
            self._cache['analytics_data'] = data
            return data
            
        except Exception as e:
            logger.error(f"Error getting analytics data for user {self.user_id}: {e}")
            return {
                'total_questions': 0,
                'correct_answers': 0,
                'accuracy': 0,
                'study_streak': 0,
                'total_sessions': 0,
                'questions_to_review': 0,
                'mastery_score': 0,
                'xp_earned': 0,
                'level': 1,
                'achievements_unlocked': 0
            }
    
    def get_dashboard_stats(self) -> Dict[str, Any]:
        """Get consistent dashboard statistics"""
        data = self._get_analytics_data()
        
        # Calculate level progression
        total_questions = data['total_questions']
        level = max(1, (total_questions // 50) + 1)  # Level up every 50 questions
        level_progress = ((total_questions % 50) / 50) * 100
        
        # Calculate XP
        base_xp = total_questions * 10
        accuracy_bonus = int((data['accuracy'] / 100) * total_questions * 5) if total_questions > 0 else 0
        total_xp = base_xp + accuracy_bonus
        
        return {
            'level': level,
            'xp': total_xp,
            'level_progress': level_progress,
            'streak': data['study_streak'],
            'total_correct': data['correct_answers'],
            'accuracy': data['accuracy'],
            'session_points': total_xp,
            'total_points': total_xp,
            'questions_answered': total_questions,
            'days_studied': data['study_streak'],
            'badges_earned': min(10, level - 1),
            'total_sessions': data['total_sessions']
        }
    
    def get_analytics_stats(self) -> Dict[str, Any]:
        """Get consistent analytics page statistics"""
        data = self._get_analytics_data()
        
        return {
            'total_questions': data['total_questions'],
            'correct_answers': data['correct_answers'],
            'accuracy': data['accuracy'],
            'study_streak': data['study_streak'],
            'total_sessions': data['total_sessions'],
            'questions_to_review': data['questions_to_review'],
            'mastery_score': data['mastery_score']
        }
    
    def get_review_stats(self) -> Dict[str, Any]:
        """Get consistent review system statistics"""
        data = self._get_analytics_data()
        
        return {
            'questions_to_review': data['questions_to_review'],
            'total_attempts': data['total_questions'],
            'correct_attempts': data['correct_answers'],
            'review_accuracy': data['accuracy']
        }
    
    def get_achievement_stats(self) -> Dict[str, Any]:
        """Get consistent achievement system statistics"""
        data = self._get_analytics_data()
        
        # Calculate achievements based on consistent data
        total_questions = data['total_questions']
        level = max(1, (total_questions // 50) + 1)
        
        return {
            'questions_answered': total_questions,
            'total_correct': data['correct_answers'],
            'accuracy': data['accuracy'],
            'level': level,
            'xp_earned': data['xp_earned'],
            'achievements_unlocked': data['achievements_unlocked'],
            'study_streak': data['study_streak']
        }


def get_unified_analytics(user_id: str, db_session=None) -> UnifiedAnalyticsProvider:
    """Factory function to create UnifiedAnalyticsProvider instance"""
    return UnifiedAnalyticsProvider(user_id, db_session)
