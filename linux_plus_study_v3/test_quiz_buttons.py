#!/usr/bin/env python3
"""Test script to verify quiz button functionality"""

import requests
import json
import time

BASE_URL = "http://127.0.0.1:5000"

def test_quiz_mode_endpoints():
    """Test all quiz mode API endpoints"""
    print("🧪 Testing Quiz Button Functionality")
    print("=" * 50)
    
    # Test data for each mode
    test_modes = [
        {
            'mode': 'standard',
            'endpoint': '/api/start_quiz',
            'data': {'mode': 'standard', 'category': 'All Categories', 'num_questions': 20}
        },
        {
            'mode': 'timed',
            'endpoint': '/api/start_timed_challenge',
            'data': {'mode': 'timed', 'category': 'All Categories', 'num_questions': 20}
        },
        {
            'mode': 'survival',
            'endpoint': '/api/start_survival_mode',
            'data': {'mode': 'survival', 'category': 'All Categories'}
        },
        {
            'mode': 'exam',
            'endpoint': '/api/start_exam_mode',
            'data': {'mode': 'exam', 'category': 'All Categories'}
        }
    ]
    
    results = {}
    
    for test in test_modes:
        print(f"\n🎯 Testing {test['mode'].upper()} mode...")
        print(f"   Endpoint: {test['endpoint']}")
        print(f"   Data: {test['data']}")
        
        try:
            response = requests.post(
                BASE_URL + test['endpoint'],
                headers={'Content-Type': 'application/json'},
                json=test['data'],
                timeout=10
            )
            
            print(f"   Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   Response: {json.dumps(data, indent=2)}")
                
                if data.get('success'):
                    print(f"   ✅ {test['mode'].upper()} mode started successfully!")
                    results[test['mode']] = {'status': 'success', 'data': data}
                else:
                    print(f"   ❌ {test['mode'].upper()} mode failed: {data.get('error', 'Unknown error')}")
                    results[test['mode']] = {'status': 'failed', 'error': data.get('error')}
            else:
                print(f"   ❌ HTTP Error {response.status_code}: {response.text}")
                results[test['mode']] = {'status': 'http_error', 'code': response.status_code}
                
        except requests.exceptions.RequestException as e:
            print(f"   ❌ Request failed: {str(e)}")
            results[test['mode']] = {'status': 'request_error', 'error': str(e)}
        
        # Small delay between requests
        time.sleep(0.5)
    
    # Summary
    print("\n📊 TEST SUMMARY")
    print("=" * 50)
    successful = 0
    failed = 0
    
    for mode, result in results.items():
        if result['status'] == 'success':
            print(f"✅ {mode.upper()}: Working correctly")
            successful += 1
        else:
            print(f"❌ {mode.upper()}: {result.get('error', result['status'])}")
            failed += 1
    
    print(f"\n📈 Results: {successful}/{len(test_modes)} modes working")
    
    if successful == len(test_modes):
        print("🎉 All quiz modes are functioning correctly!")
        return True
    else:
        print("⚠️  Some quiz modes have issues that need to be fixed.")
        return False

def test_web_page_access():
    """Test if the quiz page loads correctly"""
    print("\n🌐 Testing Quiz Page Access")
    print("=" * 30)
    
    try:
        response = requests.get(BASE_URL + "/quiz", timeout=10)
        if response.status_code == 200:
            print("✅ Quiz page loads successfully")
            
            # Check for key elements in the HTML
            html = response.text
            checks = [
                ('Quiz mode cards', 'onclick="selectMode('),
                ('Start quiz button', 'onclick="startQuiz()"'),
                ('Mode selection', 'class="mode-card"'),
                ('Quiz options', 'id="quiz-category"')
            ]
            
            for check_name, check_pattern in checks:
                if check_pattern in html:
                    print(f"✅ {check_name}: Found")
                else:
                    print(f"❌ {check_name}: Missing")
            
            return True
        else:
            print(f"❌ Quiz page failed to load: HTTP {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to access quiz page: {str(e)}")
        return False

if __name__ == "__main__":
    print("Starting quiz button functionality tests...")
    print("Please ensure the Flask server is running on http://127.0.0.1:5000")
    print()
    
    # Test web page access first
    page_ok = test_web_page_access()
    
    if page_ok:
        # Test API endpoints
        api_ok = test_quiz_mode_endpoints()
        
        if api_ok:
            print("\n🎉 ALL TESTS PASSED! Quiz buttons should be working correctly.")
        else:
            print("\n⚠️  API tests failed. Check server logs for errors.")
    else:
        print("\n❌ Quiz page failed to load. Check if server is running.")
