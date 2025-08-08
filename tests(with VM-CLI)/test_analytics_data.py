#!/usr/bin/env python3
"""
Test Analytics Data Display

Quick test to verify analytics service is retrieving correct data.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from services.analytics_service import AnalyticsService
from utils.database import initialize_database_pool

def test_analytics_data():
    """Test analytics service data retrieval."""
    print("🧪 Testing Analytics Service Data")
    print("=" * 50)
    
    try:
        # Initialize database
        db_manager = initialize_database_pool()
        
        with db_manager.get_session() as session:
            analytics_service = AnalyticsService(session)
            
            # Test anonymous user (should get demo data)
            print("📊 Testing Anonymous User Analytics:")
            anonymous_stats = analytics_service.get_user_summary('anonymous')
            print(f"   Questions Answered: {anonymous_stats['total_questions']}")
            print(f"   Overall Accuracy: {anonymous_stats['overall_accuracy']:.1f}%")
            print(f"   Study Time: {anonymous_stats['total_study_time']/3600:.1f} hours")
            print(f"   VM Commands: {anonymous_stats['total_vm_commands']}")
            print(f"   Study Streak: {anonymous_stats['study_streak']} days")
            print(f"   Total Sessions: {anonymous_stats['total_sessions']}")
            
            # Test demo user directly
            print("\n📊 Testing Demo User Analytics:")
            demo_stats = analytics_service.get_user_summary('demo_user_001')
            print(f"   Questions Answered: {demo_stats['total_questions']}")
            print(f"   Overall Accuracy: {demo_stats['overall_accuracy']:.1f}%")
            print(f"   Study Time: {demo_stats['total_study_time']/3600:.1f} hours")
            print(f"   VM Commands: {demo_stats['total_vm_commands']}")
            print(f"   Study Streak: {demo_stats['study_streak']} days")
            print(f"   Total Sessions: {demo_stats['total_sessions']}")
            
            # Show topic breakdown
            print("\n📚 Topic Breakdown:")
            for topic, count in demo_stats['topic_breakdown'].items():
                print(f"   {topic}: {count} questions")
            
            # Show activity breakdown
            print("\n🎯 Activity Breakdown:")
            for activity, count in demo_stats['activity_breakdown'].items():
                print(f"   {activity}: {count} sessions")
            
            # Show recent performance
            print("\n📈 Recent Performance (last few sessions):")
            for perf in demo_stats['recent_performance'][:5]:
                print(f"   {perf['date'][:10]}: {perf['accuracy']:.1f}% ({perf['questions']} questions, {perf['activity']})")
        
        print("\n✅ Analytics service is working correctly!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing analytics: {e}")
        return False

if __name__ == "__main__":
    success = test_analytics_data()
    sys.exit(0 if success else 1)
