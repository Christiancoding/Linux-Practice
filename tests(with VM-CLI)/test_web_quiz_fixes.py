#!/usr/bin/env python3
"""
Test script to verify web interface quiz functionality.
"""

import sys
import os
import json
import time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_web_quiz_api():
    """Test quiz API endpoints."""
    try:
        import requests
        
        # Test if the web server is running
        base_url = "http://localhost:5000"
        
        print("Testing web interface quiz API...")
        
        # Test categories endpoint
        try:
            response = requests.get(f"{base_url}/api/get_categories", timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    print(f"✓ Categories API working - found {len(data.get('categories', []))} categories")
                else:
                    print("✗ Categories API returned error")
            else:
                print(f"✗ Categories API failed - status {response.status_code}")
        except requests.exceptions.RequestException:
            print("⚠ Web server not running - start with 'python main.py' to test web interface")
            return
        
        # Test starting different quiz modes
        modes_to_test = [
            ('standard', '/api/start_quiz'),
            ('timed', '/api/start_timed_challenge'),
            ('survival', '/api/start_survival_mode'),
            ('exam', '/api/start_exam_mode')
        ]
        
        for mode, endpoint in modes_to_test:
            try:
                payload = {
                    'mode': mode,
                    'category': 'All Categories'
                }
                
                if mode not in ['survival', 'exam']:
                    payload['num_questions'] = 5
                
                response = requests.post(f"{base_url}{endpoint}", 
                                       json=payload, 
                                       timeout=5)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('success'):
                        print(f"✓ {mode} mode API working")
                        
                        # Test getting a question
                        q_response = requests.get(f"{base_url}/api/get_question", timeout=5)
                        if q_response.status_code == 200:
                            q_data = q_response.json()
                            if 'question' in q_data and not q_data.get('quiz_complete'):
                                print(f"✓ {mode} mode can get questions")
                            else:
                                print(f"⚠ {mode} mode question response: {q_data}")
                        
                        # End the session
                        requests.post(f"{base_url}/api/end_quiz", timeout=5)
                    else:
                        print(f"✗ {mode} mode API error: {data.get('error', 'Unknown error')}")
                else:
                    print(f"✗ {mode} mode API failed - status {response.status_code}")
                    
            except requests.exceptions.RequestException as e:
                print(f"✗ {mode} mode API request failed: {e}")
                
        print("Web interface testing completed!")
        
    except ImportError:
        print("⚠ 'requests' library not available - install with 'pip install requests' to test web interface")

if __name__ == "__main__":
    test_web_quiz_api()
