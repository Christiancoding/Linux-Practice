#!/usr/bin/env python3
"""
Debug analytics and profile issues:
1. Profile renaming not reflected in analytics
2. New quiz data not showing
3. Question count mismatches
4. Streak counter not updating
5. Confusing reset options
"""

import json
import os
from flask import Flask, session
from services.simple_analytics import get_analytics_manager

def test_profile_analytics_integration():
    """Test the integration between profiles and analytics"""
    print("🔍 Testing Profile Analytics Integration...")
    
    # Initialize analytics manager
    analytics = get_analytics_manager()
    
    # Get all profiles
    profiles = analytics.get_all_profiles()
    print(f"\n📋 Current Profiles: {list(profiles.keys())}")
    
    for profile_id, profile_data in profiles.items():
        print(f"\n👤 Profile: {profile_id}")
        print(f"   Display Name: {profile_data.get('display_name', 'N/A')}")
        print(f"   Total Questions: {profile_data.get('total_questions', 0)}")
        print(f"   Accuracy: {profile_data.get('accuracy', 0)}%")
        print(f"   Last Activity: {profile_data.get('last_activity', 'Never')}")
        
        # Get detailed user data
        user_data = analytics.get_user_data(profile_id)
        print(f"   Detailed Data Keys: {list(user_data.keys())}")

def test_session_user_mapping():
    """Test how sessions map to users"""
    print("\n🔍 Testing Session-User Mapping...")
    
    # Test Flask session simulation
    app = Flask(__name__)
    app.secret_key = 'test'
    
    with app.test_request_context():
        # Simulate different session states
        test_cases = [
            ('anonymous', {}),
            ('test_user', {'user_id': 'test_user'}),
            ('renamed_user', {'user_id': 'renamed_user'})
        ]
        
        for label, session_data in test_cases:
            print(f"\n📝 Testing session: {label}")
            session.clear()
            session.update(session_data)
            
            user_id = session.get('user_id', 'anonymous')
            print(f"   Session user_id: {user_id}")
            
            # Test analytics lookup
            analytics = get_analytics_manager()
            user_data = analytics.get_user_data(user_id)
            print(f"   Analytics found: {user_data is not None}")
            if user_data:
                print(f"   Display name: {user_data.get('display_name', 'N/A')}")

def test_analytics_data_file():
    """Examine the actual analytics data file"""
    print("\n🔍 Testing Analytics Data File...")
    
    # Find analytics data file
    analytics = get_analytics_manager()
    data_file = analytics.data_file
    print(f"📁 Data file location: {data_file}")
    
    if os.path.exists(data_file):
        with open(data_file, 'r') as f:
            data = json.load(f)
        
        print(f"📊 Data file contents ({len(data)} profiles):")
        for profile_id, profile_data in data.items():
            print(f"   {profile_id}: {profile_data.get('display_name', 'No display name')}")
            print(f"      Questions: {profile_data.get('total_questions', 0)}")
            print(f"      Accuracy: {profile_data.get('accuracy', 0)}%")
            print(f"      Sessions: {len(profile_data.get('session_history', []))}")
    else:
        print("❌ Analytics data file not found!")

def test_quiz_controller_integration():
    """Test how quiz controller interacts with analytics"""
    print("\n🔍 Testing Quiz Controller Integration...")
    
    try:
        from controllers.quiz_controller import QuizController
        from models.game_state import GameState
        
        # Initialize game state
        game_state = GameState()
        quiz_controller = QuizController(game_state)
        
        print(f"✅ Quiz controller initialized")
        print(f"   Session score: {quiz_controller.session_score}")
        print(f"   Session total: {quiz_controller.session_total}")
        print(f"   Current streak: {quiz_controller.current_streak}")
        
        # Test session status
        status = quiz_controller.get_session_status()
        print(f"   Session status: {status}")
        
    except Exception as e:
        print(f"❌ Failed to test quiz controller: {e}")

def check_question_count_issues():
    """Check for question count discrepancies"""
    print("\n🔍 Checking Question Count Issues...")
    
    try:
        # Load questions data
        questions_file = "linux_plus_questions.json"
        if os.path.exists(questions_file):
            with open(questions_file, 'r') as f:
                questions = json.load(f)
            
            print(f"📚 Total questions in file: {len(questions)}")
            
            # Count by category
            categories = {}
            for q in questions:
                cat = q.get('category', 'Unknown')
                categories[cat] = categories.get(cat, 0) + 1
            
            print("📊 Questions by category:")
            for cat, count in categories.items():
                print(f"   {cat}: {count}")
                
        else:
            print("❌ Questions file not found!")
            
    except Exception as e:
        print(f"❌ Failed to check questions: {e}")

def main():
    """Run all diagnostic tests"""
    print("🚀 Starting Analytics Issues Diagnosis...")
    print("=" * 50)
    
    test_profile_analytics_integration()
    test_session_user_mapping() 
    test_analytics_data_file()
    test_quiz_controller_integration()
    check_question_count_issues()
    
    print("\n" + "=" * 50)
    print("✅ Diagnosis complete!")

if __name__ == "__main__":
    main()
