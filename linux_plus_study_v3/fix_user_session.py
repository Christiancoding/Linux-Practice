#!/usr/bin/env python3
"""
Fix User Session - Restore Anonymous User

This script fixes the issue where random users were created instead of using the anonymous user.
It also provides a way to reset the session back to anonymous.
"""

import json
import os

def reset_user_session():
    """Reset to anonymous user and clean up any random users"""
    data_file = os.path.join(os.path.dirname(__file__), 'data', 'user_analytics.json')
    
    try:
        with open(data_file, 'r') as f:
            data = json.load(f)
        
        print("📊 Current user profiles:")
        for user_id, user_data in data.items():
            print(f"  - {user_id}: {user_data.get('total_questions', 0)} questions, "
                  f"{user_data.get('display_name', 'No name')}")
        
        # Find any random users (user_XXXXXXXX pattern)
        random_users = [uid for uid in data.keys() if uid.startswith('user_') and uid != 'anonymous']
        
        if random_users:
            print(f"\n🧹 Found {len(random_users)} random user(s) to clean up:")
            for user_id in random_users:
                print(f"  - Removing: {user_id}")
                # Move any data to anonymous if anonymous has no progress
                if data['anonymous']['total_questions'] == 0 and data[user_id]['total_questions'] > 0:
                    print(f"    📤 Moving {data[user_id]['total_questions']} questions to anonymous")
                    # Keep the display name and created date from anonymous
                    display_name = data['anonymous'].get('display_name', 'Anonymous')
                    created_date = data['anonymous'].get('created_date')
                    
                    # Copy all progress data
                    data['anonymous'] = data[user_id].copy()
                    data['anonymous']['display_name'] = display_name
                    if created_date:
                        data['anonymous']['created_date'] = created_date
                
                # Remove the random user
                del data[user_id]
        
        # Save the cleaned data
        with open(data_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        print("\n✅ User session fixed!")
        print("📊 Final user profiles:")
        for user_id, user_data in data.items():
            print(f"  - {user_id}: {user_data.get('total_questions', 0)} questions, "
                  f"{user_data.get('display_name', 'No name')}")
        
        print("\n🎯 Recommendations:")
        print("1. Refresh your browser to clear any cached session data")
        print("2. Your progress has been restored to the anonymous profile")
        print("3. The system will now correctly default to 'anonymous' instead of creating random users")
        
    except Exception as e:
        print(f"❌ Error fixing user session: {e}")

if __name__ == "__main__":
    print("🔧 Linux+ Study App - User Session Fix")
    print("=" * 50)
    reset_user_session()
