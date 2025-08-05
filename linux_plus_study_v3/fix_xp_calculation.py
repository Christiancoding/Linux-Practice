#!/usr/bin/env python3
"""
Fix XP Calculation Issue

Recalculate XP based on existing quiz data to fix the 0 XP display issue.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from services.simple_analytics import get_analytics_manager

def fix_xp_calculation():
    """Fix XP calculation for existing users"""
    print("🔧 Fixing XP Calculation")
    print("=" * 50)
    
    import json
    
    # Get data file path
    analytics = get_analytics_manager()
    data_file = analytics.data_file
    
    # Load current data directly
    with open(data_file, 'r') as f:
        data = json.load(f)
    
    print("📊 Current User Data:")
    for user_id, user_data in data.items():
        print(f"\n👤 User: {user_id}")
        print(f"   Display Name: {user_data.get('display_name', 'N/A')}")
        print(f"   Questions: {user_data['total_questions']}")
        print(f"   Correct: {user_data['correct_answers']}")
        print(f"   Incorrect: {user_data['incorrect_answers']}")
        print(f"   Current XP: {user_data['xp']}")
        
        # Calculate what XP should be
        correct_xp = user_data['correct_answers'] * 10
        incorrect_xp = user_data['incorrect_answers'] * 5
        expected_xp = correct_xp + incorrect_xp
        
        print(f"   Expected XP: {expected_xp} ({correct_xp} from correct + {incorrect_xp} from incorrect)")
        
        if user_data['xp'] != expected_xp:
            print(f"   🔧 FIXING: {user_data['xp']} → {expected_xp}")
            user_data['xp'] = expected_xp
            user_data['level'] = max(1, (expected_xp // 100) + 1)
            print(f"   📈 New Level: {user_data['level']}")
        else:
            print(f"   ✅ XP is correct")
    
    # Save the fixed data
    with open(data_file, 'w') as f:
        json.dump(data, f, indent=2, default=str)
    print(f"\n💾 Data saved to: {data_file}")
    
    return True

if __name__ == "__main__":
    success = fix_xp_calculation()
    sys.exit(0 if success else 1)
