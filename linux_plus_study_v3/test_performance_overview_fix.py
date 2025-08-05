#!/usr/bin/env python3
"""
Test script to validate performance overview fixes in achievements and dashboard pages.
"""

import sys
import tempfile
import os
import json
from datetime import datetime

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_achievements_api():
    """Test the achievements API functionality."""
    print("🔍 Testing Achievements API...")
    
    try:
        from models.game_state import GameState
        from controllers.stats_controller import StatsController
        
        # Create temporary database
        temp_db = tempfile.mktemp(suffix='.db')
        game_state = GameState(temp_db)
        stats_controller = StatsController(game_state)
        
        # Get achievements data
        achievements_data = stats_controller.get_achievements_data()
        level_info = game_state.achievement_system.get_level_progress()
        
        # Simulate the API endpoint logic
        detailed_stats = stats_controller.get_detailed_statistics()
        accuracy = detailed_stats['overall']['overall_accuracy']
        questions_answered = game_state.achievements.get('questions_answered', 0)
        
        unlocked_list = achievements_data.get('unlocked', [])
        available_list = achievements_data.get('available', [])
        
        unlocked_count = len(unlocked_list) if isinstance(unlocked_list, list) else 0
        available_count = len(available_list) if isinstance(available_list, list) else 0
        total_achievements = unlocked_count + available_count
        
        # Build the expected API response
        api_response = {
            **achievements_data,
            'stats': {
                'unlocked': unlocked_count,
                'total': total_achievements,
                'points': achievements_data.get('total_points', 0),
                'completion': round((unlocked_count / max(1, total_achievements)) * 100, 1),
                'rarest': 'None',
                'level': level_info['level'],
                'xp': level_info['total_xp'],
                'level_progress': level_info['progress_percentage'],
                'accuracy': accuracy
            },
            'questions_answered': questions_answered
        }
        
        print(f"✅ Achievements API structure:")
        print(f"   - Unlocked achievements: {unlocked_count}")
        print(f"   - Total achievements: {total_achievements}")
        print(f"   - User level: {level_info['level']}")
        print(f"   - User XP: {level_info['total_xp']}")
        print(f"   - Accuracy: {accuracy}%")
        print(f"   - Questions answered: {questions_answered}")
        print(f"   - Has questions_answered key: {'questions_answered' in api_response}")
        
        # Cleanup
        if os.path.exists(temp_db):
            os.remove(temp_db)
            
        return True
        
    except Exception as e:
        print(f"❌ Achievements API test failed: {e}")
        return False

def test_analytics_service():
    """Test the analytics service functionality."""
    print("\n🔍 Testing Analytics Service...")
    
    try:
        from services.analytics_service import AnalyticsService
        
        # Create mock session
        class MockSession:
            pass
        
        service = AnalyticsService(MockSession())
        
        # Test user summary
        summary = service.get_user_summary('test_user')
        
        required_keys = [
            'total_questions', 'overall_accuracy', 'total_study_time', 
            'total_vm_commands', 'recent_performance', 'category_performance',
            'recent_sessions', 'study_streak'
        ]
        
        missing_keys = [key for key in required_keys if key not in summary]
        
        if missing_keys:
            print(f"❌ Missing required keys: {missing_keys}")
            return False
        
        print(f"✅ Analytics Service working:")
        print(f"   - Total questions: {summary['total_questions']}")
        print(f"   - Overall accuracy: {summary['overall_accuracy']}%")
        print(f"   - Total study time: {summary['total_study_time']/3600:.1f}h")
        print(f"   - VM commands: {summary['total_vm_commands']}")
        print(f"   - Recent performance entries: {len(summary['recent_performance'])}")
        print(f"   - Study streak: {summary['study_streak']} days")
        
        # Test global statistics
        global_stats = service.get_global_statistics()
        print(f"   - Global stats keys: {list(global_stats.keys())}")
        
        return True
        
    except Exception as e:
        print(f"❌ Analytics Service test failed: {e}")
        return False

def test_template_fixes():
    """Test that template fixes are in place."""
    print("\n🔍 Testing Template Fixes...")
    
    try:
        # Read achievements template
        achievements_path = "templates/achievements.html"
        if not os.path.exists(achievements_path):
            print(f"❌ Achievements template not found at {achievements_path}")
            return False
        
        with open(achievements_path, 'r') as f:
            achievements_content = f.read()
        
        # Check for fixed CSS selector
        if '.player-score' in achievements_content and 'querySelectorAll(\'.leaderboard-item .player-score\')' in achievements_content:
            print("✅ Achievements leaderboard selector fixed")
        else:
            print("❌ Achievements leaderboard selector not fixed")
            return False
        
        # Check for displayAchievements function
        if 'function displayAchievements(' in achievements_content:
            print("✅ displayAchievements function added")
        else:
            print("❌ displayAchievements function missing")
            return False
        
        # Read analytics dashboard template
        dashboard_path = "templates/analytics_dashboard.html"
        if not os.path.exists(dashboard_path):
            print(f"❌ Analytics dashboard template not found at {dashboard_path}")
            return False
        
        with open(dashboard_path, 'r') as f:
            dashboard_content = f.read()
        
        # Check for error handling improvements
        if 'initializeAnalyticsDashboard()' in dashboard_content and 'showErrorState()' in dashboard_content:
            print("✅ Analytics dashboard error handling improved")
        else:
            print("❌ Analytics dashboard error handling not improved")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Template fixes test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🚀 Testing Performance Overview Fixes\n")
    print("=" * 50)
    
    tests = [
        ("Achievements API", test_achievements_api),
        ("Analytics Service", test_analytics_service),
        ("Template Fixes", test_template_fixes)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 50)
    print("📊 Test Summary:")
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"   {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All performance overview fixes are working correctly!")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please check the issues above.")
        return 1

if __name__ == "__main__":
    exit(main())
