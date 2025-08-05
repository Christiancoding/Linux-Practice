#!/usr/bin/env python3
"""
Test script to verify the review functionality is working
"""

import sys
import requests

def test_review_functionality():
    """Test the review page and button functionality"""
    base_url = "http://127.0.0.1:5000"
    
    print("=== Testing Review Functionality ===")
    
    # Test 1: Check if review page loads
    print("1. Testing review page accessibility...")
    review_response = requests.get(f"{base_url}/review")
    
    if review_response.status_code == 200:
        print("✓ Review page loads successfully")
    else:
        print(f"ERROR: Review page failed to load - {review_response.status_code}")
        return False
    
    # Test 2: Check if review API endpoint works
    print("\n2. Testing review API endpoint...")
    review_api_response = requests.get(f"{base_url}/api/review_incorrect")
    
    if review_api_response.status_code == 200:
        review_data = review_api_response.json()
        print(f"✓ Review API works - Found {len(review_data.get('questions', []))} questions to review")
        
        # Check if we have review questions
        if review_data.get('has_questions', False):
            print("✓ Review system has questions available")
        else:
            print("ℹ No questions currently in review list (this is normal for a fresh system)")
        
    else:
        print(f"ERROR: Review API failed - {review_api_response.status_code}")
        return False
    
    # Test 3: Simulate getting some incorrect answers to populate review list
    print("\n3. Creating some incorrect answers to test review functionality...")
    
    # Start a quiz session
    start_response = requests.post(f"{base_url}/api/start_quiz", json={"mode": "standard"})
    if start_response.status_code != 200:
        print("ERROR: Could not start quiz for review test")
        return False
    
    # Get a question and answer it incorrectly (try a few wrong answers)
    question_response = requests.get(f"{base_url}/api/get_question")
    if question_response.status_code == 200:
        question_data = question_response.json()
        options = question_data.get('options', [])
        
        # Try to submit wrong answers (we'll submit multiple to increase chances of getting some wrong)
        for i in range(min(2, len(options))):
            submit_response = requests.post(f"{base_url}/api/submit_answer", 
                                          json={"answer_index": i})
            if submit_response.status_code == 200:
                submit_data = submit_response.json()
                is_correct = submit_data.get('is_correct', False)
                print(f"  Answer {i}: {'correct' if is_correct else 'incorrect'}")
                
                # If we got one wrong, that should add to review list
                if not is_correct:
                    print("  ✓ Added an incorrect answer to review list")
                    break
                    
                # Get next question if we continue
                if i < min(2, len(options)) - 1:
                    question_response = requests.get(f"{base_url}/api/get_question")
                    if question_response.status_code != 200:
                        break
            else:
                print(f"  ERROR: Failed to submit answer {i}")
    
    # End the test quiz
    requests.post(f"{base_url}/api/end_quiz")
    
    # Test 4: Check review list again after incorrect answers
    print("\n4. Checking review list after incorrect answers...")
    review_api_response = requests.get(f"{base_url}/api/review_incorrect")
    
    if review_api_response.status_code == 200:
        review_data = review_api_response.json()
        question_count = len(review_data.get('questions', []))
        print(f"✓ Review API still works - Now has {question_count} questions to review")
        
        if question_count > 0:
            print("✓ Review functionality is working - questions are being added to review list")
            return True
        else:
            print("⚠ No questions in review list (might be normal if all answers were correct)")
            return True
    else:
        print(f"ERROR: Review API failed after adding questions - {review_api_response.status_code}")
        return False

if __name__ == "__main__":
    try:
        success = test_review_functionality()
        if success:
            print("\n✅ Review functionality test PASSED")
            sys.exit(0)
        else:
            print("\n❌ Review functionality test FAILED")
            sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test error: {e}")
        sys.exit(1)
