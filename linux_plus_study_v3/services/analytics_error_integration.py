#!/usr/bin/env python3
"""
Integration patch for Error Tracking and Analytics

This module integrates the error tracking system with the existing web application.
"""

import logging
from flask import Flask
from typing import Optional

from services.error_tracking_middleware import ErrorTrackingMiddleware
from services.analytics_integration import WebAnalyticsTracker

logger = logging.getLogger(__name__)

def setup_enhanced_analytics_and_error_tracking(app: Flask) -> None:
    """
    Set up enhanced analytics and error tracking for the Flask application.
    
    This integrates both the new WebAnalyticsTracker and ErrorTrackingMiddleware
    with the existing application.
    """
    try:
        # Initialize WebAnalyticsTracker for enhanced analytics
        analytics_tracker = WebAnalyticsTracker(app)
        logger.info("✓ Enhanced analytics tracking initialized")
        
        # Initialize ErrorTrackingMiddleware for comprehensive error tracking
        error_middleware = ErrorTrackingMiddleware(app)
        logger.info("✓ Error tracking middleware initialized")
        
        # Log successful setup
        logger.info("✓ Enhanced analytics and error tracking setup complete")
        
    except Exception as e:
        logger.error(f"Failed to setup enhanced analytics and error tracking: {e}")
        # Don't let this failure break the application
        
def setup_error_logging_integration() -> None:
    """
    Set up integration between existing logging and error tracking.
    """
    try:
        from services.error_tracking import error_tracker
        
        # Create a custom log handler that feeds into error tracking
        class ErrorTrackingLogHandler(logging.Handler):
            def emit(self, record):
                if record.levelno >= logging.ERROR:
                    # Extract error information from log record
                    error_message = record.getMessage()
                    
                    # Determine error type based on logger name
                    logger_name = record.name
                    if 'database' in logger_name:
                        error_type = 'database_error'
                    elif 'analytics' in logger_name:
                        error_type = 'analytics_error'
                    elif 'vm' in logger_name or 'virtual' in logger_name:
                        error_type = 'vm_error'
                    else:
                        error_type = 'application_error'
                    
                    # Track the error
                    try:
                        error_tracker.track_error(
                            error_type=error_type,
                            error_message=error_message,
                            additional_context={
                                'logger_name': logger_name,
                                'log_level': record.levelname,
                                'module': record.module if hasattr(record, 'module') else 'unknown',
                                'function': record.funcName if hasattr(record, 'funcName') else 'unknown'
                            }
                        )
                    except Exception:
                        # Don't let error tracking itself cause issues
                        pass
        
        # Add the handler to the root logger
        error_handler = ErrorTrackingLogHandler()
        error_handler.setLevel(logging.ERROR)
        
        # Add to specific loggers that we know have errors
        important_loggers = [
            'utils.database',
            'services.analytics_integration',
            'services.analytics_service',
            'views.web_view',
            'controllers.quiz_controller',
            'controllers.stats_controller'
        ]
        
        for logger_name in important_loggers:
            target_logger = logging.getLogger(logger_name)
            target_logger.addHandler(error_handler)
        
        logger.info("✓ Error logging integration setup complete")
        
    except Exception as e:
        logger.error(f"Failed to setup error logging integration: {e}")

def add_analytics_dashboard_routes(app: Flask) -> None:
    """Add routes for viewing analytics and error data."""
    
    @app.route('/api/analytics/errors')
    def get_error_analytics():
        """Get error analytics data."""
        try:
            from models.analytics import AnalyticsService
            from utils.database import get_db_session
            
            with get_db_session() as db_session:
                analytics_service = AnalyticsService(db_session)
                
                # Get error-related analytics
                error_analytics = db_session.query(analytics_service.db.query.__self__).filter(
                    analytics_service.db.query.__self__.activity_type == 'error_tracking'
                ).all()
                
                error_summary = {
                    'total_error_sessions': len(error_analytics),
                    'total_errors': sum(a.error_count or 0 for a in error_analytics),
                    'error_types': {},
                    'recent_errors': []
                }
                
                for analytics in error_analytics:
                    error_type = analytics.activity_subtype or 'unknown'
                    error_summary['error_types'][error_type] = error_summary['error_types'].get(error_type, 0) + (analytics.error_count or 0)
                    
                    if analytics.custom_metrics and 'error_batch' in analytics.custom_metrics:
                        error_batch = analytics.custom_metrics['error_batch']
                        error_summary['recent_errors'].extend(error_batch.get('errors', [])[:3])  # Add up to 3 recent errors
                
                # Limit recent errors to most recent 10
                error_summary['recent_errors'] = error_summary['recent_errors'][-10:]
                
                return {'success': True, 'data': error_summary}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    # Don't add the analytics_dashboard route here to avoid conflicts
    # Let the existing web_view.py handle the main analytics dashboard
    
    logger.info("✓ Analytics error tracking routes added")

def integrate_with_existing_web_app(web_app_instance) -> None:
    """
    Integrate error tracking and enhanced analytics with an existing web app instance.
    
    Args:
        web_app_instance: The LinuxPlusStudyWeb instance
    """
    try:
        # Setup enhanced analytics and error tracking
        setup_enhanced_analytics_and_error_tracking(web_app_instance.app)
        
        # Setup error logging integration
        setup_error_logging_integration()
        
        # Add analytics dashboard routes
        add_analytics_dashboard_routes(web_app_instance.app)
        
        logger.info("✓ Successfully integrated error tracking and analytics with existing web app")
        
    except Exception as e:
        logger.error(f"Failed to integrate with existing web app: {e}")
