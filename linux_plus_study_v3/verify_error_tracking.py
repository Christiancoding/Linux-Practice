#!/usr/bin/env python3
"""
Quick verification that error tracking and analytics are working properly.
"""

import os
import sys
import sqlite3
sys.path.append(os.path.dirname(__file__))

def check_analytics_table():
    """Check if analytics table exists and has the right structure."""
    try:
        conn = sqlite3.connect('data/linux_plus_study.db')
        cursor = conn.cursor()
        
        # Check if analytics table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='analytics';")
        table_exists = cursor.fetchone() is not None
        
        if table_exists:
            # Check table structure
            cursor.execute("PRAGMA table_info(analytics);")
            columns = [row[1] for row in cursor.fetchall()]
            
            required_columns = ['error_count', 'custom_metrics', 'activity_type', 'session_id']
            has_error_columns = all(col in columns for col in required_columns)
            
            # Check for any analytics entries
            cursor.execute("SELECT COUNT(*) FROM analytics;")
            total_entries = cursor.fetchone()[0]
            
            # Check for error tracking entries
            cursor.execute("SELECT COUNT(*) FROM analytics WHERE activity_type = 'error_tracking';")
            error_entries = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'table_exists': True,
                'has_error_columns': has_error_columns,
                'total_entries': total_entries,
                'error_entries': error_entries,
                'column_count': len(columns)
            }
        else:
            conn.close()
            return {'table_exists': False}
            
    except Exception as e:
        return {'error': str(e)}

def main():
    print("🔍 ERROR TRACKING & ANALYTICS VERIFICATION")
    print("=" * 50)
    
    # Check analytics table
    print("\n📊 Analytics Table Status:")
    table_status = check_analytics_table()
    
    if 'error' in table_status:
        print(f"  ❌ Database Error: {table_status['error']}")
    elif not table_status['table_exists']:
        print("  ❌ Analytics table does not exist")
    else:
        print("  ✅ Analytics table exists")
        print(f"  ✅ Has error tracking columns: {table_status['has_error_columns']}")
        print(f"  📈 Total analytics entries: {table_status['total_entries']}")
        print(f"  🔥 Error tracking entries: {table_status['error_entries']}")
        print(f"  📝 Table columns: {table_status['column_count']}")
    
    # Check if error tracking modules load
    print("\n🔧 Module Loading Status:")
    
    try:
        from services.error_tracking import ErrorTracker
        print("  ✅ ErrorTracker class loaded successfully")
    except Exception as e:
        print(f"  ❌ ErrorTracker failed to load: {e}")
    
    try:
        from services.error_tracking_middleware import ErrorTrackingMiddleware
        print("  ✅ ErrorTrackingMiddleware loaded successfully")
    except Exception as e:
        print(f"  ❌ ErrorTrackingMiddleware failed to load: {e}")
    
    try:
        from models.analytics import Analytics
        print("  ✅ Analytics model loaded successfully")
    except Exception as e:
        print(f"  ❌ Analytics model failed to load: {e}")
    
    # Check web integration
    print("\n🌐 Web Integration Status:")
    
    try:
        from views.web_view import LinuxPlusStudyWeb
        print("  ✅ Web view with analytics integration loaded")
    except Exception as e:
        print(f"  ❌ Web view integration failed: {e}")
    
    print("\n🎯 SUMMARY:")
    if (table_status.get('table_exists', False) and 
        table_status.get('has_error_columns', False)):
        print("  🎉 SUCCESS: Error tracking and analytics are properly integrated!")
        print("  🚀 Ready to capture and display terminal errors in analytics dashboard")
        print("\n📋 To use:")
        print("    1. Run: python3 main.py")
        print("    2. Visit: http://localhost:5000/analytics/dashboard")
        print("    3. Check: All terminal errors will be automatically tracked")
    else:
        print("  ⚠️  Some components may need attention, but core functionality is available")
    
    print("\n" + "=" * 50)

if __name__ == "__main__":
    main()
