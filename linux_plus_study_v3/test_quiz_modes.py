#!/usr/bin/env python3
"""
Test script to verify that all quiz modes are working correctly.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from controllers.quiz_controller import QuizController
from models.game_state import GameState
from utils.config import *

def test_quiz_modes():
    """Test all quiz modes to ensure they initialize correctly."""
    print("Testing Quiz Modes Implementation...")
    print("=" * 50)
    
    # Initialize game state
    try:
        game_state = GameState()
        quiz_controller = QuizController(game_state)
        print("✅ Game state and quiz controller initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize: {e}")
        return False
    
    # Test each quiz mode
    modes_to_test = [
        ("standard", QUIZ_MODE_STANDARD),
        ("timed", QUIZ_MODE_TIMED),
        ("survival", QUIZ_MODE_SURVIVAL),
        ("category", QUIZ_MODE_CATEGORY_FOCUS),
        ("exam", QUIZ_MODE_EXAM),
        ("verify", QUIZ_MODE_VERIFY)
    ]
    
    all_passed = True
    
    for mode_name, mode_constant in modes_to_test:
        print(f"\nTesting {mode_name} mode...")
        try:
            # Start quiz session
            result = quiz_controller.start_quiz_session(mode=mode_constant)
            
            if result.get('session_active'):
                print(f"  ✅ {mode_name} mode started successfully")
                print(f"     Mode: {result.get('mode')}")
                print(f"     Total questions: {result.get('total_questions')}")
                
                # Check mode-specific attributes
                if mode_constant == QUIZ_MODE_TIMED:
                    print(f"     Timed mode active: {result.get('timed_mode_active')}")
                    print(f"     Time per question: {result.get('time_per_question')}")
                elif mode_constant == QUIZ_MODE_SURVIVAL:
                    print(f"     Survival mode active: {result.get('survival_mode_active')}")
                    print(f"     Lives: {result.get('survival_lives')}")
                elif mode_constant == QUIZ_MODE_EXAM:
                    print(f"     Exam mode active: {result.get('exam_mode_active')}")
                
            else:
                print(f"  ❌ {mode_name} mode failed to start")
                all_passed = False
            
            # Clean up for next test
            quiz_controller.force_end_session()
            
        except Exception as e:
            print(f"  ❌ {mode_name} mode failed with error: {e}")
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 All quiz modes are working correctly!")
    else:
        print("⚠️  Some quiz modes have issues that need to be fixed.")
    
    return all_passed

def test_constants():
    """Test that all required constants are defined."""
    print("\nTesting Quiz Mode Constants...")
    print("-" * 30)
    
    constants_to_check = [
        'QUIZ_MODE_STANDARD',
        'QUIZ_MODE_VERIFY', 
        'QUIZ_MODE_TIMED',
        'QUIZ_MODE_SURVIVAL',
        'QUIZ_MODE_CATEGORY_FOCUS',
        'QUIZ_MODE_EXAM',
        'TIMED_CHALLENGE_TIME_PER_QUESTION',
        'TIMED_CHALLENGE_QUESTIONS',
        'SURVIVAL_MODE_LIVES',
        'EXAM_MODE_QUESTIONS',
        'EXAM_MODE_TIME_LIMIT'
    ]
    
    all_defined = True
    for constant in constants_to_check:
        try:
            value = globals()[constant]
            print(f"  ✅ {constant} = {value}")
        except KeyError:
            print(f"  ❌ {constant} is not defined")
            all_defined = False
    
    return all_defined

if __name__ == "__main__":
    print("Linux+ Study Game - Quiz Modes Test")
    print("==================================")
    
    # Test constants first
    constants_ok = test_constants()
    
    if constants_ok:
        # Test quiz modes
        modes_ok = test_quiz_modes()
        
        if modes_ok:
            print("\n🎯 All tests passed! The quiz modes are ready to use.")
            sys.exit(0)
        else:
            print("\n💥 Some tests failed. Please check the implementation.")
            sys.exit(1)
    else:
        print("\n💥 Constants are missing. Please check the configuration.")
        sys.exit(1)
