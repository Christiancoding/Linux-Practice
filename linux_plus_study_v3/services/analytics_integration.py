"""
Analytics Integration for Web Application

This module provides integration between the Analytics model and the web application,
including Flask route helpers, middleware, and utility functions.
"""

from flask import request, session, g, Flask, Response
from datetime import datetime, timezone
import uuid
from typing import Optional, Dict, Any, Callable
import json
import logging
import os
import zoneinfo

from models.analytics import Analytics, AnalyticsService
from utils.database import get_db_session

logger = logging.getLogger(__name__)

# Allow disabling analytics via environment variable
_analytics_enabled = os.getenv('ANALYTICS_ENABLED', 'true').lower() == 'true'

class WebAnalyticsTracker:
    """Web application analytics tracking integration."""
    
    app: Optional[Flask]
    
    def __init__(self, app: Optional[Flask] = None):
        self.app = app
        if app:
            self.init_app(app)
    
    def init_app(self, app: Flask) -> None:
        """Initialize analytics tracking for Flask app."""
        app.before_request(self.before_request)
        app.after_request(self.after_request)
        app.teardown_appcontext(self.teardown_analytics)
    
    def before_request(self) -> None:
        """Set up analytics tracking for each request."""
        global _analytics_enabled
        if not _analytics_enabled:
            return
            
        try:
            # Create or get session analytics ID
            if 'analytics_session_id' not in session:
                session['analytics_session_id'] = str(uuid.uuid4())
            
            # Initialize analytics service with proper session handling
            from utils.database import get_database_manager
            db_manager = get_database_manager()
            if db_manager and db_manager.session_factory:
                g.analytics_db_session = db_manager.session_factory()
            else:
                g.analytics_db_session = None
            g.analytics_session_id = session['analytics_session_id']
            g.request_start_time = datetime.now(zoneinfo.ZoneInfo("America/Chicago"))
        except Exception as e:
            logger.warning(f"Could not initialize analytics session: {e}")
            # Disable analytics for this session
            _analytics_enabled = False
    
    def after_request(self, response: Response) -> Response:
        """Process analytics after request completion."""
        global _analytics_enabled
        if not _analytics_enabled:
            return response
            
        try:
            if hasattr(g, 'analytics_db_session') and hasattr(g, 'current_analytics') and g.current_analytics:
                # Calculate page load time
                if hasattr(g, 'request_start_time'):
                    load_time = (datetime.now(zoneinfo.ZoneInfo("America/Chicago")) - g.request_start_time).total_seconds() * 1000
                    g.current_analytics.page_load_time = load_time
                
                # Track response status
                if response.status_code >= 400:
                    g.current_analytics.record_error(f"http_{response.status_code}")
                
                # Ensure the analytics object is properly saved
                try:
                    g.analytics_db_session.commit()
                except Exception as commit_error:
                    logger.warning(f"Could not commit analytics session: {commit_error}")
                    g.analytics_db_session.rollback()
        except Exception as e:
            logger.warning(f"Non-critical error in after_request analytics: {e}")
        
        return response
    
    def teardown_analytics(self, exception: Optional[BaseException]) -> None:
        """Clean up analytics session."""
        global _analytics_enabled
        if not _analytics_enabled:
            return
            
        try:
            # Properly close the analytics session
            if hasattr(g, 'analytics_db_session') and g.analytics_db_session:
                try:
                    if exception:
                        g.analytics_db_session.rollback()
                    else:
                        g.analytics_db_session.commit()
                except Exception as cleanup_error:
                    logger.warning(f"Error during analytics session cleanup: {cleanup_error}")
                finally:
                    g.analytics_db_session.close()
        except Exception as e:
            logger.warning(f"Non-critical error in teardown_analytics: {e}")

def track_activity(activity_type: str, **kwargs: Any) -> Optional[Analytics]:
    """Track a new activity session."""
    try:
        session_id = getattr(g, 'analytics_session_id', str(uuid.uuid4()))
        
        # Get user ID from session or request
        user_id = session.get('user_id') or request.headers.get('X-User-ID')
        
        # Extract browser and device info
        user_agent = request.headers.get('User-Agent', '')
        device_type = 'mobile' if any(mobile in user_agent.lower() 
                                    for mobile in ['mobile', 'android', 'iphone']) else 'desktop'
        
        # Use the session from Flask's g object if available
        if hasattr(g, 'analytics_db_session') and g.analytics_db_session:
            db_session = g.analytics_db_session
            analytics_service = AnalyticsService(db_session)
            
            # Create analytics session
            analytics = analytics_service.create_session_analytics(
                session_id=session_id,
                activity_type=activity_type,
                user_id=user_id,
                browser_info=user_agent[:255],
                device_type=device_type,
                **kwargs
            )
            
            # Store in global context for request
            g.current_analytics = analytics
            
            return analytics
        else:
            # Fall back to using context manager if no session available
            with get_db_session() as db_session:
                analytics_service = AnalyticsService(db_session)
                
                # Create analytics session
                analytics = analytics_service.create_session_analytics(
                    session_id=session_id,
                    activity_type=activity_type,
                    user_id=user_id,
                    browser_info=user_agent[:255],
                    device_type=device_type,
                    **kwargs
                )
                
                # Store in global context for request
                g.current_analytics = analytics
                
                return analytics
    except Exception as e:
        logger.error(f"Error tracking activity: {e}")
        return None

def track_quiz_start(topic_area: Optional[str] = None, difficulty_level: Optional[str] = None) -> Optional[Analytics]:
    """Track the start of a quiz session."""
    return track_activity(
        activity_type='quiz',
        topic_area=topic_area,
        difficulty_level=difficulty_level
    )

def track_quiz_question(correct: bool, time_taken: Optional[float] = None) -> None:
    """Track a quiz question answer."""
    try:
        if hasattr(g, 'current_analytics') and g.current_analytics:
            g.current_analytics.update_quiz_performance(correct, time_taken)
    except Exception as e:
        logger.error(f"Error tracking quiz question: {e}")


def track_vm_session(topic_area: Optional[str] = None) -> Optional[Analytics]:
    """Track a VM lab session."""
    analytics = track_activity(
        activity_type='vm_lab',
        topic_area=topic_area
    )
    if analytics:
        analytics.start_vm_session()
    return analytics

def track_cli_playground() -> Optional[Analytics]:
    """Track CLI playground usage."""
    analytics = track_activity(activity_type='cli_playground')
    if analytics:
        analytics.update_cli_usage()
    return analytics

def track_page_view(page_name: str) -> None:
    """Track a page view."""
    global _analytics_enabled
    if not _analytics_enabled:
        return
        
    try:
        if hasattr(g, 'current_analytics') and g.current_analytics:
            # Ensure the analytics object is bound to a session
            if hasattr(g, 'analytics_db_session') and g.analytics_db_session:
                # Refresh the object to ensure it's properly bound
                try:
                    # Check if object is already bound to avoid DetachedInstanceError
                    if not hasattr(g.current_analytics, '_sa_instance_state') or g.current_analytics._sa_instance_state.session is None:
                        g.analytics_db_session.add(g.current_analytics)
                    
                    g.current_analytics.increment_page_view(page_name)
                    g.analytics_db_session.commit()
                except Exception as refresh_error:
                    logger.warning(f"Could not manage analytics session: {refresh_error}")
                    # Silently continue without analytics
            else:
                # No active session, try to create new one but don't fail if it doesn't work
                try:
                    track_activity(activity_type='study', activity_subtype='page_view')
                    if hasattr(g, 'current_analytics') and g.current_analytics:
                        g.current_analytics.increment_page_view(page_name)
                except Exception:
                    pass  # Silently continue without analytics
        else:
            # Create new session for page view but don't fail if it doesn't work
            try:
                track_activity(activity_type='study', activity_subtype='page_view')
                if hasattr(g, 'current_analytics') and g.current_analytics:
                    g.current_analytics.increment_page_view(page_name)
            except Exception:
                pass  # Silently continue without analytics
    except Exception as e:
        logger.warning(f"Analytics tracking disabled due to error: {e}")
        # Disable analytics for the rest of the session
        _analytics_enabled = False

def track_vm_command(command: str, execution_time: Optional[float] = None) -> None:
    """Track VM command execution."""
    try:
        if hasattr(g, 'current_analytics') and g.current_analytics:
            g.current_analytics.add_vm_command(execution_time)
            # Track specific command usage
            g.current_analytics.update_feature_usage(f"vm_command_{command.split()[0]}")
    except Exception as e:
        logger.error(f"Error tracking VM command: {e}")

def track_achievement(achievement_id: str) -> None:
    """Track achievement unlock."""
    try:
        if hasattr(g, 'current_analytics') and g.current_analytics:
            g.current_analytics.record_achievement(achievement_id)
    except Exception as e:
        logger.error(f"Error tracking achievement: {e}")

def track_help_request(help_type: Optional[str] = None) -> None:
    """Track help request."""
    try:
        if hasattr(g, 'current_analytics') and g.current_analytics:
            g.current_analytics.record_help_request(help_type)
    except Exception as e:
        logger.error(f"Error tracking help request: {e}")

def track_hint_usage(hint_type: Optional[str] = None) -> None:
    """Track hint usage."""
    try:
        if hasattr(g, 'current_analytics') and g.current_analytics:
            g.current_analytics.record_hint_usage(hint_type)
    except Exception as e:
        logger.error(f"Error tracking hint usage: {e}")

def end_current_session() -> None:
    """End the current analytics session."""
    try:
        if hasattr(g, 'current_analytics') and g.current_analytics:
            g.current_analytics.end_session()
            # Session will be committed by the context manager
    except Exception as e:
        logger.error(f"Error ending analytics session: {e}")

def get_user_analytics_summary(user_id: Optional[str] = None) -> Dict[str, Any]:
    """Get analytics summary for current or specified user."""
    try:
        if not user_id:
            user_id = session.get('user_id')
        
        if not user_id:
            return {'error': 'No user ID available'}
        
        with get_db_session() as db_session:
            analytics_service = AnalyticsService(db_session)
            return analytics_service.get_user_summary(user_id)
    except Exception as e:
        logger.error(f"Error getting user analytics summary: {e}")
        return {'error': str(e)}

def get_global_analytics() -> Dict[str, Any]:
    """Get global application analytics."""
    try:
        with get_db_session() as db_session:
            analytics_service = AnalyticsService(db_session)
            return analytics_service.get_global_statistics()
    except Exception as e:
        logger.error(f"Error getting global analytics: {e}")
        return {'error': str(e)}

# Decorator for automatic activity tracking
def track_route_activity(activity_type: str, **analytics_kwargs: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to automatically track route activities."""
    def decorator(f: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Start tracking
            track_activity(activity_type, **analytics_kwargs)
            try:
                result = f(*args, **kwargs)
                return result
            except Exception:
                # Track error
                if hasattr(g, 'current_analytics') and g.current_analytics:
                    g.current_analytics.record_error(f"route_error_{f.__name__}")
                raise
        wrapper.__name__ = f.__name__
        return wrapper
    return decorator

# JavaScript integration helpers
def get_analytics_js_config() -> str:
    """Get JavaScript configuration for client-side analytics."""
    config: Dict[str, Any] = {
        'sessionId': getattr(g, 'analytics_session_id', None),
        'userId': session.get('user_id'),
        'trackingEnabled': True,
        'endpoints': {
            'track_event': '/api/analytics/track',
            'page_view': '/api/analytics/page-view',
            'quiz_answer': '/api/analytics/quiz-answer',
            'vm_command': '/api/analytics/vm-command'
        }
    }
    return json.dumps(config)

# API endpoint helpers for AJAX tracking
def handle_analytics_api_request() -> Dict[str, Any]:
    """Handle AJAX analytics tracking requests."""
    try:
        data = request.get_json()
        event_type = data.get('event_type')
        
        if event_type == 'page_view':
            track_page_view(data.get('page_name', 'unknown'))
        elif event_type == 'quiz_answer':
            track_quiz_question(
                correct=data.get('correct', False),
                time_taken=data.get('time_taken')
            )
        elif event_type == 'vm_command':
            track_vm_command(
                command=data.get('command', ''),
                execution_time=data.get('execution_time')
            )
        elif event_type == 'help_request':
            track_help_request(data.get('help_type'))
        elif event_type == 'hint_usage':
            track_hint_usage(data.get('hint_type'))
        elif event_type == 'feature_usage':
            if hasattr(g, 'current_analytics') and g.current_analytics:
                g.current_analytics.update_feature_usage(
                    data.get('feature_name', ''),
                    data.get('usage_count', 1)
                )
        
        return {'status': 'success'}
    except Exception as e:
        logger.error(f"Error handling analytics API request: {e}")
        return {'status': 'error', 'message': str(e)}
