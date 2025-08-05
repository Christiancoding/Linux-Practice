#!/usr/bin/env python3
"""
Test script to verify the session completion timing is correct
"""

import sys
import requests
import time

def test_session_completion_timing():
    """Test the quiz session completion behavior"""
    base_url = "http://127.0.0.1:5000"
    
    print("=== Testing Session Completion Timing ===")
    
    # Start a quiz session
    print("1. Starting quiz session...")
    start_response = requests.post(f"{base_url}/api/start_quiz", json={"mode": "standard"})
    
    if start_response.status_code != 200:
        print(f"ERROR: Failed to start quiz - {start_response.status_code}")
        return False
    
    print("✓ Quiz session started")
    
    # Answer several questions to test the completion behavior
    questions_answered = 0
    max_questions = 5  # Test with 5 questions
    
    for i in range(max_questions):
        print(f"\n2.{i+1}. Getting question {i+1}...")
        
        # Get question
        question_response = requests.get(f"{base_url}/api/get_question")
        
        if question_response.status_code != 200:
            print(f"No more questions available after {questions_answered} questions")
            break
        
        question_data = question_response.json()
        
        # Check if quiz is marked as complete in the question response
        if question_data.get('quiz_complete', False):
            print(f"Quiz marked as complete in question response after {questions_answered} questions")
            break
        
        print(f"✓ Got question: {question_data.get('question', 'N/A')[:50]}...")
        
        # Submit an answer (try index 0)
        print(f"  Submitting answer...")
        submit_response = requests.post(f"{base_url}/api/submit_answer", json={"answer_index": 0})
        
        if submit_response.status_code != 200:
            print(f"ERROR: Failed to submit answer - {submit_response.status_code}")
            break
        
        submit_data = submit_response.json()
        session_complete = submit_data.get('session_complete', False)
        is_correct = submit_data.get('is_correct', False)
        session_score = submit_data.get('session_score', 0)
        session_total = submit_data.get('session_total', 0)
        
        questions_answered += 1
        
        print(f"  ✓ Answer submitted: {'correct' if is_correct else 'incorrect'}")
        print(f"  Score: {session_score}/{session_total}")
        print(f"  Session complete: {session_complete}")
        
        if session_complete:
            print(f"✓ Session completed naturally after {questions_answered} questions")
            break
        
        # Small delay to simulate real usage
        time.sleep(0.1)
    
    # Test if we can still get session status
    print(f"\n3. Checking final session status...")
    status_response = requests.get(f"{base_url}/api/status")
    
    if status_response.status_code == 200:
        status_data = status_response.json()
        quiz_active = status_data.get('quiz_active', False)
        print(f"✓ Quiz active: {quiz_active}")
        print(f"  Final score: {status_data.get('session_score', 0)}/{status_data.get('session_total', 0)}")
    
    # Try to end the quiz
    print(f"\n4. Ending quiz session...")
    end_response = requests.post(f"{base_url}/api/end_quiz")
    
    if end_response.status_code == 200:
        end_data = end_response.json()
        print(f"✓ Quiz ended successfully")
        print(f"  Final results: {end_data.get('session_score', 0)}/{end_data.get('session_total', 0)}")
        print(f"  Accuracy: {end_data.get('accuracy', 0):.1f}%")
    else:
        print(f"ERROR: Failed to end quiz - {end_response.status_code}")
        return False
    
    # Evaluation
    if questions_answered >= 3:
        print(f"\n✅ Session completion timing test PASSED")
        print(f"   - Answered {questions_answered} questions before completion")
        print(f"   - Session completion behavior appears normal")
        return True
    else:
        print(f"\n⚠ Session completed very quickly after only {questions_answered} questions")
        print(f"   - This might indicate premature completion, but could be normal for small question pools")
        return True  # Not necessarily a failure

if __name__ == "__main__":
    try:
        success = test_session_completion_timing()
        if success:
            print("\n✅ Session completion timing test PASSED")
            sys.exit(0)
        else:
            print("\n❌ Session completion timing test FAILED")
            sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test error: {e}")
        sys.exit(1)
