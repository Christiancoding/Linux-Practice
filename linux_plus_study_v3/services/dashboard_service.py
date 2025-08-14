#!/usr/bin/env python3
"""
Dashboard Data Service for Linux+ Study System

Comprehensive data loading service inspired by Money Manager's architecture.
Provides centralized data aggregation for all pages/tabs with proper error handling.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple
from utils.database import get_db_session
from models.db_models import Analytics, UserAchievement, UserHistory, Question
from services.db_time_tracking_service import DBTimeTrackingService
from utils.config import QUIZ_SETTINGS
import json

logger = logging.getLogger(__name__)

class DashboardService:
    """Centralized dashboard data service for comprehensive page loading."""
    
    def __init__(self, user_id: str = 'anonymous'):
        """Initialize dashboard service for a specific user."""
        self.user_id = user_id
        self.time_tracking = DBTimeTrackingService(user_id)
    
    def get_dashboard_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive dashboard summary similar to Money Manager's index route.
        Provides all data needed for the main dashboard with proper error handling.
        """
        try:
            # Get analytics data from the JSON-based analytics service
            analytics_data = self._get_analytics_data()
            
            # Get time-based summaries (today, week, month) - try DB first, fallback to analytics
            today_summary = self._get_period_summary(1, analytics_data)
            week_summary = self._get_period_summary(7, analytics_data)
            month_summary = self._get_period_summary(30, analytics_data)
            
            # Get recent activity - try DB first, fallback to analytics
            recent_sessions = self._get_recent_sessions(limit=10, analytics_data=analytics_data)
            recent_questions = self._get_recent_questions(limit=5, analytics_data=analytics_data)
            
            # Get user progress and achievements - use analytics data
            user_progress = self._get_user_progress_from_analytics(analytics_data)
            achievements_summary = self._get_achievements_summary_from_analytics(analytics_data)
            
            # Get study statistics
            study_stats = self._get_study_statistics()
            
            # Get quiz performance metrics - use analytics data
            performance_metrics = self._get_performance_metrics_from_analytics(analytics_data)
            
            # Get category breakdown - use analytics data
            category_breakdown = self._get_category_breakdown_from_analytics(analytics_data)
            
            # Calculate total study metrics - use analytics data
            total_study_metrics = self._calculate_total_metrics_from_analytics(analytics_data)
            
            logger.info(f"Dashboard summary loaded for user {self.user_id}")
            
            dashboard_data = {
                # Time-based summaries
                'today': today_summary,
                'week': week_summary,
                'month': month_summary,
                
                # Recent activity
                'recent_sessions': recent_sessions,
                'recent_questions': recent_questions,
                
                # User progress
                'user_progress': user_progress,
                'achievements_summary': achievements_summary,
                
                # Study statistics
                'study_stats': study_stats,
                'performance_metrics': performance_metrics,
                'category_breakdown': category_breakdown,
                
                # Totals
                'total_metrics': total_study_metrics,
                
                # Metadata
                'last_updated': datetime.now().isoformat(),
                'user_id': self.user_id
            }
            
            # Validate data integrity 
            is_valid, validation_issues = validate_dashboard_data(dashboard_data)
            if not is_valid:
                logger.warning(f"Dashboard data validation issues for user {self.user_id}: {validation_issues}")
                # Add validation metadata
                dashboard_data['validation'] = {
                    'is_valid': False,
                    'issues': validation_issues,
                    'validated_at': datetime.now().isoformat()
                }
            else:
                dashboard_data['validation'] = {
                    'is_valid': True,
                    'issues': [],
                    'validated_at': datetime.now().isoformat()
                }
            
            return dashboard_data
            
        except Exception as e:
            logger.error(f"Error loading dashboard summary for {self.user_id}: {e}", exc_info=True)
            return self._get_fallback_dashboard()
    
    def _get_period_summary(self, days: int, analytics_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Get summary statistics for a specific time period."""
        try:
            with get_db_session() as session:
                # Calculate date range
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days)
                
                # Get analytics data for period
                period_analytics = session.query(Analytics).filter(
                    Analytics.user_id == self.user_id,
                    Analytics.session_start >= start_date,
                    Analytics.session_start <= end_date
                ).all()
                
                # Aggregate statistics
                total_sessions = len(period_analytics)
                total_questions = sum(a.questions_attempted for a in period_analytics)
                total_correct = sum(a.questions_correct for a in period_analytics)
                total_time = sum(a.session_duration or 0 for a in period_analytics)
                
                accuracy = (total_correct / total_questions * 100) if total_questions > 0 else 0
                avg_session_time = total_time / total_sessions if total_sessions > 0 else 0
                
                return {
                    'sessions': total_sessions,
                    'questions_attempted': total_questions,
                    'questions_correct': total_correct,
                    'accuracy': round(accuracy, 1),
                    'total_time': total_time,
                    'avg_session_time': avg_session_time,
                    'time_formatted': self._format_time(total_time),
                    'period_days': days
                }
                
        except Exception as e:
            logger.warning(f"Error getting {days}-day summary: {e}")
            return {
                'sessions': 0, 'questions_attempted': 0, 'questions_correct': 0,
                'accuracy': 0, 'total_time': 0, 'avg_session_time': 0,
                'time_formatted': '0s', 'period_days': days
            }
    
    def _get_recent_sessions(self, limit: int = 10, analytics_data: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Get recent study sessions with details."""
        try:
            with get_db_session() as session:
                recent_analytics = session.query(Analytics).filter(
                    Analytics.user_id == self.user_id
                ).order_by(Analytics.session_start.desc()).limit(limit).all()
                
                sessions = []
                for analytics in recent_analytics:
                    accuracy = 0
                    if analytics.questions_attempted > 0:
                        accuracy = (analytics.questions_correct / analytics.questions_attempted) * 100
                    
                    sessions.append({
                        'session_id': analytics.session_id,
                        'date': analytics.session_start.strftime('%Y-%m-%d'),
                        'time': analytics.session_start.strftime('%H:%M'),
                        'duration': analytics.session_duration or 0,
                        'duration_formatted': self._format_time(analytics.session_duration or 0),
                        'questions_attempted': analytics.questions_attempted,
                        'questions_correct': analytics.questions_correct,
                        'accuracy': round(accuracy, 1),
                        'activity_type': analytics.activity_type,
                        'topic_area': analytics.topic_area
                    })
                
                return sessions
                
        except Exception as e:
            logger.warning(f"Error getting recent sessions: {e}")
            return []
    
    def _get_recent_questions(self, limit: int = 5, analytics_data: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Get recently answered questions with performance."""
        try:
            with get_db_session() as session:
                recent_history = session.query(UserHistory).filter(
                    UserHistory.user_id == self.user_id,
                    UserHistory.activity_type == 'quiz'
                ).order_by(UserHistory.created_at.desc()).limit(limit).all()
                
                questions = []
                for history in recent_history:
                    questions.append({
                        'question_id': history.question_id,
                        'date': history.created_at.strftime('%Y-%m-%d %H:%M'),
                        'is_correct': history.is_correct,
                        'time_taken': history.time_taken,
                        'points_earned': history.points_earned,
                        'category': history.category,
                        'difficulty': history.difficulty,
                        'answer_given': history.answer_given,
                        'correct_answer': history.correct_answer
                    })
                
                return questions
                
        except Exception as e:
            logger.warning(f"Error getting recent questions: {e}")
            return []
    
    def _get_user_progress(self) -> Dict[str, Any]:
        """Get user progress and level information."""
        try:
            with get_db_session() as session:
                achievement_data = session.query(UserAchievement).filter_by(
                    user_id=self.user_id
                ).first()
                
                if not achievement_data:
                    return {
                        'level': 1, 'xp': 0, 'xp_to_next': 100,
                        'streak': 0, 'total_points': 0,
                        'questions_answered': 0, 'days_studied': 0
                    }
                
                # Calculate level and XP
                total_points = achievement_data.points_earned
                level = max(1, total_points // 100)  # 100 points per level
                xp = total_points % 100
                xp_to_next = 100 - xp
                
                # Parse days studied
                days_studied_data = json.loads(achievement_data.days_studied) if isinstance(achievement_data.days_studied, str) else achievement_data.days_studied
                days_studied = len(days_studied_data) if isinstance(days_studied_data, (list, set)) else 0
                
                return {
                    'level': level,
                    'xp': xp,
                    'xp_to_next': xp_to_next,
                    'xp_percentage': (xp / 100) * 100,
                    'streak': achievement_data.streaks_achieved,
                    'total_points': total_points,
                    'questions_answered': achievement_data.questions_answered,
                    'days_studied': days_studied,
                    'perfect_sessions': achievement_data.perfect_sessions
                }
                
        except Exception as e:
            logger.warning(f"Error getting user progress: {e}")
            return {
                'level': 1, 'xp': 0, 'xp_to_next': 100, 'xp_percentage': 0,
                'streak': 0, 'total_points': 0, 'questions_answered': 0,
                'days_studied': 0, 'perfect_sessions': 0
            }
    
    def _get_achievements_summary(self) -> Dict[str, Any]:
        """Get achievements summary for dashboard."""
        try:
            with get_db_session() as session:
                achievement_data = session.query(UserAchievement).filter_by(
                    user_id=self.user_id
                ).first()
                
                if not achievement_data:
                    return {
                        'total_badges': 0, 'recent_badges': [],
                        'completion_percentage': 0, 'next_milestone': 'First Quiz'
                    }
                
                # Parse badges
                badges_data = json.loads(achievement_data.badges) if isinstance(achievement_data.badges, str) else achievement_data.badges
                badges = badges_data if isinstance(badges_data, list) else []
                
                # Calculate completion percentage (assuming 20 total achievements)
                total_possible = 20
                completion_percentage = min(100, (len(badges) / total_possible) * 100)
                
                # Get recent badges (last 3)
                recent_badges = badges[-3:] if len(badges) > 3 else badges
                
                # Determine next milestone
                next_milestone = self._get_next_milestone(achievement_data)
                
                return {
                    'total_badges': len(badges),
                    'recent_badges': recent_badges,
                    'completion_percentage': round(completion_percentage, 1),
                    'next_milestone': next_milestone,
                    'all_badges': badges
                }
                
        except Exception as e:
            logger.warning(f"Error getting achievements summary: {e}")
            return {
                'total_badges': 0, 'recent_badges': [],
                'completion_percentage': 0, 'next_milestone': 'First Quiz'
            }
    
    def _get_study_statistics(self) -> Dict[str, Any]:
        """Get comprehensive study statistics."""
        try:
            # Get time tracking data
            time_data = self.time_tracking.get_daily_summary()
            weekly_data = self.time_tracking.get_weekly_summary()
            
            # Get study streak information
            streak_info = self._calculate_study_streak()
            
            return {
                'today_time': time_data.get('quiz_time_today', 0),
                'today_formatted': time_data.get('quiz_time_formatted', '0s'),
                'total_time': time_data.get('total_study_time', 0),
                'total_formatted': time_data.get('study_time_formatted', '0s'),
                'weekly_summary': weekly_data,
                'current_streak': streak_info.get('current_streak', 0),
                'longest_streak': streak_info.get('longest_streak', 0),
                'average_daily': self._calculate_average_daily_time()
            }
            
        except Exception as e:
            logger.warning(f"Error getting study statistics: {e}")
            return {
                'today_time': 0, 'today_formatted': '0s',
                'total_time': 0, 'total_formatted': '0s',
                'weekly_summary': {}, 'current_streak': 0,
                'longest_streak': 0, 'average_daily': 0
            }
    
    def _get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics and trends."""
        try:
            with get_db_session() as session:
                # Get recent performance data
                recent_analytics = session.query(Analytics).filter(
                    Analytics.user_id == self.user_id,
                    Analytics.questions_attempted > 0
                ).order_by(Analytics.session_start.desc()).limit(30).all()
                
                if not recent_analytics:
                    return {'accuracy_trend': 'stable', 'performance_level': 'beginner'}
                
                # Calculate metrics
                total_attempted = sum(a.questions_attempted for a in recent_analytics)
                total_correct = sum(a.questions_correct for a in recent_analytics)
                overall_accuracy = (total_correct / total_attempted * 100) if total_attempted > 0 else 0
                
                # Calculate trend
                first_half = recent_analytics[len(recent_analytics)//2:]
                second_half = recent_analytics[:len(recent_analytics)//2]
                
                first_accuracy = self._calculate_group_accuracy(first_half)
                second_accuracy = self._calculate_group_accuracy(second_half)
                
                trend = 'improving' if second_accuracy > first_accuracy + 5 else \
                       'declining' if second_accuracy < first_accuracy - 5 else 'stable'
                
                # Determine performance level
                performance_level = 'expert' if overall_accuracy >= 90 else \
                                  'advanced' if overall_accuracy >= 80 else \
                                  'intermediate' if overall_accuracy >= 70 else \
                                  'beginner'
                
                return {
                    'overall_accuracy': round(overall_accuracy, 1),
                    'accuracy_trend': trend,
                    'performance_level': performance_level,
                    'recent_sessions': len(recent_analytics),
                    'total_attempted': total_attempted,
                    'total_correct': total_correct,
                    'trend_change': round(second_accuracy - first_accuracy, 1)
                }
                
        except Exception as e:
            logger.warning(f"Error getting performance metrics: {e}")
            return {
                'overall_accuracy': 0, 'accuracy_trend': 'stable',
                'performance_level': 'beginner', 'recent_sessions': 0,
                'total_attempted': 0, 'total_correct': 0, 'trend_change': 0
            }
    
    def _get_category_breakdown(self) -> List[Dict[str, Any]]:
        """Get category performance breakdown."""
        try:
            with get_db_session() as session:
                # Get category performance data
                categories = {}
                history_records = session.query(UserHistory).filter(
                    UserHistory.user_id == self.user_id,
                    UserHistory.category.isnot(None)
                ).all()
                
                for record in history_records:
                    cat = record.category
                    if cat not in categories:
                        categories[cat] = {'attempted': 0, 'correct': 0}
                    
                    categories[cat]['attempted'] += 1
                    if record.is_correct:
                        categories[cat]['correct'] += 1
                
                # Format for output
                breakdown = []
                for category, stats in categories.items():
                    accuracy = (stats['correct'] / stats['attempted'] * 100) if stats['attempted'] > 0 else 0
                    
                    breakdown.append({
                        'category': category,
                        'attempted': stats['attempted'],
                        'correct': stats['correct'],
                        'accuracy': round(accuracy, 1),
                        'accuracy_level': 'good' if accuracy >= 80 else 'average' if accuracy >= 60 else 'poor'
                    })
                
                # Sort by accuracy descending
                breakdown.sort(key=lambda x: x['accuracy'], reverse=True)
                return breakdown
                
        except Exception as e:
            logger.warning(f"Error getting category breakdown: {e}")
            return []
    
    def _calculate_total_metrics(self) -> Dict[str, Any]:
        """Calculate total lifetime metrics."""
        try:
            with get_db_session() as session:
                # Get all analytics data
                all_analytics = session.query(Analytics).filter(
                    Analytics.user_id == self.user_id
                ).all()
                
                total_sessions = len(all_analytics)
                total_questions = sum(a.questions_attempted for a in all_analytics)
                total_correct = sum(a.questions_correct for a in all_analytics)
                total_time = sum(a.session_duration or 0 for a in all_analytics)
                
                # Get first session date
                first_session = None
                if all_analytics:
                    first_session = min(a.session_start for a in all_analytics)
                    days_active = (datetime.now() - first_session).days + 1
                else:
                    days_active = 0
                
                overall_accuracy = (total_correct / total_questions * 100) if total_questions > 0 else 0
                
                return {
                    'total_sessions': total_sessions,
                    'total_questions': total_questions,
                    'total_correct': total_correct,
                    'overall_accuracy': round(overall_accuracy, 1),
                    'total_time': total_time,
                    'total_time_formatted': self._format_time(total_time),
                    'days_active': days_active,
                    'first_session': first_session.strftime('%Y-%m-%d') if first_session else None,
                    'avg_questions_per_session': round(total_questions / total_sessions, 1) if total_sessions > 0 else 0
                }
                
        except Exception as e:
            logger.warning(f"Error calculating total metrics: {e}")
            return {
                'total_sessions': 0, 'total_questions': 0, 'total_correct': 0,
                'overall_accuracy': 0, 'total_time': 0, 'total_time_formatted': '0s',
                'days_active': 0, 'first_session': None, 'avg_questions_per_session': 0
            }
    
    def _calculate_study_streak(self) -> Dict[str, int]:
        """Calculate current and longest study streaks."""
        try:
            with get_db_session() as session:
                achievement_data = session.query(UserAchievement).filter_by(
                    user_id=self.user_id
                ).first()
                
                if not achievement_data:
                    return {'current_streak': 0, 'longest_streak': 0}
                
                # Parse days studied
                days_studied_data = json.loads(achievement_data.days_studied) if isinstance(achievement_data.days_studied, str) else achievement_data.days_studied
                
                if not isinstance(days_studied_data, (list, set)):
                    return {'current_streak': 0, 'longest_streak': 0}
                
                # Convert to sorted list of dates
                study_dates = sorted([datetime.strptime(date, '%Y-%m-%d').date() for date in days_studied_data])
                
                if not study_dates:
                    return {'current_streak': 0, 'longest_streak': 0}
                
                # Calculate current streak
                current_streak = 0
                today = datetime.now().date()
                
                if today in [d for d in study_dates]:
                    current_streak = 1
                    check_date = today - timedelta(days=1)
                    
                    while check_date in [d for d in study_dates]:
                        current_streak += 1
                        check_date -= timedelta(days=1)
                
                # Calculate longest streak
                longest_streak = 0
                temp_streak = 0
                
                for i, date in enumerate(study_dates):
                    if i == 0 or (date - study_dates[i-1]).days == 1:
                        temp_streak += 1
                    else:
                        longest_streak = max(longest_streak, temp_streak)
                        temp_streak = 1
                
                longest_streak = max(longest_streak, temp_streak)
                
                return {
                    'current_streak': current_streak,
                    'longest_streak': longest_streak
                }
                
        except Exception as e:
            logger.warning(f"Error calculating study streak: {e}")
            return {'current_streak': 0, 'longest_streak': 0}
    
    def _calculate_average_daily_time(self) -> float:
        """Calculate average daily study time."""
        try:
            weekly_data = self.time_tracking.get_weekly_summary()
            if not weekly_data:
                return 0.0
            
            total_time = sum(weekly_data.values())
            days_with_activity = sum(1 for time in weekly_data.values() if time > 0)
            
            return total_time / days_with_activity if days_with_activity > 0 else 0.0
            
        except Exception as e:
            logger.warning(f"Error calculating average daily time: {e}")
            return 0.0
    
    def _calculate_group_accuracy(self, analytics_group: List[Any]) -> float:
        """Calculate accuracy for a group of analytics records."""
        if not analytics_group:
            return 0.0
        
        total_attempted = sum(a.questions_attempted for a in analytics_group)
        total_correct = sum(a.questions_correct for a in analytics_group)
        
        return (total_correct / total_attempted * 100) if total_attempted > 0 else 0.0
    
    def _get_next_milestone(self, achievement_data: Any) -> str:
        """Determine the next achievement milestone."""
        try:
            questions_answered = achievement_data.questions_answered
            
            if questions_answered < 10:
                return "Answer 10 Questions"
            elif questions_answered < 50:
                return "Answer 50 Questions"
            elif questions_answered < 100:
                return "Answer 100 Questions"
            elif questions_answered < 500:
                return "Answer 500 Questions"
            elif achievement_data.perfect_sessions < 5:
                return "Get 5 Perfect Sessions"
            elif achievement_data.streaks_achieved < 10:
                return "Achieve 10 Study Streaks"
            else:
                return "Master Level Achieved"
                
        except Exception:
            return "First Quiz"
    
    def _format_time(self, seconds: float) -> str:
        """Format seconds into readable time format."""
        if seconds < 60:
            return f"{seconds:.1f}s"
        
        minutes = int(seconds // 60)
        remaining_seconds = seconds % 60
        
        if minutes < 60:
            if remaining_seconds < 0.1:
                return f"{minutes}m"
            else:
                return f"{minutes}m {remaining_seconds:.1f}s"
        else:
            hours = minutes // 60
            remaining_minutes = minutes % 60
            if remaining_minutes == 0:
                return f"{hours}h"
            else:
                return f"{hours}h {remaining_minutes}m"
    
    def _get_fallback_dashboard(self) -> Dict[str, Any]:
        """Provide fallback dashboard data when errors occur."""
        return {
            'today': {'sessions': 0, 'questions_attempted': 0, 'questions_correct': 0, 'accuracy': 0, 'total_time': 0, 'time_formatted': '0s'},
            'week': {'sessions': 0, 'questions_attempted': 0, 'questions_correct': 0, 'accuracy': 0, 'total_time': 0, 'time_formatted': '0s'},
            'month': {'sessions': 0, 'questions_attempted': 0, 'questions_correct': 0, 'accuracy': 0, 'total_time': 0, 'time_formatted': '0s'},
            'recent_sessions': [],
            'recent_questions': [],
            'user_progress': {'level': 1, 'xp': 0, 'xp_to_next': 100, 'xp_percentage': 0, 'streak': 0, 'total_points': 0, 'questions_answered': 0, 'days_studied': 0, 'perfect_sessions': 0},
            'achievements_summary': {'total_badges': 0, 'recent_badges': [], 'completion_percentage': 0, 'next_milestone': 'First Quiz'},
            'study_stats': {'today_time': 0, 'today_formatted': '0s', 'total_time': 0, 'total_formatted': '0s', 'weekly_summary': {}, 'current_streak': 0, 'longest_streak': 0, 'average_daily': 0},
            'performance_metrics': {'overall_accuracy': 0, 'accuracy_trend': 'stable', 'performance_level': 'beginner', 'recent_sessions': 0, 'total_attempted': 0, 'total_correct': 0, 'trend_change': 0},
            'category_breakdown': [],
            'total_metrics': {'total_sessions': 0, 'total_questions': 0, 'total_correct': 0, 'overall_accuracy': 0, 'total_time': 0, 'total_time_formatted': '0s', 'days_active': 0, 'first_session': None, 'avg_questions_per_session': 0},
            'last_updated': datetime.now().isoformat(),
            'user_id': self.user_id
        }
    
    def _get_analytics_data(self) -> Dict[str, Any]:
        """Get analytics data from SimpleAnalyticsManager."""
        try:
            from services.simple_analytics import SimpleAnalyticsManager
            analytics = SimpleAnalyticsManager()
            return analytics.get_user_data(self.user_id)
        except Exception as e:
            logger.warning(f"Error getting analytics data: {e}")
            return {}
    
    def _get_user_progress_from_analytics(self, analytics_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get user progress from analytics data."""
        try:
            # Try database first
            db_progress = self._get_user_progress()
            if db_progress.get('total_points', 0) > 0:
                return db_progress
            
            # Fallback to analytics data - handle both old and new formats
            total_questions = analytics_data.get('total_questions', 0)
            # Handle both 'total_correct' and 'correct_answers' for backward compatibility
            total_correct = analytics_data.get('total_correct', analytics_data.get('correct_answers', 0))
            total_points = total_correct * 10  # 10 points per correct answer
            
            level = max(1, total_points // 100)  # 100 points per level
            xp = total_points % 100
            xp_to_next = 100 - xp
            xp_percentage = (xp / 100) * 100 if xp > 0 else 0
            
            # Handle study_streak - can be int or dict
            study_streak = analytics_data.get('study_streak', 0)
            if isinstance(study_streak, dict):
                current_streak = study_streak.get('current_streak', 0)
            else:
                current_streak = study_streak if isinstance(study_streak, int) else 0
            
            # Handle activity_breakdown safely
            activity_breakdown = analytics_data.get('activity_breakdown', {})
            if isinstance(activity_breakdown, dict):
                perfect_sessions = activity_breakdown.get('perfect_sessions', 0)
            else:
                perfect_sessions = 0
            
            # Handle recent_performance safely
            recent_performance = analytics_data.get('recent_performance', [])
            if isinstance(recent_performance, list):
                days_studied = len(recent_performance)
            else:
                days_studied = 0
            
            return {
                'level': level,
                'xp': xp,
                'xp_to_next': xp_to_next,
                'xp_percentage': xp_percentage,
                'streak': current_streak,
                'total_points': total_points,
                'questions_answered': total_questions,
                'days_studied': days_studied,
                'perfect_sessions': perfect_sessions
            }
        except Exception as e:
            logger.warning(f"Error getting user progress from analytics: {e}")
            # Return safe defaults to prevent KeyError
            return {
                'level': 1,
                'xp': 0,
                'xp_to_next': 100,
                'xp_percentage': 0,
                'streak': 0,
                'total_points': 0,
                'questions_answered': 0,
                'days_studied': 0,
                'perfect_sessions': 0
            }
    
    def _get_achievements_summary_from_analytics(self, analytics_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get achievements summary from analytics data."""
        try:
            # Try database first
            db_achievements = self._get_achievements_summary()
            if db_achievements['total_badges'] > 0:
                return db_achievements
            
            # Generate achievements based on analytics data
            total_questions = analytics_data.get('total_questions', 0)
            accuracy = analytics_data.get('overall_accuracy', 0)
            
            badges = []
            if total_questions >= 10:
                badges.append('First Steps')
            if total_questions >= 50:
                badges.append('Getting Started')
            if total_questions >= 100:
                badges.append('Dedicated Learner')
            if accuracy >= 80:
                badges.append('High Achiever')
            if accuracy >= 90:
                badges.append('Expert')
            
            return {
                'total_badges': len(badges),
                'recent_badges': badges[-3:] if len(badges) > 3 else badges,
                'completion_percentage': min(100, (len(badges) / 10) * 100),
                'next_milestone': self._get_next_milestone_from_analytics(analytics_data),
                'all_badges': badges
            }
        except Exception as e:
            logger.warning(f"Error getting achievements from analytics: {e}")
            return self._get_achievements_summary()
    
    def _get_performance_metrics_from_analytics(self, analytics_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get performance metrics from analytics data."""
        try:
            # Try database first
            db_metrics = self._get_performance_metrics()
            if db_metrics.get('total_attempted', 0) > 0:
                return db_metrics
            
            # Use analytics data - handle both old and new formats
            recent_performance = analytics_data.get('recent_performance', [])
            overall_accuracy = analytics_data.get('overall_accuracy', analytics_data.get('accuracy', 0))
            total_attempted = analytics_data.get('total_questions', 0)
            # Handle both 'total_correct' and 'correct_answers' for backward compatibility
            total_correct = analytics_data.get('total_correct', analytics_data.get('correct_answers', 0))
            
            # Calculate trend from recent performance - handle list safely
            if isinstance(recent_performance, list) and len(recent_performance) >= 4:
                first_half = recent_performance[len(recent_performance)//2:]
                second_half = recent_performance[:len(recent_performance)//2]
                
                # Calculate averages safely
                first_accuracy = 0
                if first_half:
                    first_sum = sum(p.get('accuracy', 0) if isinstance(p, dict) else 0 for p in first_half)
                    first_accuracy = first_sum / len(first_half)
                
                second_accuracy = 0
                if second_half:
                    second_sum = sum(p.get('accuracy', 0) if isinstance(p, dict) else 0 for p in second_half)
                    second_accuracy = second_sum / len(second_half)
                
                trend = 'improving' if second_accuracy > first_accuracy + 5 else \
                       'declining' if second_accuracy < first_accuracy - 5 else 'stable'
                trend_change = second_accuracy - first_accuracy
            else:
                trend = 'stable'
                trend_change = 0
            
            performance_level = 'expert' if overall_accuracy >= 90 else \
                              'advanced' if overall_accuracy >= 80 else \
                              'intermediate' if overall_accuracy >= 70 else \
                              'beginner'
            
            # Calculate recent sessions count safely
            recent_sessions_count = len(recent_performance) if isinstance(recent_performance, list) else 0
            
            return {
                'overall_accuracy': round(overall_accuracy, 1),
                'accuracy_trend': trend,
                'performance_level': performance_level,
                'recent_sessions': recent_sessions_count,
                'total_attempted': total_attempted,
                'total_correct': total_correct,
                'trend_change': round(trend_change, 1)
            }
        except Exception as e:
            logger.warning(f"Error getting performance metrics from analytics: {e}")
            # Return safe defaults to prevent KeyError
            return {
                'overall_accuracy': 0.0,
                'accuracy_trend': 'stable',
                'performance_level': 'beginner',
                'recent_sessions': 0,
                'total_attempted': 0,
                'total_correct': 0,
                'trend_change': 0.0
            }
    
    def _get_category_breakdown_from_analytics(self, analytics_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get category breakdown from analytics data."""
        try:
            # Try database first
            db_breakdown = self._get_category_breakdown()
            if db_breakdown:
                return db_breakdown
            
            # Use analytics topic breakdown
            topic_breakdown = analytics_data.get('topic_breakdown', {})
            
            breakdown = []
            for category, accuracy in topic_breakdown.items():
                # Estimate questions based on accuracy (this is approximate)
                estimated_questions = max(5, int(accuracy / 10))  # Rough estimate
                estimated_correct = int(estimated_questions * accuracy / 100)
                
                breakdown.append({
                    'category': category,
                    'attempted': estimated_questions,
                    'correct': estimated_correct,
                    'accuracy': round(accuracy, 1),
                    'accuracy_level': 'good' if accuracy >= 80 else 'average' if accuracy >= 60 else 'poor'
                })
            
            breakdown.sort(key=lambda x: x['accuracy'], reverse=True)
            return breakdown
        except Exception as e:
            logger.warning(f"Error getting category breakdown from analytics: {e}")
            return self._get_category_breakdown()
    
    def _calculate_total_metrics_from_analytics(self, analytics_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate total metrics from analytics data."""
        try:
            # Try database first
            db_metrics = self._calculate_total_metrics()
            if db_metrics.get('total_sessions', 0) > 0:
                return db_metrics
            
            # Use analytics data - handle both old and new formats
            total_sessions = analytics_data.get('total_sessions', 0)
            total_questions = analytics_data.get('total_questions', 0)
            # Handle both 'total_correct' and 'correct_answers' for backward compatibility
            total_correct = analytics_data.get('total_correct', analytics_data.get('correct_answers', 0))
            total_time = analytics_data.get('total_study_time', 0)
            overall_accuracy = analytics_data.get('overall_accuracy', analytics_data.get('accuracy', 0))
            
            # Estimate days active from recent performance - handle list safely
            recent_performance = analytics_data.get('recent_performance', [])
            days_active = 0
            first_session = None
            
            if isinstance(recent_performance, list) and recent_performance:
                try:
                    # Extract unique dates safely
                    dates = set()
                    for p in recent_performance:
                        if isinstance(p, dict) and p.get('date'):
                            date_str = str(p.get('date'))[:10]  # Get first 10 chars (YYYY-MM-DD)
                            if date_str:
                                dates.add(date_str)
                    days_active = len(dates)
                    
                    # Get first session date safely
                    all_dates = [str(p.get('date', '')) for p in recent_performance 
                                if isinstance(p, dict) and p.get('date')]
                    if all_dates:
                        first_session = min(all_dates)[:10]
                except Exception as date_error:
                    logger.warning(f"Error processing recent performance dates: {date_error}")
                    days_active = 0
                    first_session = None
            
            return {
                'total_sessions': total_sessions,
                'total_questions': total_questions,
                'total_correct': total_correct,
                'overall_accuracy': round(overall_accuracy, 1),
                'total_time': total_time,
                'total_time_formatted': self._format_time(total_time),
                'days_active': days_active,
                'first_session': first_session,
                'avg_questions_per_session': round(total_questions / total_sessions, 1) if total_sessions > 0 else 0
            }
        except Exception as e:
            logger.warning(f"Error calculating total metrics from analytics: {e}")
            # Return safe defaults to prevent KeyError
            return {
                'total_sessions': 0,
                'total_questions': 0,
                'total_correct': 0,
                'overall_accuracy': 0.0,
                'total_time': 0,
                'total_time_formatted': '0s',
                'days_active': 0,
                'first_session': None,
                'avg_questions_per_session': 0.0
            }
    
    def _get_next_milestone_from_analytics(self, analytics_data: Dict[str, Any]) -> str:
        """Get next milestone from analytics data."""
        try:
            total_questions = analytics_data.get('total_questions', 0)
            
            if total_questions < 10:
                return "Answer 10 Questions"
            elif total_questions < 50:
                return "Answer 50 Questions"
            elif total_questions < 100:
                return "Answer 100 Questions"
            elif total_questions < 500:
                return "Answer 500 Questions"
            else:
                return "Master Level Achieved"
        except Exception:
            return "First Quiz"

# Global instance for easy access
_dashboard_service = None

def get_dashboard_service(user_id: str = 'anonymous') -> DashboardService:
    """Get or create dashboard service instance."""
    global _dashboard_service
    if _dashboard_service is None or _dashboard_service.user_id != user_id:
        _dashboard_service = DashboardService(user_id)
    return _dashboard_service

def validate_dashboard_data(dashboard_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate dashboard data integrity and consistency.
    
    Returns:
        Tuple of (is_valid, list_of_issues)
    """
    issues = []
    
    try:
        # Check required top-level keys
        required_keys = ['today', 'week', 'month', 'user_progress', 'total_metrics', 'last_updated']
        for key in required_keys:
            if key not in dashboard_data:
                issues.append(f"Missing required key: {key}")
        
        # Validate numerical consistency
        total_metrics = dashboard_data.get('total_metrics', {})
        user_progress = dashboard_data.get('user_progress', {})
        
        # Check that total questions >= total correct
        total_questions = total_metrics.get('total_questions', 0)
        total_correct = total_metrics.get('total_correct', 0)
        if total_correct > total_questions:
            issues.append(f"Total correct ({total_correct}) cannot exceed total questions ({total_questions})")
        
        # Check accuracy calculation
        if total_questions > 0:
            calculated_accuracy = (total_correct / total_questions) * 100
            reported_accuracy = total_metrics.get('overall_accuracy', 0)
            if abs(calculated_accuracy - reported_accuracy) > 1.0:  # Allow 1% tolerance
                issues.append(f"Accuracy mismatch: calculated {calculated_accuracy:.1f}%, reported {reported_accuracy:.1f}%")
        
        # Validate progress metrics
        level = user_progress.get('level', 0)
        xp = user_progress.get('xp', 0)
        if level < 1:
            issues.append(f"Invalid level: {level} (must be >= 1)")
        if xp < 0 or xp >= 100:
            issues.append(f"Invalid XP: {xp} (must be 0-99)")
        
        # Check time consistency
        total_time = total_metrics.get('total_time', 0)
        if total_time < 0:
            issues.append(f"Invalid total time: {total_time} (cannot be negative)")
        
        # Validate session data
        total_sessions = total_metrics.get('total_sessions', 0)
        if total_sessions < 0:
            issues.append(f"Invalid session count: {total_sessions} (cannot be negative)")
        
        # Check category breakdown data integrity
        category_breakdown = dashboard_data.get('category_breakdown', [])
        for i, category in enumerate(category_breakdown):
            if not isinstance(category, dict):
                issues.append(f"Category {i} is not a dictionary")
                continue
            
            attempted = category.get('attempted', 0)
            correct = category.get('correct', 0)
            if correct > attempted:
                issues.append(f"Category '{category.get('category', f'#{i}')}': correct ({correct}) > attempted ({attempted})")
        
        # Validate recent sessions data
        recent_sessions = dashboard_data.get('recent_sessions', [])
        for i, session in enumerate(recent_sessions):
            if not isinstance(session, dict):
                issues.append(f"Recent session {i} is not a dictionary")
                continue
            
            session_attempted = session.get('questions_attempted', 0)
            session_correct = session.get('questions_correct', 0)
            if session_correct > session_attempted:
                issues.append(f"Session {i}: correct ({session_correct}) > attempted ({session_attempted})")
        
        return len(issues) == 0, issues
        
    except Exception as e:
        issues.append(f"Validation error: {str(e)}")
        return False, issues