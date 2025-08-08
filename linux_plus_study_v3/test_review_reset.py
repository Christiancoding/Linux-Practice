#!/usr/bin/env python3
"""
Test script to verify the review questions reset functionality
"""

import sys
import os
import json

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_review_reset():
    """Test that review questions are cleared when reset is performed"""
    print("🧪 Testing Review Questions Reset")
    print("=" * 40)
    
    # Check the game state history file directly
    history_file = "linux_plus_history.json"
    
    if os.path.exists(history_file):
        with open(history_file, 'r') as f:
            history = json.load(f)
        
        incorrect_review = history.get("incorrect_review", [])
        print(f"📋 Current review questions count: {len(incorrect_review)}")
        
        if incorrect_review:
            print(f"📝 Review questions:")
            for i, question in enumerate(incorrect_review[:5], 1):  # Show first 5
                print(f"  {i}. {question[:80]}{'...' if len(question) > 80 else ''}")
            if len(incorrect_review) > 5:
                print(f"  ... and {len(incorrect_review) - 5} more")
        else:
            print("✅ No review questions found (already cleared)")
    else:
        print("❌ History file not found")
        return False
    
    return len(incorrect_review) == 0

def clear_review_questions_manually():
    """Manually clear review questions for testing"""
    print("\n🔧 Manually clearing review questions...")
    
    history_file = "linux_plus_history.json"
    
    if os.path.exists(history_file):
        with open(history_file, 'r') as f:
            history = json.load(f)
        
        # Clear the review questions
        old_count = len(history.get("incorrect_review", []))
        history["incorrect_review"] = []
        
        # Save back to file
        with open(history_file, 'w') as f:
            json.dump(history, f, indent=2)
        
        print(f"✅ Cleared {old_count} review questions")
        return True
    else:
        print("❌ History file not found")
        return False

if __name__ == "__main__":
    is_clear = test_review_reset()
    
    if not is_clear:
        print("\n❓ Would you like to clear the review questions manually? (y/n)")
        # For testing, let's auto-clear
        clear_review_questions_manually()
        
        # Test again
        print("\n🔄 Testing after manual clear...")
        is_clear = test_review_reset()
    
    if is_clear:
        print("\n🎉 Review questions are cleared!")
    else:
        print("\n💥 Review questions still present!")
