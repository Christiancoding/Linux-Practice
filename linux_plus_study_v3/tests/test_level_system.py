#!/usr/bin/env python3
"""
Test script to validate the level calculation system
"""

import math

def calculate_level_from_points(points: int) -> int:
    """Test the level calculation logic"""
    if points <= 0:
        return 1
    level = int(math.sqrt(points / 50)) + 1
    return max(1, level)

def calculate_xp_for_level(level: int) -> int:
    """Calculate total XP required for a specific level"""
    if level <= 1:
        return 0
    return (level - 1) ** 2 * 50

def test_level_system():
    """Test the level system with various point values"""
    test_points = [0, 10, 50, 100, 130, 200, 500, 1000, 2000]
    
    print("Level System Test:")
    print("=" * 60)
    print(f"{'Points':<10} {'Level':<8} {'XP Required':<15} {'Next Level XP':<15}")
    print("-" * 60)
    
    for points in test_points:
        level = calculate_level_from_points(points)
        current_level_xp = calculate_xp_for_level(level)
        next_level_xp = calculate_xp_for_level(level + 1)
        
        print(f"{points:<10} {level:<8} {current_level_xp:<15} {next_level_xp:<15}")
    
    print("\nLevel Progress Examples:")
    print("=" * 60)
    
    # Test with current user's points (130)
    user_points = 130
    user_level = calculate_level_from_points(user_points)
    current_level_xp = calculate_xp_for_level(user_level)
    next_level_xp = calculate_xp_for_level(user_level + 1)
    
    xp_in_current_level = user_points - current_level_xp
    xp_needed_for_next = next_level_xp - current_level_xp
    progress_percentage = (xp_in_current_level / xp_needed_for_next * 100) if xp_needed_for_next > 0 else 0
    
    print(f"User with {user_points} XP:")
    print(f"  Level: {user_level}")
    print(f"  XP in current level: {xp_in_current_level}")
    print(f"  XP needed for next level: {xp_needed_for_next}")
    print(f"  Progress to next level: {progress_percentage:.1f}%")

if __name__ == "__main__":
    test_level_system()
