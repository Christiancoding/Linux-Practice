#!/usr/bin/env python3
"""
Test script to verify quiz data persistence.
"""
import sys
import os
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from models.game_state import GameState
from controllers.quiz_controller import QuizController

def test_persistence():
    """Test quiz data persistence."""
    print("🧪 Testing Quiz Data Persistence")
    print("=" * 50)
    
    # Initialize game state and quiz controller
    game_state = GameState()
    quiz_controller = QuizController(game_state)
    
    print(f"📁 History file path: {game_state.history_file}")
    print(f"📊 Initial total attempts: {game_state.study_history.get('total_attempts', 0)}")
    
    # Start a quiz session
    print("\n🎯 Starting a standard quiz session...")
    result = quiz_controller.start_quiz_session(mode='standard')
    print(f"   Session started: {result.get('session_active', False)}")
    
    # Get a question
    print("\n❓ Getting next question...")
    question_result = quiz_controller.get_next_question()
    if question_result:
        question_data = question_result['question_data']
        original_index = question_result['original_index']
        print(f"   Question: {question_data[0][:50]}...")
        
        # Submit a correct answer (index 0 for simplicity)
        print("\n✅ Submitting answer...")
        answer_result = quiz_controller.submit_answer(
            question_data=question_data,
            user_answer_index=question_data[2],  # Use correct answer index
            original_index=original_index
        )
        print(f"   Answer correct: {answer_result.get('is_correct', False)}")
        print(f"   Session complete: {answer_result.get('session_complete', False)}")
        
        # Check if data was saved
        print(f"\n💾 Total attempts after answer: {game_state.study_history.get('total_attempts', 0)}")
        
        # End the session manually to force save
        print("\n🏁 Ending session...")
        end_result = quiz_controller.end_session()
        print(f"   Session ended successfully: {'error' not in end_result}")
        print(f"   Final session score: {end_result.get('session_score', 0)}/{end_result.get('session_total', 0)}")
        
        # Check if history file was created
        if os.path.exists(game_state.history_file):
            print(f"\n✅ History file created: {game_state.history_file}")
            with open(game_state.history_file, 'r') as f:
                history_data = json.load(f)
            print(f"   Total attempts in file: {history_data.get('total_attempts', 0)}")
            print(f"   Total correct in file: {history_data.get('total_correct', 0)}")
        else:
            print(f"\n❌ History file NOT created: {game_state.history_file}")
    
    print("\n" + "=" * 50)
    print("🔄 Now testing persistence by creating new instances...")
    
    # Create new instances to simulate server restart
    new_game_state = GameState()
    new_quiz_controller = QuizController(new_game_state)
    
    print(f"📊 Total attempts after 'restart': {new_game_state.study_history.get('total_attempts', 0)}")
    print(f"📊 Total correct after 'restart': {new_game_state.study_history.get('total_correct', 0)}")
    
    if new_game_state.study_history.get('total_attempts', 0) > 0:
        print("✅ Data persisted successfully!")
    else:
        print("❌ Data was NOT persisted!")

if __name__ == "__main__":
    test_persistence()
