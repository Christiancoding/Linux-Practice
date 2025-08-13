#!/usr/bin/env python3
"""
Enhanced Error Tracking Service

Captures and tracks various types of errors including database errors,
application exceptions, HTTP errors, and system issues.
"""

import logging
import traceback
import json
import sys
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Union
from flask import g, request, session
import re
import os

from models.analytics import Analytics
# Analytics integration disabled
# from services.analytics_integration import track_activity
from utils.database import get_db_session

logger = logging.getLogger(__name__)

class ErrorTracker:
    """Enhanced error tracking for comprehensive analytics."""
    
    def __init__(self):
        self.error_patterns = {
            'database_error': [
                r'sqlite3\.OperationalError',
                r'no such table',
                r'database.*locked',
                r'constraint.*failed'
            ],
            'session_error': [
                r'Session.*rollback',
                r'DetachedInstanceError',
                r'transaction.*rolled back'
            ],
            'http_error': [
                r'HTTP.*[4-5]\d{2}',
                r'Request.*failed',
                r'Connection.*error'
            ],
            'analytics_error': [
                r'Error tracking',
                r'Analytics.*failed',
                r'Could not.*analytics'
            ],
            'vm_error': [
                r'VM.*error',
                r'Virtual machine',
                r'vm_integration.*not found'
            ],
            'import_error': [
                r'ModuleNotFoundError',
                r'ImportError',
                r'module.*not found'
            ]
        }
    
    def track_error(self, 
                   error_type: str,
                   error_message: str,
                   exception: Optional[Exception] = None,
                   additional_context: Optional[Dict[str, Any]] = None) -> None:
        """
        Track an error occurrence with comprehensive details.
        
        Args:
            error_type: Type/category of error
            error_message: Human-readable error message
            exception: Original exception if available
            additional_context: Extra context information
        """
        try:
            # Extract and classify error details
            error_details = self._extract_error_details(error_type, error_message, exception)
            
            # Add context information
            if additional_context:
                error_details.update(additional_context)
            
            # Track in analytics
            self._record_in_analytics(error_details)
            
            # Log structured error
            self._log_structured_error(error_details)
            
        except Exception as tracking_error:
            # Don't let error tracking itself cause issues
            logger.error(f"Failed to track error: {tracking_error}")
    
    def track_database_error(self, sql_query: str, error_message: str, parameters: Optional[List[Any]] = None) -> None:
        """Track database-specific errors."""
        context = {
            'sql_query': sql_query[:500],  # Truncate long queries
            'sql_parameters': str(parameters)[:200] if parameters else None,
            'database_type': 'sqlite'
        }
        
        self.track_error(
            error_type='database_error',
            error_message=error_message,
            additional_context=context
        )
    
    def track_session_error(self, session_operation: str, error_message: str) -> None:
        """Track session management errors."""
        context = {
            'session_operation': session_operation,
            'session_id': getattr(g, 'analytics_session_id', 'unknown'),
            'user_id': session.get('user_id', 'anonymous')
        }
        
        self.track_error(
            error_type='session_error',
            error_message=error_message,
            additional_context=context
        )
    
    def track_http_error(self, status_code: int, endpoint: str, error_message: str) -> None:
        """Track HTTP request errors."""
        context = {
            'status_code': status_code,
            'endpoint': endpoint,
            'method': request.method if request else 'unknown',
            'user_agent': request.headers.get('User-Agent', '') if request else '',
            'ip_address': request.remote_addr if request else ''
        }
        
        self.track_error(
            error_type='http_error',
            error_message=error_message,
            additional_context=context
        )
    
    def track_analytics_error(self, operation: str, error_message: str) -> None:
        """Track analytics system errors."""
        context = {
            'analytics_operation': operation,
            'session_enabled': hasattr(g, 'analytics_session_id'),
            'db_session_available': hasattr(g, 'analytics_db_session')
        }
        
        self.track_error(
            error_type='analytics_error',
            error_message=error_message,
            additional_context=context
        )
    
    def track_vm_error(self, vm_operation: str, error_message: str) -> None:
        """Track virtual machine related errors."""
        context = {
            'vm_operation': vm_operation,
            'vm_available': 'vm_integration module availability check would go here'
        }
        
        self.track_error(
            error_type='vm_error',
            error_message=error_message,
            additional_context=context
        )
    
    def process_log_line(self, log_line: str) -> None:
        """Process a log line and extract error information."""
        # Skip if not an error line
        if not any(level in log_line for level in ['ERROR', 'WARNING', 'CRITICAL']):
            return
        
        # Extract error type based on patterns
        error_type = self._classify_error(log_line)
        
        # Extract timestamp if present
        timestamp_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', log_line)
        timestamp = timestamp_match.group(1) if timestamp_match else None
        
        # Extract logger name
        logger_match = re.search(r' - ([^-]+) - ', log_line)
        logger_name = logger_match.group(1).strip() if logger_match else 'unknown'
        
        # Track the error
        context = {
            'log_timestamp': timestamp,
            'logger_name': logger_name,
            'log_line': log_line[:1000]  # Truncate very long lines
        }
        
        self.track_error(
            error_type=error_type,
            error_message=log_line.split(' - ')[-1] if ' - ' in log_line else log_line,
            additional_context=context
        )
    
    def _extract_error_details(self, error_type: str, error_message: str, exception: Optional[Exception]) -> Dict[str, Any]:
        """Extract comprehensive error details."""
        details = {
            'error_type': error_type,
            'error_message': error_message[:1000],  # Truncate long messages
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'request_url': request.url if request else None,
            'request_method': request.method if request else None,
            'user_id': session.get('user_id') if session else None,
            'session_id': getattr(g, 'analytics_session_id', None) if hasattr(g, 'analytics_session_id') else None
        }
        
        if exception:
            details.update({
                'exception_type': type(exception).__name__,
                'exception_args': str(exception.args),
                'traceback': traceback.format_exc()[:2000]  # Truncate long tracebacks
            })
        
        return details
    
    def _classify_error(self, log_line: str) -> str:
        """Classify error based on log content."""
        log_lower = log_line.lower()
        
        for error_type, patterns in self.error_patterns.items():
            for pattern in patterns:
                if re.search(pattern, log_line, re.IGNORECASE):
                    return error_type
        
        return 'general_error'
    
    def _record_in_analytics(self, error_details: Dict[str, Any]) -> None:
        """Record error tracking information in analytics database."""
        try:
            # Generate a unique session ID for error tracking
            import uuid
            session_id = f"error_session_{uuid.uuid4().hex[:8]}"
            
            # Get the current user or use a default
            user_id = error_details.get('user_id') or 'system'
            
            # Prepare analytics data focused on error tracking
            analytics_data = {
                'user_id': user_id,
                'session_id': session_id,
                'session_start': datetime.now(),
                'activity_type': 'error_tracking',
                'activity_subtype': error_details.get('error_type', 'unknown_error'),
                'error_count': 1,
                'custom_metrics': json.dumps({
                    'error_batch': {
                        'session_id': session_id,
                        'timestamp': error_details.get('timestamp', datetime.now().isoformat()),
                        'error_count': 1,
                        'errors': [{
                            'message': error_details.get('error_message', 'Unknown error'),
                            'type': error_details.get('error_type', 'unknown'),
                            'context': error_details.get('additional_context', {}),
                            'stack_trace': error_details.get('stack_trace', ''),
                            'request_info': {
                                'url': error_details.get('request_url'),
                                'method': error_details.get('request_method'),
                                'user_agent': error_details.get('user_agent')
                            }
                        }]
                    }
                })
            }
            
            # Use a simplified database approach to avoid recursion
            from utils.database import get_db_connection
            
            # Create analytics entry without triggering error handlers
            import sqlite3
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Insert directly into analytics table
            cursor.execute("""
                INSERT INTO analytics (
                    user_id, session_id, session_start, activity_type, activity_subtype, 
                    error_count, custom_metrics, created_at, updated_at,
                    questions_attempted, questions_correct, questions_incorrect
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                analytics_data['user_id'],
                analytics_data['session_id'], 
                analytics_data['session_start'].isoformat(),
                analytics_data['activity_type'],
                analytics_data['activity_subtype'],
                analytics_data['error_count'],
                analytics_data['custom_metrics'],
                datetime.now().isoformat(),
                datetime.now().isoformat(),
                0,  # questions_attempted
                0,  # questions_correct 
                0   # questions_incorrect
            ))
            
            conn.commit()
            conn.close()
                
        except Exception as e:
            # Log to file instead of database to avoid recursion
            try:
                import logging
                logging.basicConfig(
                    filename='logs/error_tracking_fallback.log',
                    level=logging.ERROR,
                    format='%(asctime)s - ERROR TRACKING FALLBACK - %(message)s'
                )
                logger = logging.getLogger('error_tracking_fallback')
                logger.error(f"Failed to record error in analytics: {e}")
                logger.error(f"Original error details: {error_details}")
            except:
                # Last resort - print to console
                print(f"CRITICAL: Error tracking failed completely: {e}")
                print(f"Original error: {error_details}")
                pass
    
    def _log_structured_error(self, error_details: Dict[str, Any]) -> None:
        """Log error in structured format."""
        try:
            # Create structured log entry
            structured_log = {
                'event_type': 'error_tracked',
                'error_details': error_details,
                'environment': {
                    'python_version': sys.version,
                    'platform': os.name
                }
            }
            
            # Log as structured JSON for easier parsing
            logger.error(f"STRUCTURED_ERROR: {json.dumps(structured_log, default=str)}")
            
        except Exception as e:
            # Fallback to simple logging
            logger.error(f"Error tracking failed: {error_details.get('error_message', 'Unknown error')}")

# Global error tracker instance
error_tracker = ErrorTracker()

# Convenience functions
def track_error(error_type: str, error_message: str, exception: Optional[Exception] = None, **context: Any) -> None:
    """Convenience function to track errors."""
    error_tracker.track_error(error_type, error_message, exception, context)

def track_database_error(sql_query: str, error_message: str, parameters: Optional[List[Any]] = None) -> None:
    """Convenience function to track database errors."""
    error_tracker.track_database_error(sql_query, error_message, parameters)

def track_session_error(session_operation: str, error_message: str) -> None:
    """Convenience function to track session errors."""
    error_tracker.track_session_error(session_operation, error_message)

def track_http_error(status_code: int, endpoint: str, error_message: str) -> None:
    """Convenience function to track HTTP errors."""
    error_tracker.track_http_error(status_code, endpoint, error_message)

def track_analytics_error(operation: str, error_message: str) -> None:
    """Convenience function to track analytics errors."""
    error_tracker.track_analytics_error(operation, error_message)

def track_vm_error(vm_operation: str, error_message: str) -> None:
    """Convenience function to track VM errors."""
    error_tracker.track_vm_error(vm_operation, error_message)

def process_log_file(log_file_path: str) -> Dict[str, int]:
    """Process an entire log file and track all errors found."""
    error_counts = {}
    
    try:
        with open(log_file_path, 'r') as f:
            for line in f:
                error_tracker.process_log_line(line.strip())
                
                # Count error types
                error_type = error_tracker._classify_error(line)
                if 'error' in error_type.lower():
                    error_counts[error_type] = error_counts.get(error_type, 0) + 1
    
    except Exception as e:
        logger.error(f"Could not process log file {log_file_path}: {e}")
    
    return error_counts
