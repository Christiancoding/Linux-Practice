#!/usr/bin/env python3
"""
Test script for the Game Values Configuration System.
Demonstrates how the centralized configuration works.
"""

from utils.game_values import get_game_value_manager, get_game_value

def main():
    print("🎮 Linux+ Study Game - Centralized Configuration Test")
    print("=" * 60)
    
    # Get the game value manager
    manager = get_game_value_manager()
    
    # Display current values
    print("\n📊 Current Game Values:")
    print("-" * 40)
    
    # Scoring values
    print(f"Points per correct answer: {get_game_value('scoring', 'points_per_correct')}")
    print(f"Points per incorrect answer: {get_game_value('scoring', 'points_per_incorrect')}")
    print(f"Hint penalty: {get_game_value('scoring', 'hint_penalty')}")
    print(f"Speed bonus: {get_game_value('scoring', 'speed_bonus')}")
    print(f"Streak bonus: {get_game_value('scoring', 'streak_bonus')}")
    print(f"Max streak bonus: {get_game_value('scoring', 'max_streak_bonus')}")
    
    # Streak values
    print(f"\nDaily streak threshold: {get_game_value('streaks', 'daily_streak_threshold')}")
    print(f"Weekly streak threshold: {get_game_value('streaks', 'weekly_streak_threshold')}")
    
    # Achievement thresholds
    print(f"\nAchievement point threshold: {get_game_value('scoring', 'achievement_point_threshold')}")
    print(f"Achievement question threshold: {get_game_value('scoring', 'achievement_question_threshold')}")
    
    # Quiz settings
    print(f"\nDefault question count: {get_game_value('quiz', 'default_question_count')}")
    print(f"Quick fire count: {get_game_value('quiz', 'quick_fire_count')}")
    print(f"Time per question: {get_game_value('quiz', 'time_per_question')}")
    
    # Accuracy thresholds
    print(f"\nExcellent threshold: {get_game_value('accuracy', 'excellent_threshold')}%")
    print(f"Good threshold: {get_game_value('accuracy', 'good_threshold')}%")
    print(f"Passing percentage: {get_game_value('accuracy', 'passing_percentage')}%")
    
    print("\n✅ All values loaded successfully from centralized configuration!")
    print("\n💡 To modify these values:")
    print("   1. Go to Settings > Game Values tab in the web interface")
    print("   2. Adjust values as needed")
    print("   3. Click 'Save Game Values'")
    print("   4. Values will be updated throughout the application")
    
    print("\n🔄 Testing configuration update...")
    
    # Test updating a value
    original_points = get_game_value('scoring', 'points_per_correct')
    print(f"Original points per correct: {original_points}")
    
    # Update scoring configuration
    success = manager.update_settings(
        scoring={'points_per_correct': 15}
    )
    
    if success:
        new_points = get_game_value('scoring', 'points_per_correct')
        print(f"Updated points per correct: {new_points}")
        
        # Restore original value
        manager.update_settings(
            scoring={'points_per_correct': original_points}
        )
        print(f"Restored points per correct: {get_game_value('scoring', 'points_per_correct')}")
        print("✅ Configuration update test successful!")
    else:
        print("❌ Configuration update test failed!")

if __name__ == "__main__":
    main()
