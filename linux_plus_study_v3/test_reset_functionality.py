#!/usr/bin/env python3
"""
Test script to verify the reset functionality works correctly
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.simple_analytics import get_analytics_manager

def test_reset_functionality():
    """Test the reset functionality"""
    print("🧪 Testing Reset Functionality")
    print("=" * 40)
    
    analytics = get_analytics_manager()
    test_user = "test_reset_user"
    
    # Add some test data
    print("📝 Adding test data...")
    analytics.update_quiz_results(test_user, True, "Test Topic", "beginner")
    analytics.update_quiz_results(test_user, False, "Test Topic", "beginner")
    analytics.update_quiz_results(test_user, True, "Test Topic", "beginner")
    
    # Check data before reset
    user_data = analytics.get_user_data(test_user)
    print(f"✓ Before reset:")
    print(f"  - Total questions: {user_data.get('total_questions', 0)}")
    print(f"  - Correct answers: {user_data.get('correct_answers', 0)}")
    print(f"  - XP: {user_data.get('xp', 0)}")
    print(f"  - Accuracy: {user_data.get('accuracy', 0):.1f}%")
    
    # Test reset
    print("\n🔄 Testing reset...")
    success = analytics.reset_profile(test_user)
    print(f"✓ Reset success: {success}")
    
    # Check data after reset
    user_data = analytics.get_user_data(test_user)
    print(f"\n✓ After reset:")
    print(f"  - Total questions: {user_data.get('total_questions', 0)}")
    print(f"  - Correct answers: {user_data.get('correct_answers', 0)}")
    print(f"  - XP: {user_data.get('xp', 0)}")
    print(f"  - Accuracy: {user_data.get('accuracy', 0):.1f}%")
    
    # Verify all values are reset
    if (user_data.get('total_questions', 0) == 0 and 
        user_data.get('correct_answers', 0) == 0 and 
        user_data.get('xp', 0) == 0 and 
        user_data.get('accuracy', 0) == 0):
        print("\n✅ Reset functionality working correctly!")
        return True
    else:
        print("\n❌ Reset functionality failed!")
        return False

def test_dashboard_stats():
    """Test dashboard stats consistency"""
    print("\n🧪 Testing Dashboard Stats Consistency")
    print("=" * 40)
    
    analytics = get_analytics_manager()
    test_user = "test_stats_user"
    
    # Add some test data
    print("📝 Adding test data...")
    analytics.update_quiz_results(test_user, True, "Topic A", "beginner")
    analytics.update_quiz_results(test_user, True, "Topic A", "beginner")
    analytics.update_quiz_results(test_user, False, "Topic B", "intermediate")
    analytics.update_quiz_results(test_user, True, "Topic B", "intermediate")
    analytics.update_quiz_results(test_user, True, "Topic B", "intermediate")
    
    # Get dashboard stats
    stats = analytics.get_dashboard_stats(test_user)
    
    print(f"✓ Dashboard Stats:")
    print(f"  - Total questions: {stats['total_questions']}")
    print(f"  - Correct answers: {stats['correct_answers']}")
    print(f"  - XP: {stats['xp']}")
    print(f"  - Accuracy: {stats['accuracy']}%")
    print(f"  - Level: {stats['level']}")
    
    # Verify XP calculation (should be 10 per correct answer)
    expected_xp = stats['correct_answers'] * 10
    if stats['xp'] == expected_xp:
        print(f"✅ XP calculation correct: {stats['xp']} XP for {stats['correct_answers']} correct answers")
    else:
        print(f"❌ XP calculation wrong: Expected {expected_xp}, got {stats['xp']}")
        return False
    
    # Verify accuracy calculation
    expected_accuracy = round((stats['correct_answers'] / stats['total_questions']) * 100, 1)
    if abs(stats['accuracy'] - expected_accuracy) < 0.1:
        print(f"✅ Accuracy calculation correct: {stats['accuracy']}%")
    else:
        print(f"❌ Accuracy calculation wrong: Expected {expected_accuracy}%, got {stats['accuracy']}%")
        return False
    
    print("\n✅ Dashboard stats working correctly!")
    return True

if __name__ == "__main__":
    success1 = test_reset_functionality()
    success2 = test_dashboard_stats()
    
    if success1 and success2:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print("\n💥 Some tests failed!")
        sys.exit(1)
