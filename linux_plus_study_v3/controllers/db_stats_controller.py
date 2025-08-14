#!/usr/bin/env python3
"""
Database-driven Statistics Controller for Linux+ Study Game

Provides accurate statistics using the comprehensive Analytics database
instead of JSON-based history files.
"""

from datetime import datetime, timedelta, date
from typing import Dict, List, Union, Any, Optional, Tuple
from sqlalchemy import func, desc, asc
from sqlalchemy.orm import Session
from utils.database import get_db_session
from models.db_models import Analytics
import logging

logger = logging.getLogger(__name__)


class DatabaseStatsController:
    """Database-driven statistics controller for accurate analytics."""
    
    def __init__(self, user_id: str = "anonymous"):
        """Initialize with user ID for filtering analytics data."""
        self.user_id = user_id
        self._effective_user_id = None  # Will be determined dynamically
    
    def __del__(self):
        """Clean up database session."""
        pass  # Sessions are managed by context manager now
    
    def _get_effective_user_id(self, session: Session) -> str:
        """Determine the effective user ID to use, with fallback to demo user."""
        if self._effective_user_id is not None:
            return self._effective_user_id
        
        # Check if the original user_id has any data
        if self.user_id == "anonymous":
            # Check for anonymous data (null or empty user_id)
            anonymous_count = self._count(
                session,
                (Analytics.user_id == self.user_id) |
                (Analytics.user_id.is_(None)) |
                (Analytics.user_id == ""),
                Analytics.questions_attempted > 0
            )
            
            if anonymous_count > 0:
                self._effective_user_id = self.user_id
                return self.user_id
            
            # No anonymous data, check for demo user
            demo_count = self._count(
                session,
                Analytics.user_id == "demo_user_001",
                Analytics.questions_attempted > 0
            )
            
            if demo_count > 0:
                self._effective_user_id = "demo_user_001"
                logger.info("No data for anonymous user, using demo_user_001")
                return "demo_user_001"
        else:
            # For non-anonymous users, check if they have data
            user_count = self._count(
                session,
                Analytics.user_id == self.user_id,
                Analytics.questions_attempted > 0
            )
            
            if user_count > 0:
                self._effective_user_id = self.user_id
                return self.user_id
        
        # Fallback to original user_id
        self._effective_user_id = self.user_id
        return self.user_id
    
    def get_performance_over_time(self, days: int = 7) -> Dict[str, Any]:
        """Get performance data over specified time period."""
        try:
            with get_db_session() as session:
                # Get effective user ID first (may fallback to demo user)
                effective_user_id = self._get_effective_user_id(session)
                
                end_date = datetime.now().date()
                start_date = end_date - timedelta(days=days - 1)
                
                # Query sessions grouped by date
                query = session.query(
                    func.date(Analytics.session_start).label('date'),
                    func.count(Analytics.id).label('sessions'),
                    func.sum(Analytics.questions_attempted).label('total_questions'),
                    func.sum(Analytics.questions_correct).label('total_correct'),
                    func.avg(Analytics.accuracy_percentage).label('avg_accuracy'),
                    func.sum(Analytics.session_duration).label('total_duration')
                ).filter(
                    func.date(Analytics.session_start) >= start_date,
                    func.date(Analytics.session_start) <= end_date
                )
                
                # Filter by effective user ID
                if effective_user_id == "anonymous":
                    # Include records with null/empty user_id for anonymous
                    query = query.filter((Analytics.user_id == effective_user_id) | (Analytics.user_id.is_(None)) | (Analytics.user_id == ""))
                else:
                    query = query.filter(Analytics.user_id == effective_user_id)
                
                query = query.group_by(func.date(Analytics.session_start)).order_by(asc(func.date(Analytics.session_start)))
                
                results = query.all()
            
            # Create data arrays for all days in range
            labels = []
            questions_data = []
            correct_data = []
            incorrect_data = []
            accuracy_data = []
            
            for i in range(days):
                current_date = start_date + timedelta(days=i)
                labels.append(current_date.strftime('%m/%d'))
                
                # Find data for this date
                day_data = next((r for r in results if r.date == current_date), None)
                
                if day_data:
                    total_q = day_data.total_questions or 0
                    total_c = day_data.total_correct or 0
                    # Normalize accuracy: if None, 0; if >1, assume percentage; else scale
                    avg_acc = day_data.avg_accuracy or 0
                    if avg_acc is None:
                        accuracy = 0
                    elif avg_acc > 1:
                        accuracy = avg_acc
                    else:
                        accuracy = avg_acc * 100
                    
                    questions_data.append(total_q)
                    correct_data.append(total_c)
                    incorrect_data.append(total_q - total_c)
                    accuracy_data.append(round(accuracy, 1))
                else:
                    questions_data.append(0)
                    correct_data.append(0)
                    incorrect_data.append(0)
                    accuracy_data.append(0)
            
            return {
                'labels': labels,
                'questions_attempted': questions_data,
                'questions_correct': correct_data,
                'questions_incorrect': incorrect_data,
                'accuracy_percentage': accuracy_data,
                'total_sessions': sum(1 for r in results if r.sessions > 0),
                'total_questions': sum(questions_data),
                'avg_accuracy': round(sum(accuracy_data) / len([a for a in accuracy_data if a > 0]) if any(a > 0 for a in accuracy_data) else 0, 1)
            }
            
        except Exception as e:
            logger.error(f"Error getting performance over time: {e}")
            return self._empty_performance_data(days)
    
    def get_recent_study_sessions(self, limit: int = 10) -> Dict[str, Any]:
        """Get recent study sessions with accurate data."""
        try:
            with get_db_session() as session:
                # Get effective user ID (may fallback to demo user)
                effective_user_id = self._get_effective_user_id(session)
                
                query = session.query(Analytics).filter(
                    Analytics.questions_attempted > 0
                )
                
                # Filter by effective user ID
                if effective_user_id == "anonymous":
                    query = query.filter((Analytics.user_id == effective_user_id) | (Analytics.user_id.is_(None)) | (Analytics.user_id == ""))
                else:
                    query = query.filter(Analytics.user_id == effective_user_id)
                
                query = query.order_by(desc(Analytics.session_start)).limit(limit)
                
                analytics_sessions = query.all()
                
                session_data = []
                for analytics_session in analytics_sessions:
                    duration_minutes = round((analytics_session.session_duration or 0) / 60, 1)
                    accuracy = round((analytics_session.accuracy_percentage or 0) * 100, 1)
                    
                    session_data.append({
                        'date': analytics_session.session_start.strftime('%m/%d/%Y'),
                        'time': analytics_session.session_start.strftime('%H:%M'),
                        'questions': analytics_session.questions_attempted or 0,
                        'correct': analytics_session.questions_correct or 0,
                        'accuracy': accuracy,
                        'duration': duration_minutes,
                        'topic': analytics_session.topic_area or 'Mixed',
                        'session_id': analytics_session.session_id
                    })
            
            return {
                'sessions': session_data,
                'total_sessions': len(session_data),
                'has_sessions': len(session_data) > 0
            }
            
        except Exception as e:
            logger.error(f"Error getting recent study sessions: {e}")
            return {'sessions': [], 'total_sessions': 0, 'has_sessions': False}
    
    def get_category_performance(self) -> Dict[str, Any]:
        """Get performance breakdown by topic/category."""
        try:
            with get_db_session() as session:
                # Get effective user ID (may fallback to demo user)
                effective_user_id = self._get_effective_user_id(session)
                
                query = session.query(
                    Analytics.topic_area,
                    func.count(Analytics.id).label('sessions'),
                    func.sum(Analytics.questions_attempted).label('total_questions'),
                    func.sum(Analytics.questions_correct).label('total_correct'),
                    func.avg(Analytics.accuracy_percentage).label('avg_accuracy')
                ).filter(
                    Analytics.topic_area.isnot(None),
                    Analytics.questions_attempted > 0
                )
                
                # Filter by effective user ID
                if effective_user_id == "anonymous":
                    query = query.filter((Analytics.user_id == effective_user_id) | (Analytics.user_id.is_(None)) | (Analytics.user_id == ""))
                else:
                    query = query.filter(Analytics.user_id == effective_user_id)
                
                query = query.group_by(Analytics.topic_area).order_by(desc('avg_accuracy'))
                
                results = query.all()
            
            strongest_categories = []
            areas_to_improve = []
            
            for result in results:
                accuracy = round((result.avg_accuracy or 0) * 100, 1)
                category_data = {
                    'category': result.topic_area,
                    'accuracy': accuracy,
                    'questions': result.total_questions or 0,
                    'correct': result.total_correct or 0,
                    'sessions': result.sessions or 0
                }
                
                if accuracy >= 75:
                    strongest_categories.append(category_data)
                elif accuracy < 60:
                    areas_to_improve.append(category_data)
            
            # Sort areas to improve by lowest accuracy first
            areas_to_improve.sort(key=lambda x: x['accuracy'])
            
            return {
                'strongest_categories': strongest_categories[:5],
                'areas_to_improve': areas_to_improve[:5],
                'has_category_data': len(results) > 0,
                'total_categories': len(results)
            }
            
        except Exception as e:
            logger.error(f"Error getting category performance: {e}")
            return {
                'strongest_categories': [],
                'areas_to_improve': [],
                'has_category_data': False,
                'total_categories': 0
            }
    
    def get_overall_statistics(self) -> Dict[str, Any]:
        """Get comprehensive overall statistics."""
        try:
            with get_db_session() as session:
                # Get effective user ID (may fallback to demo user)
                effective_user_id = self._get_effective_user_id(session)
                
                query = session.query(
                    func.count(Analytics.id).label('total_sessions'),
                    func.sum(Analytics.questions_attempted).label('total_questions'),
                    func.sum(Analytics.questions_correct).label('total_correct'),
                    func.sum(Analytics.session_duration).label('total_duration'),
                    func.avg(Analytics.accuracy_percentage).label('avg_accuracy'),
                    func.count(func.distinct(func.date(Analytics.session_start))).label('days_studied')
                ).filter(
                    Analytics.questions_attempted > 0
                )
                
                # Filter by effective user ID
                if effective_user_id == "anonymous":
                    query = query.filter((Analytics.user_id == effective_user_id) | (Analytics.user_id.is_(None)) | (Analytics.user_id == ""))
                else:
                    query = query.filter(Analytics.user_id == effective_user_id)
                
                result = query.first()
            
            if not result or not result.total_sessions:
                return self._empty_overall_stats()
            
            total_questions = result.total_questions or 0
            total_correct = result.total_correct or 0
            overall_accuracy = round((result.avg_accuracy or 0) * 100, 1)
            total_duration_hours = round((result.total_duration or 0) / 3600, 1)
            
            # Calculate study streak
            study_streak = self._calculate_study_streak()
            
            return {
                'total_sessions': result.total_sessions or 0,
                'total_questions': total_questions,
                'total_correct': total_correct,
                'total_incorrect': total_questions - total_correct,
                'overall_accuracy': overall_accuracy,
                'total_study_time_hours': total_duration_hours,
                'days_studied': result.days_studied or 0,
                'current_streak': study_streak,
                'average_session_duration': round((result.total_duration or 0) / max(total_questions, 1) / 60, 1),  # Time per question in minutes
                'questions_per_session': round(total_questions / (result.total_sessions or 1), 1)
            }
            
        except Exception as e:
            logger.error(f"Error getting overall statistics: {e}")
            return self._empty_overall_stats()
    
    def get_filtered_performance(self, date_range: str = "7_days") -> Dict[str, Any]:
        """Get performance data for specific date range."""
        try:
            # Parse date range
            if date_range == "7_days":
                days = 7
            elif date_range == "30_days":
                days = 30
            elif date_range == "90_days":
                days = 90
            elif date_range.startswith("custom_"):
                # Format: custom_YYYY-MM-DD_YYYY-MM-DD
                _, start_str, end_str = date_range.split("_")
                start_date = datetime.strptime(start_str, "%Y-%m-%d").date()
                end_date = datetime.strptime(end_str, "%Y-%m-%d").date()
                days = (end_date - start_date).days + 1
                
                # Override the default calculation for custom range
                return self._get_custom_range_performance(start_date, end_date)
            else:
                days = 7  # Default fallback
            
            return self.get_performance_over_time(days)
            
        except Exception as e:
            logger.error(f"Error getting filtered performance: {e}")
            return self._empty_performance_data(7)
    
    def _get_custom_range_performance(self, start_date: date, end_date: date) -> Dict[str, Any]:
        """Get performance data for custom date range."""
        try:
            with get_db_session() as session:
                # Get effective user ID (may fallback to demo user)
                effective_user_id = self._get_effective_user_id(session)
                
                query = session.query(
                    func.date(Analytics.session_start).label('date'),
                    func.count(Analytics.id).label('sessions'),
                    func.sum(Analytics.questions_attempted).label('total_questions'),
                    func.sum(Analytics.questions_correct).label('total_correct'),
                    func.avg(Analytics.accuracy_percentage).label('avg_accuracy')
                ).filter(
                    func.date(Analytics.session_start) >= start_date,
                    func.date(Analytics.session_start) <= end_date
                )
                
                # Filter by effective user ID
                if effective_user_id == "anonymous":
                    query = query.filter((Analytics.user_id == effective_user_id) | (Analytics.user_id.is_(None)) | (Analytics.user_id == ""))
                else:
                    query = query.filter(Analytics.user_id == effective_user_id)
                
                query = query.group_by(func.date(Analytics.session_start)).order_by(asc(func.date(Analytics.session_start)))
                
                results = query.all()
            
            # Calculate summary data
            total_questions = sum(r.total_questions or 0 for r in results)
            total_correct = sum(r.total_correct or 0 for r in results)
            total_sessions = sum(r.sessions or 0 for r in results)
            avg_accuracy = round(sum((r.avg_accuracy or 0) * 100 for r in results if r.avg_accuracy) / len([r for r in results if r.avg_accuracy]) if results else 0, 1)
            
            # Create labels and data arrays
            labels = []
            questions_data = []
            correct_data = []
            incorrect_data = []
            accuracy_data = []
            
            current_date = start_date
            while current_date <= end_date:
                labels.append(current_date.strftime('%m/%d'))
                
                day_data = next((r for r in results if r.date == current_date), None)
                
                if day_data:
                    total_q = day_data.total_questions or 0
                    total_c = day_data.total_correct or 0
                    accuracy = (day_data.avg_accuracy or 0) * 100
                    
                    questions_data.append(total_q)
                    correct_data.append(total_c)
                    incorrect_data.append(total_q - total_c)
                    accuracy_data.append(round(accuracy, 1))
                else:
                    questions_data.append(0)
                    correct_data.append(0)
                    incorrect_data.append(0)
                    accuracy_data.append(0)
                
                current_date += timedelta(days=1)
            
            return {
                'labels': labels,
                'questions_attempted': questions_data,
                'questions_correct': correct_data,
                'questions_incorrect': incorrect_data,
                'accuracy_percentage': accuracy_data,
                'total_sessions': total_sessions,
                'total_questions': total_questions,
                'avg_accuracy': avg_accuracy
            }
            
        except Exception as e:
            logger.error(f"Error getting custom range performance: {e}")
            return self._empty_performance_data(7)
    
    def _calculate_study_streak(self) -> int:
        """Calculate current study streak from database."""
        try:
            with get_db_session() as session:
                # Get effective user ID (may fallback to demo user)
                effective_user_id = self._get_effective_user_id(session)
                
                # Get distinct study dates
                query = session.query(
                    func.distinct(func.date(Analytics.session_start)).label('study_date')
                ).filter(
                    Analytics.questions_attempted > 0
                )
                
                # Filter by effective user ID
                if effective_user_id == "anonymous":
                    query = query.filter((Analytics.user_id == effective_user_id) | (Analytics.user_id.is_(None)) | (Analytics.user_id == ""))
                else:
                    query = query.filter(Analytics.user_id == effective_user_id)
                
                query = query.order_by(desc(func.date(Analytics.session_start)))
                
                results = query.all()
            
            if not results:
                return 0
            
            study_dates = [r.study_date for r in results]
            current_date = datetime.now().date()
            
            # Check if user studied today or yesterday to start counting
            if study_dates[0] not in [current_date, current_date - timedelta(days=1)]:
                return 0
            
            # Count consecutive days
            streak = 0
            expected_date = study_dates[0]
            
            for study_date in study_dates:
                if study_date == expected_date:
                    streak += 1
                    expected_date -= timedelta(days=1)
                else:
                    break
            
            return streak
            
        except Exception as e:
            logger.error(f"Error calculating study streak: {e}")
            return 0
    
    def _empty_performance_data(self, days: int) -> Dict[str, Any]:
        """Return empty performance data structure."""
        return {
            'labels': [(datetime.now().date() - timedelta(days=days-1-i)).strftime('%m/%d') for i in range(days)],
            'questions_attempted': [0] * days,
            'questions_correct': [0] * days,
            'questions_incorrect': [0] * days,
            'accuracy_percentage': [0] * days,
            'total_sessions': 0,
            'total_questions': 0,
            'avg_accuracy': 0
        }
    
    def _empty_overall_stats(self) -> Dict[str, Any]:
        """Return empty overall statistics."""
        return {
            'total_sessions': 0,
            'total_questions': 0,
            'total_correct': 0,
            'total_incorrect': 0,
            'overall_accuracy': 0,
            'total_study_time_hours': 0,
            'days_studied': 0,
            'current_streak': 0,
            'average_session_duration': 0,
            'questions_per_session': 0
        }
    
    def _count(self, session: Session, *criteria: Any) -> int:
        """Type-safe count wrapper to avoid unknown .count() return type warnings."""
        return int(
            session.query(func.count(Analytics.id))
                   .filter(*criteria)
                   .scalar() or 0
        )