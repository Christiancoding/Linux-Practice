#!/usr/bin/env python3
"""
Test script to verify the API reset functionality works
"""

import sys
import os
import json

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_api_reset_simulation():
    """Simulate the reset API call without starting the web server"""
    print("🧪 Testing API Reset Simulation")
    print("=" * 40)
    
    # Import the necessary modules
    from services.simple_analytics import get_analytics_manager
    from models.game_state import GameState
    
    # Create a mock game state
    game_state = GameState()
    
    # Check initial state
    incorrect_review = game_state.study_history.get("incorrect_review", [])
    print(f"📋 Initial review questions count: {len(incorrect_review)}")
    
    if incorrect_review:
        print(f"📝 Sample review questions:")
        for i, question in enumerate(incorrect_review[:3], 1):
            print(f"  {i}. {question[:60]}...")
    
    # Simulate the reset functionality
    print("\n🔄 Simulating reset functionality...")
    
    # Reset analytics
    analytics = get_analytics_manager()
    user_id = "anonymous"
    success = analytics.reset_profile(user_id)
    print(f"✓ Analytics reset success: {success}")
    
    # Reset review questions in game state
    if hasattr(game_state, 'study_history'):
        game_state.study_history["incorrect_review"] = []
        print("✓ Review questions cleared from game state")
        
        # Save the game state
        if hasattr(game_state, 'save_history'):
            game_state.save_history()
            print("✓ Game state saved")
    
    # Verify the reset
    print("\n🔍 Verifying reset...")
    
    # Check analytics
    stats = analytics.get_dashboard_stats(user_id)
    print(f"✓ Analytics - Total questions: {stats['total_questions']}")
    print(f"✓ Analytics - Correct answers: {stats['correct_answers']}")
    print(f"✓ Analytics - XP: {stats['xp']}")
    
    # Check game state
    incorrect_review_after = game_state.study_history.get("incorrect_review", [])
    print(f"✓ Game state - Review questions: {len(incorrect_review_after)}")
    
    # Check if file was updated
    try:
        with open("linux_plus_history.json", 'r') as f:
            history = json.load(f)
        file_review_count = len(history.get("incorrect_review", []))
        print(f"✓ File - Review questions: {file_review_count}")
    except Exception as e:
        print(f"❌ File check error: {e}")
        file_review_count = -1
    
    # Final assessment
    if (stats['total_questions'] == 0 and 
        stats['correct_answers'] == 0 and 
        stats['xp'] == 0 and 
        len(incorrect_review_after) == 0 and 
        file_review_count == 0):
        print("\n🎉 Reset functionality working correctly!")
        return True
    else:
        print("\n💥 Reset functionality has issues!")
        return False

if __name__ == "__main__":
    success = test_api_reset_simulation()
    if success:
        print("\n✅ All reset tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some reset tests failed!")
        sys.exit(1)
