#!/usr/bin/env python3
"""
Simple test script to verify quiz functionality
"""

import time
import requests
import json
from multiprocessing import Process
import subprocess
import sys
import os

def start_server():
    """Start the Flask server in background"""
    os.chdir('/home/retiredfan/Documents/github/linux_plus_study_v3_main/linux_plus_study_v3')
    # Start Flask app with web interface mode
    subprocess.run([sys.executable, 'main.py'], input='1\n', text=True)

def test_quiz_endpoints():
    """Test quiz API endpoints"""
    base_url = "http://127.0.0.1:5000"
    
    # Wait for server to start
    print("Waiting for server to start...")
    time.sleep(3)
    
    try:
        # Test quiz modes
        modes = {
            'standard': '/api/start_quiz',
            'timed': '/api/start_timed_challenge', 
            'survival': '/api/start_survival_mode',
            'exam': '/api/start_exam_mode'
        }
        
        for mode_name, endpoint in modes.items():
            print(f"\n=== Testing {mode_name.upper()} MODE ===")
            
            # Start quiz
            response = requests.post(f"{base_url}{endpoint}", 
                                   json={'mode': mode_name, 'category': 'all'},
                                   timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    print(f"✅ {mode_name} mode started successfully")
                    print(f"   Mode: {data.get('mode', 'unknown')}")
                    print(f"   Total questions: {data.get('total_questions', 'unknown')}")
                    
                    # Test getting a question
                    q_response = requests.get(f"{base_url}/api/get_question", timeout=5)
                    if q_response.status_code == 200:
                        q_data = q_response.json()
                        if not q_data.get('error'):
                            print(f"✅ Question loaded successfully")
                            print(f"   Question: {q_data.get('question', 'No question')[:50]}...")
                        else:
                            print(f"❌ Error getting question: {q_data.get('error')}")
                    else:
                        print(f"❌ Failed to get question: {q_response.status_code}")
                else:
                    print(f"❌ {mode_name} mode failed: {data.get('error', 'Unknown error')}")
            else:
                print(f"❌ HTTP error for {mode_name}: {response.status_code}")
                
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Make sure it's running.")
    except Exception as e:
        print(f"❌ Error testing endpoints: {e}")

if __name__ == "__main__":
    print("🧪 Testing Quiz Functionality")
    print("=" * 50)
    
    # Start server in background
    server_process = Process(target=start_server)
    server_process.start()
    
    try:
        # Test endpoints
        test_quiz_endpoints()
        
        print("\n" + "=" * 50)
        print("🔍 Test completed. Check results above.")
        
    finally:
        # Clean up
        server_process.terminate()
        server_process.join(timeout=2)
        if server_process.is_alive():
            server_process.kill()
        print("\n🧹 Server stopped.")
