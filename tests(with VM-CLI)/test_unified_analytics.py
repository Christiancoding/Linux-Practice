#!/usr/bin/env python3
"""
Test unified analytics provider to ensure consistent data across all dashboard sections
"""

import sys
import json
import requests
from models.analytics import Analytics
from utils.database import DatabasePoolManager

def test_unified_analytics():
    """Test that unified analytics provides consistent data"""
    print("Testing unified analytics provider...")
    
    # Create test user with some analytics data
    db_manager = DatabasePoolManager()
    
    try:
        with db_manager.get_session() as session:
            # Clean up any existing test data
            existing = session.query(Analytics).filter_by(user_id='test_user').first()
            if existing:
                session.delete(existing)
                session.commit()
            
            # Create test analytics data
            test_analytics = Analytics(
                user_id='test_user',
                total_questions=7,
                correct_answers=2,
                accuracy=28.57,  # 2/7 = 28.57%
                total_study_time=45,  # 45 seconds
                study_streak=1,
                total_sessions=1,
                questions_to_review=4,
                mastery_score=25.0,
                xp_earned=85,
                level=1,
                achievements_unlocked=0
            )
            
            session.add(test_analytics)
            session.commit()
            print("✓ Test analytics data created")
            
            # Test unified analytics provider directly
            from services.unified_analytics import get_unified_analytics
            
            analytics_provider = get_unified_analytics('test_user', session)
            
            # Test dashboard stats
            dashboard_stats = analytics_provider.get_dashboard_stats()
            print(f"Dashboard stats: {dashboard_stats}")
            
            # Test analytics stats
            analytics_stats = analytics_provider.get_analytics_stats()
            print(f"Analytics stats: {analytics_stats}")
            
            # Test review stats
            review_stats = analytics_provider.get_review_stats()
            print(f"Review stats: {review_stats}")
            
            # Test achievement stats
            achievement_stats = analytics_provider.get_achievement_stats()
            print(f"Achievement stats: {achievement_stats}")
            
            # Verify consistency
            print("\n=== Consistency Check ===")
            
            # Check total questions consistency
            dashboard_questions = dashboard_stats['questions_answered']
            analytics_questions = analytics_stats['total_questions']
            review_questions = review_stats['total_attempts']
            achievement_questions = achievement_stats['questions_answered']
            
            print(f"Total questions - Dashboard: {dashboard_questions}, Analytics: {analytics_questions}, Review: {review_questions}, Achievements: {achievement_questions}")
            
            if dashboard_questions == analytics_questions == review_questions == achievement_questions:
                print("✓ Total questions consistent across all sections")
            else:
                print("✗ Total questions inconsistent!")
                
            # Check accuracy consistency
            dashboard_accuracy = dashboard_stats['accuracy']
            analytics_accuracy = analytics_stats['accuracy']
            review_accuracy = review_stats['review_accuracy']
            achievement_accuracy = achievement_stats['accuracy']
            
            print(f"Accuracy - Dashboard: {dashboard_accuracy}%, Analytics: {analytics_accuracy}%, Review: {review_accuracy}%, Achievements: {achievement_accuracy}%")
            
            if dashboard_accuracy == analytics_accuracy == review_accuracy == achievement_accuracy:
                print("✓ Accuracy consistent across all sections")
            else:
                print("✗ Accuracy inconsistent!")
                
            # Check correct answers consistency
            dashboard_correct = dashboard_stats['total_correct']
            analytics_correct = analytics_stats['correct_answers']
            review_correct = review_stats['correct_attempts']
            achievement_correct = achievement_stats['total_correct']
            
            print(f"Correct answers - Dashboard: {dashboard_correct}, Analytics: {analytics_correct}, Review: {review_correct}, Achievements: {achievement_correct}")
            
            if dashboard_correct == analytics_correct == review_correct == achievement_correct:
                print("✓ Correct answers consistent across all sections")
            else:
                print("✗ Correct answers inconsistent!")
                
            print("\n=== Expected Values Check ===")
            print(f"Expected: 7 questions, 2 correct, 28.57% accuracy")
            print(f"Got: {dashboard_questions} questions, {dashboard_correct} correct, {dashboard_accuracy}% accuracy")
            
            if dashboard_questions == 7 and dashboard_correct == 2 and abs(dashboard_accuracy - 28.57) < 0.1:
                print("✓ Values match expected test data")
            else:
                print("✗ Values don't match expected test data")
                
            # Clean up test data
            session.delete(test_analytics)
            session.commit()
            print("✓ Test data cleaned up")
            
    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()

def test_api_consistency():
    """Test that API endpoints return consistent data"""
    print("\n=== Testing API Consistency ===")
    
    try:
        # Test dashboard API
        response = requests.get('http://localhost:5000/api/dashboard')
        if response.status_code == 200:
            dashboard_data = response.json()
            print(f"Dashboard API: {dashboard_data}")
            print("✓ Dashboard API working")
        else:
            print(f"✗ Dashboard API failed: {response.status_code}")
            
    except Exception as e:
        print(f"Error testing API: {e}")

if __name__ == '__main__':
    print("🔍 Testing Unified Analytics Provider")
    print("=====================================")
    
    test_unified_analytics()
    test_api_consistency()
    
    print("\n✅ Test complete!")
