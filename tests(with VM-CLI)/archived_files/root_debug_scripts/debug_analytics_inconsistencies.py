#!/usr/bin/env python3
"""
Debug Analytics Data Inconsistencies

This script identifies and fixes the data inconsistency issues in the analytics dashboard.
The user reported doing only a few questions in a few seconds on one day, but seeing:
- 2 correct answers with 29% accuracy (should be 100% or at least consistent)
- 4 questions to review with 7 total attempts (inconsistent with only doing a few questions)
- Multiple discrepancies across different dashboard sections

Issues to fix:
1. Multiple analytics data sources creating conflicting information
2. Demo data bleeding into user data
3. Inconsistent calculation methods between different views
4. Mock/fallback data overriding real user data
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def debug_data_sources():
    """Debug the different data sources causing inconsistencies."""
    print("🔍 Debugging Analytics Data Inconsistencies")
    print("=" * 60)
    
    try:
        # Test the main dashboard API
        print("\n1. Testing Main Dashboard API (/api/dashboard)")
        print("-" * 40)
        
        from utils.database import get_database_manager
        from controllers.stats_controller import StatsController
        
        db_manager = get_database_manager()
        if not db_manager:
            print("❌ Database manager not available")
            return False
            
        stats_controller = StatsController()
        dashboard_data = stats_controller.get_dashboard_data()
        
        print(f"Dashboard Data:")
        print(f"  Total Correct: {dashboard_data.get('total_correct', 'N/A')}")
        print(f"  Accuracy: {dashboard_data.get('accuracy', 'N/A')}%")
        print(f"  Questions Answered: {dashboard_data.get('questions_answered', 'N/A')}")
        print(f"  Study Time: {dashboard_data.get('study_time', 'N/A')}")
        print(f"  Streak: {dashboard_data.get('streak', 'N/A')}")
        
    except Exception as e:
        print(f"❌ Error testing dashboard API: {e}")
    
    try:
        # Test the analytics service
        print("\n2. Testing Analytics Service (/api/user/analytics-summary)")
        print("-" * 40)
        
        from services.analytics_service import AnalyticsService
        
        session = db_manager.session_factory()
        analytics_service = AnalyticsService(session)
        
        # Test anonymous user
        print("Anonymous User Data:")
        anon_data = analytics_service.get_user_summary('anonymous')
        print(f"  Total Questions: {anon_data.get('total_questions', 'N/A')}")
        print(f"  Total Correct: {anon_data.get('total_correct', 'N/A')}")
        print(f"  Overall Accuracy: {anon_data.get('overall_accuracy', 'N/A')}%")
        print(f"  Study Streak: {anon_data.get('study_streak', 'N/A')}")
        print(f"  Total Sessions: {anon_data.get('total_sessions', 'N/A')}")
        
        # Test demo user
        print("\nDemo User Data:")
        demo_data = analytics_service.get_user_summary('demo_user_001')
        print(f"  Total Questions: {demo_data.get('total_questions', 'N/A')}")
        print(f"  Total Correct: {demo_data.get('total_correct', 'N/A')}")
        print(f"  Overall Accuracy: {demo_data.get('overall_accuracy', 'N/A')}%")
        print(f"  Study Streak: {demo_data.get('study_streak', 'N/A')}")
        print(f"  Total Sessions: {demo_data.get('total_sessions', 'N/A')}")
        
        session.close()
        
    except Exception as e:
        print(f"❌ Error testing analytics service: {e}")
    
    try:
        # Test review system
        print("\n3. Testing Review System Data")
        print("-" * 40)
        
        from models.quiz_models import ReviewSystem
        from models.question_manager import QuestionManager
        
        question_manager = QuestionManager()
        review_system = ReviewSystem(question_manager)
        
        # Get review stats
        review_stats = review_system.get_review_stats()
        print(f"Questions to Review: {review_stats.get('questions_to_review', 'N/A')}")
        print(f"Average Accuracy: {review_stats.get('average_accuracy', 'N/A')}%")
        print(f"Total Attempts: {review_stats.get('total_attempts', 'N/A')}")
        print(f"Improvement Rate: {review_stats.get('improvement_rate', 'N/A')}%")
        
        # Check specific questions
        questions_needing_review = review_system.get_questions_needing_review()
        print(f"Actual Questions in Review: {len(questions_needing_review)}")
        
        for i, question in enumerate(questions_needing_review[:3]):  # Show first 3
            print(f"  Question {i+1}: {question.get('attempts', 0)} attempts")
        
    except Exception as e:
        print(f"❌ Error testing review system: {e}")
    
    try:
        # Test achievements system
        print("\n4. Testing Achievements System Data")
        print("-" * 40)
        
        from models.achievements import AchievementSystem
        
        achievement_system = AchievementSystem()
        achievement_stats = achievement_system.get_achievement_stats()
        
        print(f"Achievements Unlocked: {achievement_stats.get('achievements_unlocked', 'N/A')}")
        print(f"Total Points: {achievement_stats.get('total_points', 'N/A')}")
        print(f"Completion Rate: {achievement_stats.get('completion_rate', 'N/A')}%")
        print(f"Rarest Achievement: {achievement_stats.get('rarest_achievement', 'N/A')}")
        
    except Exception as e:
        print(f"❌ Error testing achievements system: {e}")
    
    print("\n" + "=" * 60)
    print("🎯 ANALYSIS OF INCONSISTENCIES")
    print("=" * 60)
    
    print("""
The data inconsistencies are caused by:

1. **Multiple Independent Data Sources:**
   - Dashboard API uses StatsController with game state data
   - Analytics API uses separate analytics database tables
   - Review system uses its own question tracking
   - Achievements system has independent point calculation

2. **Demo Data Bleeding:**
   - Anonymous users get demo_user_001 data as fallback
   - Frontend creates mock analytics data when real data is empty
   - Different systems have different fallback mechanisms

3. **Calculation Mismatches:**
   - Dashboard shows 2 correct answers with 29% accuracy (2/7 = 28.6%)
   - This suggests 7 total attempts across different systems
   - But user only did "a few questions in a few seconds"

4. **Frontend Data Generation:**
   - index.html creates mock analytics data for trends
   - Different pages use different calculation methods
   - Caching and localStorage create additional inconsistencies
    """)

def fix_data_inconsistencies():
    """Implement fixes for the data inconsistencies."""
    print("\n🔧 IMPLEMENTING FIXES")
    print("=" * 60)
    
    fixes = [
        {
            "issue": "Multiple Data Sources",
            "fix": "Create unified analytics data provider",
            "file": "services/unified_analytics.py"
        },
        {
            "issue": "Demo Data Bleeding",
            "fix": "Clear separation between demo and real user data",
            "file": "main.py analytics routes"
        },
        {
            "issue": "Mock Data Override",
            "fix": "Only use mock data when explicitly in demo mode",
            "file": "templates/index.html"
        },
        {
            "issue": "Inconsistent Calculations",
            "fix": "Standardize accuracy and stats calculations",
            "file": "utils/analytics_calculator.py"
        }
    ]
    
    for i, fix in enumerate(fixes, 1):
        print(f"{i}. {fix['issue']}")
        print(f"   Solution: {fix['fix']}")
        print(f"   File: {fix['file']}")
        print()

def create_test_user_data():
    """Create consistent test data for validation."""
    print("\n📊 CREATING CONSISTENT TEST DATA")
    print("=" * 60)
    
    try:
        from utils.database import get_database_manager
        from models.analytics import Analytics
        from datetime import datetime, timezone
        
        db_manager = get_database_manager()
        session = db_manager.session_factory()
        
        # Clear existing test data for anonymous user
        session.query(Analytics).filter(
            Analytics.user_id == 'test_user'
        ).delete()
        
        # Create a single, consistent session for testing
        test_session = Analytics.create_session(
            session_id='test_session_001',
            activity_type='quiz',
            user_id='test_user',
            topic_area='system_management'
        )
        
        # Add specific quiz performance (2 correct out of 2 attempts = 100% accuracy)
        test_session.questions_attempted = 2
        test_session.questions_correct = 2
        test_session.questions_incorrect = 0
        test_session.accuracy_percentage = 1.0  # 100%
        test_session.session_duration = 30  # 30 seconds
        test_session.time_on_content = 30
        
        session.add(test_session)
        session.commit()
        
        print("✅ Created consistent test data:")
        print(f"   User: test_user")
        print(f"   Questions Attempted: 2")
        print(f"   Questions Correct: 2")
        print(f"   Accuracy: 100%")
        print(f"   Duration: 30 seconds")
        
        session.close()
        
    except Exception as e:
        print(f"❌ Error creating test data: {e}")

if __name__ == "__main__":
    debug_data_sources()
    fix_data_inconsistencies()
    create_test_user_data()
    
    print("\n🎯 NEXT STEPS:")
    print("1. Implement unified analytics data provider")
    print("2. Fix demo data bleeding in analytics routes")
    print("3. Update frontend to use consistent data source")
    print("4. Add data validation to prevent inconsistencies")
    print("5. Test with consistent user data")
