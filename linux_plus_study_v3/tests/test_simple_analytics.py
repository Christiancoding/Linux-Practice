#!/usr/bin/env python3
"""
Test simple JSON-based analytics system
"""

import json
import requests
from services.simple_analytics import get_analytics_manager

def test_simple_analytics():
    """Test the simple analytics system"""
    print("🔍 Testing Simple Analytics System")
    print("===================================")
    
    # Get analytics manager
    analytics = get_analytics_manager()
    
    # Test initial state
    print("\n1. Testing Initial State")
    initial_data = analytics.get_user_data("test_user")
    print(f"Initial data: {json.dumps(initial_data, indent=2)}")
    
    # Test quiz results tracking
    print("\n2. Testing Quiz Results Tracking")
    
    # Simulate answering some questions
    test_questions = [
        ("Linux Commands", True, "beginner"),
        ("File Permissions", False, "intermediate"),
        ("Shell Scripting", True, "advanced"),
        ("Process Management", True, "intermediate"),
        ("Network Configuration", False, "advanced"),
        ("System Administration", True, "beginner"),
        ("Package Management", False, "beginner")
    ]
    
    for topic, correct, difficulty in test_questions:
        result = analytics.update_quiz_results("test_user", correct, topic, difficulty)
        print(f"Answered {topic} ({'✓' if correct else '✗'}) - Accuracy: {result['accuracy']}%")
    
    # Test dashboard stats
    print("\n3. Testing Dashboard Stats")
    dashboard_stats = analytics.get_dashboard_stats("test_user")
    print(f"Dashboard stats: {json.dumps(dashboard_stats, indent=2)}")
    
    # Test analytics stats
    print("\n4. Testing Analytics Stats")
    analytics_stats = analytics.get_analytics_stats("test_user")
    print(f"Analytics stats: {json.dumps(analytics_stats, indent=2)}")
    
    # Verify consistency
    print("\n5. Consistency Check")
    print(f"Total questions: Dashboard={dashboard_stats['questions_answered']}, Analytics={analytics_stats['total_questions']}")
    print(f"Correct answers: Dashboard={dashboard_stats['total_correct']}, Analytics={analytics_stats['correct_answers']}")
    print(f"Accuracy: Dashboard={dashboard_stats['accuracy']}%, Analytics={analytics_stats['accuracy']}%")
    
    if (dashboard_stats['questions_answered'] == analytics_stats['total_questions'] and
        dashboard_stats['total_correct'] == analytics_stats['correct_answers'] and
        dashboard_stats['accuracy'] == analytics_stats['accuracy']):
        print("✅ All stats are consistent!")
    else:
        print("❌ Stats are inconsistent!")
    
    # Test expected values
    print("\n6. Expected Values Check")
    expected_total = len(test_questions)
    expected_correct = sum(1 for _, correct, _ in test_questions if correct)
    expected_accuracy = (expected_correct / expected_total) * 100
    
    print(f"Expected: {expected_total} questions, {expected_correct} correct, {expected_accuracy:.2f}% accuracy")
    print(f"Got: {dashboard_stats['questions_answered']} questions, {dashboard_stats['total_correct']} correct, {dashboard_stats['accuracy']}% accuracy")
    
    if (dashboard_stats['questions_answered'] == expected_total and
        dashboard_stats['total_correct'] == expected_correct and
        abs(dashboard_stats['accuracy'] - expected_accuracy) < 0.1):
        print("✅ Values match expected results!")
    else:
        print("❌ Values don't match expected results!")
    
    # Reset for clean test
    print("\n7. Testing Reset Function")
    analytics.reset_user_data("test_user")
    reset_data = analytics.get_user_data("test_user")
    print(f"After reset: {reset_data['total_questions']} questions, {reset_data['accuracy']}% accuracy")
    
    if reset_data['total_questions'] == 0 and reset_data['accuracy'] == 0:
        print("✅ Reset function works correctly!")
    else:
        print("❌ Reset function failed!")

def test_api_endpoints():
    """Test the API endpoints"""
    print("\n\n🌐 Testing API Endpoints")
    print("========================")
    
    try:
        # Test dashboard API
        print("Testing /api/dashboard")
        response = requests.get('http://localhost:5000/api/dashboard', timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Dashboard API: {data}")
        else:
            print(f"❌ Dashboard API failed: {response.status_code}")
            
        # Test analytics API
        print("\nTesting /api/analytics")
        response = requests.get('http://localhost:5000/api/analytics', timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Analytics API: {data}")
        else:
            print(f"❌ Analytics API failed: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ API test failed: {e}")
        print("Make sure the server is running: python3 main.py")

if __name__ == '__main__':
    test_simple_analytics()
    test_api_endpoints()
    
    print("\n🎉 Test Complete!")
    print("="*50)
    print("The simple analytics system provides:")
    print("- Single JSON file storage")
    print("- Consistent data across all views")
    print("- Easy to understand and maintain")
    print("- No database complexity")
    print("="*50)
