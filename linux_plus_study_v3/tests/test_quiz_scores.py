#!/usr/bin/env python3
"""
Test script to verify quiz scoring issues are fixed
"""

import sys
import requests
import json
import time

# Test the quiz functionality
def test_quiz_scoring():
    """Test the quiz scoring system"""
    base_url = "http://127.0.0.1:5000"
    
    print("=== Testing Quiz Scoring System ===")
    
    # Start a quiz session
    print("1. Starting quiz session...")
    start_response = requests.post(f"{base_url}/api/start_quiz", 
                                 json={"mode": "standard"})
    
    if start_response.status_code != 200:
        print(f"ERROR: Failed to start quiz - {start_response.status_code}")
        return False
    
    start_data = start_response.json()
    print(f"Quiz started: {start_data}")
    
    # Get first question
    print("\n2. Getting first question...")
    question_response = requests.get(f"{base_url}/api/get_question")
    
    if question_response.status_code != 200:
        print(f"ERROR: Failed to get question - {question_response.status_code}")
        return False
    
    question_data = question_response.json()
    print(f"Question received: {question_data.get('question', 'N/A')[:100]}...")
    options = question_data.get('options', [])
    print(f"Options: {len(options)} choices available")
    
    # Submit different answers to test - we'll try all options to ensure at least one is correct
    results = []
    
    for i in range(min(len(options), 4)):  # Try up to 4 answers
        print(f"\n3.{i+1}. Submitting answer {i}...")
        
        submit_response = requests.post(f"{base_url}/api/submit_answer",
                                      json={"answer_index": i})
        
        if submit_response.status_code != 200:
            print(f"ERROR: Failed to submit answer - {submit_response.status_code}")
            continue
        
        submit_data = submit_response.json()
        is_correct = submit_data.get('is_correct', False)
        session_score = submit_data.get('session_score', 0)
        session_total = submit_data.get('session_total', 0)
        
        print(f"Answer {i}: {'✓ CORRECT' if is_correct else '✗ incorrect'} - Score: {session_score}/{session_total}")
        results.append({
            'answer_index': i,
            'is_correct': is_correct,
            'session_score': session_score,
            'session_total': session_total
        })
        
        # If quiz is complete, break
        if submit_data.get('session_complete', False):
            print("Quiz completed after this answer")
            break
        
        # Get next question for the next iteration
        if i < min(len(options), 4) - 1:  # Don't get next question on last iteration
            question_response = requests.get(f"{base_url}/api/get_question")
            if question_response.status_code == 200:
                question_data = question_response.json()
                options = question_data.get('options', [])
            else:
                print("No more questions available")
                break
    
    # Check results
    correct_answers = sum(1 for r in results if r['is_correct'])
    total_answers = len(results)
    
    print(f"\n=== Test Results ===")
    print(f"Attempted {total_answers} answers, {correct_answers} were correct")
    
    if total_answers == 0:
        print("ERROR: No answers were submitted")
        return False
    
    # End quiz and get results
    print("\n4. Ending quiz...")
    end_response = requests.post(f"{base_url}/api/end_quiz")
    
    if end_response.status_code == 200:
        end_data = end_response.json()
        print(f"Quiz ended successfully")
        
        # Check final results
        final_score = end_data.get('session_score', 0)
        final_total = end_data.get('session_total', 0)
        accuracy = end_data.get('accuracy', 0)
        
        print(f"Final Results - Score: {final_score}/{final_total}, Accuracy: {accuracy}%")
        
        if final_total == 0:
            print("ERROR: No questions recorded in session")
            return False
        elif final_score == 0 and final_total > 0:
            print("WARNING: All answers were incorrect (this is possible if all guesses were wrong)")
            # This is not necessarily an error - could be bad luck with guessing
        
        # Check if scoring is consistent
        if results:
            last_result = results[-1]
            if last_result['session_score'] == final_score and last_result['session_total'] == final_total:
                print("✓ Score tracking consistency verified")
                return True
            else:
                print(f"ERROR: Score inconsistency - last answer: {last_result['session_score']}/{last_result['session_total']}, final: {final_score}/{final_total}")
                return False
        else:
            print("✓ Quiz ended properly")
            return True
    else:
        print(f"ERROR: Failed to end quiz - {end_response.status_code}")
        return False

if __name__ == "__main__":
    try:
        success = test_quiz_scoring()
        if success:
            print("\n✅ Quiz scoring test PASSED")
            sys.exit(0)
        else:
            print("\n❌ Quiz scoring test FAILED")
            sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test error: {e}")
        sys.exit(1)
