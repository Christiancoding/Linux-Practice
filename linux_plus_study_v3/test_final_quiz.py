#!/usr/bin/env python3
"""Final comprehensive test of quiz functionality"""

import requests
import json

def test_complete_quiz_flow():
    """Test the complete quiz flow"""
    print("🧪 COMPREHENSIVE QUIZ FUNCTIONALITY TEST")
    print("=" * 50)
    
    BASE_URL = "http://127.0.0.1:5000"
    
    # Test 1: Quiz page loads
    print("\n1️⃣ Testing quiz page access...")
    try:
        response = requests.get(f"{BASE_URL}/quiz")
        if response.status_code == 200:
            print("✅ Quiz page loads successfully")
            
            # Check for essential elements
            html = response.text
            checks = [
                ('Standard mode card', 'selectMode(\'standard\')'),
                ('Timed mode card', 'selectMode(\'timed\')'), 
                ('Survival mode card', 'selectMode(\'survival\')'),
                ('Exam mode card', 'selectMode(\'exam\')'),
                ('Start quiz button', 'onclick="startQuiz()"'),
                ('Category dropdown', 'id="quiz-category"'),
                ('Questions dropdown', 'id="num-questions"'),
                ('JavaScript functions', 'function selectMode'),
                ('JavaScript functions', 'function startQuiz')
            ]
            
            for name, pattern in checks:
                if pattern in html:
                    print(f"   ✅ {name}: Found")
                else:
                    print(f"   ❌ {name}: Missing")
        else:
            print(f"❌ Quiz page failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Quiz page error: {e}")
        return False
    
    # Test 2: API endpoints
    print("\n2️⃣ Testing API endpoints...")
    
    api_tests = [
        {
            'name': 'Standard Quiz',
            'endpoint': '/api/start_quiz',
            'data': {'mode': 'standard', 'category': 'All Categories', 'num_questions': 10}
        },
        {
            'name': 'Timed Challenge', 
            'endpoint': '/api/start_timed_challenge',
            'data': {'mode': 'timed', 'category': 'All Categories', 'num_questions': 10}
        },
        {
            'name': 'Survival Mode',
            'endpoint': '/api/start_survival_mode', 
            'data': {'mode': 'survival', 'category': 'All Categories'}
        },
        {
            'name': 'Exam Simulation',
            'endpoint': '/api/start_exam_mode',
            'data': {'mode': 'exam', 'category': 'All Categories'}
        }
    ]
    
    api_success = True
    for test in api_tests:
        try:
            response = requests.post(
                f"{BASE_URL}{test['endpoint']}", 
                json=test['data'],
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    print(f"   ✅ {test['name']}: Working")
                else:
                    print(f"   ❌ {test['name']}: {data.get('error', 'Unknown error')}")
                    api_success = False
            else:
                print(f"   ❌ {test['name']}: HTTP {response.status_code}")
                api_success = False
        except Exception as e:
            print(f"   ❌ {test['name']}: {e}")
            api_success = False
    
    # Test 3: Question retrieval
    print("\n3️⃣ Testing question retrieval...")
    try:
        # Start a quiz first
        requests.post(f"{BASE_URL}/api/start_quiz", json={'mode': 'standard', 'category': 'All Categories', 'num_questions': 5})
        
        # Get a question
        response = requests.get(f"{BASE_URL}/api/get_question")
        if response.status_code == 200:
            data = response.json()
            if 'question' in data and 'options' in data:
                print("   ✅ Question retrieval: Working")
            else:
                print("   ❌ Question retrieval: Invalid response format")
                api_success = False
        else:
            print(f"   ❌ Question retrieval: HTTP {response.status_code}")
            api_success = False
    except Exception as e:
        print(f"   ❌ Question retrieval: {e}")
        api_success = False
    
    # Summary
    print("\n📊 TEST SUMMARY")
    print("=" * 30)
    
    if api_success:
        print("✅ All backend functionality is working correctly!")
        print("\n🎯 If quiz buttons still don't work, the issue is frontend:")
        print("   1. Open http://127.0.0.1:5000/quiz in browser")
        print("   2. Open Developer Tools (F12)")
        print("   3. Check Console tab for JavaScript errors")
        print("   4. Try clicking mode cards and start button")
        print("   5. Check if onclick events are firing")
        
        print("\n🔧 Common frontend fixes:")
        print("   • Hard refresh (Ctrl+Shift+R) to clear cache")
        print("   • Verify CSS is not blocking clicks")
        print("   • Check for JavaScript errors in console")
        print("   • Ensure all DOM elements are loaded")
        
        return True
    else:
        print("❌ Backend issues found - fix these first")
        return False

if __name__ == "__main__":
    success = test_complete_quiz_flow()
    
    if success:
        print("\n🎉 Backend is ready! Quiz buttons should work.")
        print("   If they don't, it's a frontend issue - check browser console.")
    else:
        print("\n⚠️  Backend issues need to be resolved first.")
