#!/usr/bin/env python3
"""
Error Tracking Middleware

Integrates error tracking with Flask application to automatically capture
and track errors in analytics.
"""

import logging
from functools import wraps
from flask import Flask, request, g
from typing import Callable, Any
import traceback

from services.error_tracking import error_tracker

logger = logging.getLogger(__name__)

class ErrorTrackingMiddleware:
    """Middleware to automatically track errors in Flask applications."""
    
    def __init__(self, app: Flask = None):
        self.app = app
        if app:
            self.init_app(app)
    
    def init_app(self, app: Flask) -> None:
        """Initialize error tracking middleware for Flask app."""
        # Set up error handlers
        app.errorhandler(404)(self.handle_404_error)
        app.errorhandler(500)(self.handle_500_error)
        app.errorhandler(Exception)(self.handle_general_error)
        
        # Hook into database error logging
        self._setup_database_error_logging()
        
        # Hook into analytics error logging
        self._setup_analytics_error_logging()
    
    def handle_404_error(self, error):
        """Handle 404 Not Found errors."""
        error_tracker.track_http_error(
            status_code=404,
            endpoint=request.endpoint or request.path,
            error_message=f"Page not found: {request.path}"
        )
        
        # Return the default 404 response
        return f"Page not found: {request.path}", 404
    
    def handle_500_error(self, error):
        """Handle 500 Internal Server errors."""
        error_tracker.track_http_error(
            status_code=500,
            endpoint=request.endpoint or request.path,
            error_message=f"Internal server error: {str(error)}"
        )
        
        logger.error(f"500 error on {request.path}: {error}")
        return "Internal server error", 500
    
    def handle_general_error(self, error):
        """Handle general application errors."""
        # Skip analytics errors to avoid infinite loops
        if 'analytics' not in str(error).lower():
            error_tracker.track_error(
                error_type='application_error',
                error_message=str(error),
                exception=error,
                additional_context={
                    'endpoint': request.endpoint or request.path,
                    'method': request.method,
                    'url': request.url
                }
            )
        
        logger.error(f"Unhandled error on {request.path}: {error}")
        logger.error(traceback.format_exc())
        
        return "An error occurred", 500
    
    def _setup_database_error_logging(self):
        """Set up logging for database errors."""
        # Get the database logger and add a handler to track errors
        db_logger = logging.getLogger('utils.database')
        
        class DatabaseErrorHandler(logging.Handler):
            def emit(self, record):
                if record.levelno >= logging.ERROR:
                    error_tracker.track_database_error(
                        sql_query=getattr(record, 'sql_query', 'unknown'),
                        error_message=record.getMessage(),
                        parameters=getattr(record, 'parameters', None)
                    )
        
        db_handler = DatabaseErrorHandler()
        db_logger.addHandler(db_handler)
    
    def _setup_analytics_error_logging(self):
        """Set up logging for analytics errors."""
        analytics_logger = logging.getLogger('services.analytics_integration')
        
        class AnalyticsErrorHandler(logging.Handler):
            def emit(self, record):
                if record.levelno >= logging.ERROR:
                    error_tracker.track_analytics_error(
                        operation=getattr(record, 'operation', 'unknown'),
                        error_message=record.getMessage()
                    )
        
        analytics_handler = AnalyticsErrorHandler()
        analytics_logger.addHandler(analytics_handler)

def track_errors_decorator(error_type: str = 'function_error'):
    """Decorator to automatically track errors in functions."""
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_tracker.track_error(
                    error_type=error_type,
                    error_message=f"Error in {func.__name__}: {str(e)}",
                    exception=e,
                    additional_context={
                        'function_name': func.__name__,
                        'module': func.__module__,
                        'args_count': len(args),
                        'kwargs_keys': list(kwargs.keys())
                    }
                )
                raise
        return wrapper
    return decorator

# Convenience decorator for database operations
def track_database_errors(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator specifically for database operations."""
    return track_errors_decorator('database_operation')(func)

# Convenience decorator for analytics operations
def track_analytics_errors(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator specifically for analytics operations."""
    return track_errors_decorator('analytics_operation')(func)

# Convenience decorator for VM operations
def track_vm_errors(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator specifically for VM operations."""
    return track_errors_decorator('vm_operation')(func)
