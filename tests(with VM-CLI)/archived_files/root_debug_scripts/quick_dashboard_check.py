#!/usr/bin/env python3
"""
Quick Dashboard Check - Verify frontend is working
"""

import requests
import json

def check_dashboard_quick():
    print("🔍 QUICK DASHBOARD CHECK")
    print("=" * 30)
    
    # Test both API endpoints
    endpoints = ['/api/dashboard', '/api/achievements', '/api/analytics']
    
    for endpoint in endpoints:
        try:
            response = requests.get(f'http://localhost:5000{endpoint}', timeout=3)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ {endpoint}: OK")
                
                if endpoint == '/api/dashboard':
                    # Quick check of key sections
                    achievements = len(data.get('recent_achievements', []))
                    activity_days = len(data.get('study_activity', {}).get('daily_activity', []))
                    has_performance = bool(data.get('performance_overview', {}))
                    has_streak = bool(data.get('study_streak_details', {}))
                    
                    print(f"   📊 Achievements: {achievements}")
                    print(f"   📅 Activity Days: {activity_days}")
                    print(f"   📈 Performance: {'Yes' if has_performance else 'No'}")
                    print(f"   🔥 Streak Details: {'Yes' if has_streak else 'No'}")
                    
            else:
                print(f"❌ {endpoint}: HTTP {response.status_code}")
        except Exception as e:
            print(f"❌ {endpoint}: Error - {e}")
    
    print("\n🌐 BROWSER TEST")
    print("-" * 15)
    try:
        response = requests.get('http://localhost:5000/', timeout=3)
        if response.status_code == 200:
            print("✅ Main page: Loads successfully")
            print("📱 Dashboard should show enhanced data:")
            print("   • Recent Achievements with icons")
            print("   • Study Activity calendar with tooltips")
            print("   • Performance metrics and trends")
            print("   • Study streak information")
        else:
            print(f"❌ Main page: HTTP {response.status_code}")
    except Exception as e:
        print(f"❌ Main page: Error - {e}")
    
    print(f"\n🎯 VERIFICATION COMPLETE")
    print("Visit http://localhost:5000 to see the dashboard!")

if __name__ == '__main__':
    check_dashboard_quick()
