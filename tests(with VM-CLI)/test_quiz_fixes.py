#!/usr/bin/env python3
"""
Test script to verify quiz functionality fixes.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from controllers.quiz_controller import QuizController
from models.game_state import GameState

def test_quiz_modes():
    """Test that all quiz modes can be started."""
    
    print("Testing quiz mode functionality...")
    
    # Initialize game state
    game_state = GameState()
    quiz_controller = QuizController(game_state)
    
    modes_to_test = ['standard', 'timed', 'survival', 'exam']
    
    for mode in modes_to_test:
        print(f"\nTesting {mode} mode...")
        try:
            result = quiz_controller.start_quiz_session(mode=mode)
            if result.get('session_active'):
                print(f"✓ {mode} mode started successfully")
                
                # Test getting a question
                question = quiz_controller.get_next_question()
                if question:
                    print(f"✓ {mode} mode can get questions")
                else:
                    print(f"✗ {mode} mode failed to get questions")
                
                # End the session
                quiz_controller.end_session()
                print(f"✓ {mode} mode ended successfully")
            else:
                print(f"✗ {mode} mode failed to start: {result}")
        except Exception as e:
            print(f"✗ {mode} mode error: {e}")

def test_custom_question_limit():
    """Test custom question limit functionality."""
    
    print("\nTesting custom question limit...")
    
    game_state = GameState()
    quiz_controller = QuizController(game_state)
    
    # Set custom question limit
    quiz_controller.custom_question_limit = 3
    
    # Start quiz
    result = quiz_controller.start_quiz_session(mode='standard')
    if result.get('session_active'):
        print("✓ Quiz started with custom limit")
        
        # Simulate answering 3 questions
        for i in range(3):
            question = quiz_controller.get_next_question()
            if question:
                # Simulate answer submission
                quiz_controller.session_total += 1
                print(f"✓ Question {i+1} processed")
            else:
                print(f"✗ Failed to get question {i+1}")
                break
        
        # Check if session completes after limit
        is_complete = quiz_controller._check_session_complete()
        if is_complete:
            print("✓ Custom question limit working correctly")
        else:
            print("✗ Custom question limit not working")
    else:
        print("✗ Failed to start quiz with custom limit")

if __name__ == "__main__":
    test_quiz_modes()
    test_custom_question_limit()
    print("\nQuiz functionality tests completed!")
