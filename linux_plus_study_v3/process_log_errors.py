#!/usr/bin/env python3
"""
Log Processing Script for Error Analytics

Processes existing log files to extract and track errors in the analytics system.
This will help populate the analytics with historical error data.
"""

import os
import sys
import re
import json
from datetime import datetime, timezone
from typing import Dict, List, Any

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.error_tracking import process_log_file, error_tracker
from models.analytics import Analytics, AnalyticsService
from utils.database import get_db_session

def process_terminal_log_content(log_content: str) -> List[Dict[str, Any]]:
    """Process the terminal log content provided by the user."""
    errors = []
    lines = log_content.split('\n')
    
    for line_num, line in enumerate(lines, 1):
        line = line.strip()
        if not line:
            continue
            
        # Skip non-error lines
        if not any(level in line for level in ['ERROR', 'WARNING', 'CRITICAL']):
            continue
        
        # Extract timestamp
        timestamp_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
        timestamp = timestamp_match.group(1) if timestamp_match else None
        
        # Extract logger name
        logger_match = re.search(r' - ([^-]+) - ', line)
        logger_name = logger_match.group(1).strip() if logger_match else 'unknown'
        
        # Extract error level
        level_match = re.search(r' - (ERROR|WARNING|CRITICAL)', line)
        error_level = level_match.group(1) if level_match else 'ERROR'
        
        # Classify error type
        error_type = classify_error_from_line(line)
        
        # Extract error message
        error_message = line.split(' - ')[-1] if ' - ' in line else line
        
        # Extract SQL details for database errors
        sql_query = None
        sql_parameters = None
        if 'SQL:' in line:
            sql_match = re.search(r'\[SQL: (.+?)\]', line, re.DOTALL)
            if sql_match:
                sql_query = sql_match.group(1)
            
            param_match = re.search(r'\[parameters: (.+?)\]', line)
            if param_match:
                sql_parameters = param_match.group(1)
        
        error_info = {
            'line_number': line_num,
            'timestamp': timestamp,
            'logger_name': logger_name,
            'error_level': error_level,
            'error_type': error_type,
            'error_message': error_message[:500],  # Truncate long messages
            'sql_query': sql_query[:200] if sql_query else None,
            'sql_parameters': sql_parameters,
            'full_line': line[:1000]  # Keep full line for reference
        }
        
        errors.append(error_info)
    
    return errors

def classify_error_from_line(line: str) -> str:
    """Classify error type based on line content."""
    line_lower = line.lower()
    
    if 'no such table' in line_lower or 'sqlite3.operationalerror' in line_lower:
        return 'database_error'
    elif 'session' in line_lower and 'rollback' in line_lower:
        return 'session_error'
    elif 'analytics' in line_lower:
        return 'analytics_error'
    elif 'vm' in line_lower or 'virtual' in line_lower:
        return 'vm_error'
    elif 'import' in line_lower or 'module' in line_lower:
        return 'import_error'
    elif 'http' in line_lower and any(code in line for code in ['404', '500', '400', '403']):
        return 'http_error'
    else:
        return 'general_error'

def create_error_analytics_entries(errors: List[Dict[str, Any]]) -> int:
    """Create analytics entries for extracted errors."""
    entries_created = 0
    
    try:
        with get_db_session() as db_session:
            analytics_service = AnalyticsService(db_session)
            
            # Group errors by type and time
            error_groups = {}
            for error in errors:
                key = (error['error_type'], error['timestamp'][:16] if error['timestamp'] else 'unknown')
                if key not in error_groups:
                    error_groups[key] = []
                error_groups[key].append(error)
            
            # Create analytics entries for each error group
            for (error_type, time_key), grouped_errors in error_groups.items():
                try:
                    # Create analytics session for error tracking
                    session_id = f"error_batch_{time_key}_{error_type}"
                    
                    analytics = analytics_service.create_session_analytics(
                        session_id=session_id,
                        activity_type='error_tracking',
                        activity_subtype=error_type,
                        user_id='system_log_processor'
                    )
                    
                    # Record all errors in this group
                    for error in grouped_errors:
                        analytics.record_error(error_type)
                    
                    # Set custom metrics with detailed error information
                    custom_metrics = {
                        'error_batch': {
                            'error_count': len(grouped_errors),
                            'error_type': error_type,
                            'time_period': time_key,
                            'errors': grouped_errors[:10]  # Limit to first 10 errors
                        },
                        'log_processing': {
                            'processed_at': datetime.now(timezone.utc).isoformat(),
                            'processor': 'log_error_processor'
                        }
                    }
                    
                    analytics.set_custom_metrics(custom_metrics)
                    
                    # Set session end time
                    analytics.end_session()
                    
                    db_session.commit()
                    entries_created += 1
                    
                except Exception as e:
                    print(f"Failed to create analytics entry for {error_type}: {e}")
                    db_session.rollback()
                    continue
    
    except Exception as e:
        print(f"Failed to create error analytics entries: {e}")
    
    return entries_created

def main():
    """Main function to process the user's terminal log content."""
    
    # The user's log content from the request
    log_content = """2025-08-05 18:29:26,102 - utils.database - ERROR: Database session error: (sqlite3.OperationalError) no such table: analytics
[SQL: SELECT analytics.id AS analytics_id, analytics.created_at AS analytics_created_at, analytics.updated_at AS analytics_updated_at, analytics.user_id AS analytics_user_id, analytics.session_id AS analytics_session_id, analytics.session_start AS analytics_session_start, analytics.session_end AS analytics_session_end, analytics.session_duration AS analytics_session_duration, analytics.activity_type AS analytics_activity_type, analytics.activity_subtype AS analytics_activity_subtype, analytics.topic_area AS analytics_topic_area, analytics.difficulty_level AS analytics_difficulty_level, analytics.questions_attempted AS analytics_questions_attempted, analytics.questions_correct AS analytics_questions_correct, analytics.questions_incorrect AS analytics_questions_incorrect, analytics.accuracy_percentage AS analytics_accuracy_percentage, analytics.completion_percentage AS analytics_completion_percentage, analytics.time_per_question AS analytics_time_per_question, analytics.content_pages_viewed AS analytics_content_pages_viewed, analytics.time_on_content AS analytics_time_on_content, analytics.practice_commands_executed AS analytics_practice_commands_executed, analytics.vm_sessions_started AS analytics_vm_sessions_started, analytics.cli_playground_usage AS analytics_cli_playground_usage, analytics.study_streak_days AS analytics_study_streak_days, analytics.return_sessions AS analytics_return_sessions, analytics.help_requests AS analytics_help_requests, analytics.hint_usage AS analytics_hint_usage, analytics.review_sessions AS analytics_review_sessions, analytics.achievements_unlocked AS analytics_achievements_unlocked, analytics.skill_assessments AS analytics_skill_assessments, analytics.learning_goals_met AS analytics_learning_goals_met, analytics.certification_progress AS analytics_certification_progress, analytics.page_load_time AS analytics_page_load_time, analytics.error_count AS analytics_error_count, analytics.feature_usage AS analytics_feature_usage, analytics.browser_info AS analytics_browser_info, analytics.device_type AS analytics_device_type, analytics.vm_uptime AS analytics_vm_uptime, analytics.vm_commands_executed AS analytics_vm_commands_executed, analytics.lab_exercises_completed AS analytics_lab_exercises_completed, analytics.lab_exercises_attempted AS analytics_lab_exercises_attempted, analytics.vm_errors_encountered AS analytics_vm_errors_encountered, analytics.concept_mastery_scores AS analytics_concept_mastery_scores, analytics.retention_test_scores AS analytics_retention_test_scores, analytics.practical_application_success AS analytics_practical_application_success, analytics.active_learning_time AS analytics_active_learning_time, analytics.interaction_frequency AS analytics_interaction_frequency, analytics.focus_score AS analytics_focus_score, analytics.user_feedback_rating AS analytics_user_feedback_rating, analytics.improvement_suggestions AS analytics_improvement_suggestions, analytics.difficulty_rating AS analytics_difficulty_rating, analytics.preferred_learning_style AS analytics_preferred_learning_style, analytics.most_effective_study_method AS analytics_most_effective_study_method, analytics.least_effective_study_method AS analytics_least_effective_study_method, analytics.notes AS analytics_notes, analytics.tags AS analytics_tags, analytics.custom_metrics AS analytics_custom_metrics 
FROM analytics 
WHERE analytics.user_id = ?
 LIMIT ? OFFSET ?]
[parameters: ('anonymous', 100, 0)]
(Background on this error at: https://sqlalche.me/e/20/e3q8)
2025-08-05 18:29:26,102 - services.analytics_integration - ERROR: Error getting user analytics summary: (sqlite3.OperationalError) no such table: analytics
2025-08-05 18:29:26,198 - services.analytics_integration - ERROR: Error tracking activity: (sqlite3.OperationalError) no such table: analytics
2025-08-05 18:29:26,199 - services.analytics_integration - WARNING: Error during analytics session cleanup: This Session's transaction has been rolled back due to a previous exception during flush.
2025-08-05 18:29:45,745 - views.web_view - WARNING - VM management features not available - vm_integration module not found
2025-08-05 18:29:45,745 - views.web_view - WARNING: VM management features not available - vm_integration module not found"""
    
    print("Processing terminal log content for error analytics...")
    
    # Extract errors from log content
    errors = process_terminal_log_content(log_content)
    print(f"Found {len(errors)} error entries")
    
    # Show error summary
    error_types = {}
    for error in errors:
        error_type = error['error_type']
        error_types[error_type] = error_types.get(error_type, 0) + 1
    
    print("\nError Summary:")
    for error_type, count in error_types.items():
        print(f"  {error_type}: {count} occurrences")
    
    # Create analytics entries
    print("\nCreating analytics entries...")
    entries_created = create_error_analytics_entries(errors)
    print(f"Created {entries_created} analytics entries")
    
    # Process existing log files if they exist
    log_dir = "logs"
    if os.path.exists(log_dir):
        print(f"\nProcessing log files in {log_dir}...")
        for log_file in os.listdir(log_dir):
            if log_file.endswith('.log'):
                log_path = os.path.join(log_dir, log_file)
                print(f"Processing {log_file}...")
                error_counts = process_log_file(log_path)
                if error_counts:
                    print(f"  Found errors: {error_counts}")
    
    print("\nError processing complete!")
    
    # Show final analytics summary
    try:
        with get_db_session() as db_session:
            analytics_service = AnalyticsService(db_session)
            
            # Get error-related analytics
            error_analytics = db_session.query(Analytics).filter(
                Analytics.activity_type == 'error_tracking'
            ).all()
            
            if error_analytics:
                print(f"\nTotal error analytics entries: {len(error_analytics)}")
                total_errors = sum(a.error_count or 0 for a in error_analytics)
                print(f"Total errors tracked: {total_errors}")
    except Exception as e:
        print(f"Could not get analytics summary: {e}")

if __name__ == "__main__":
    main()
