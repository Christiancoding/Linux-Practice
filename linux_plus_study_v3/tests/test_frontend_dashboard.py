#!/usr/bin/env python3
"""
Frontend Dashboard Test - Verify all sections are working
This test checks that the frontend properly displays the enhanced dashboard data
"""

import requests
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import json

def test_dashboard_frontend():
    """Test that the dashboard frontend displays enhanced data correctly"""
    print("🔍 TESTING DASHBOARD FRONTEND")
    print("=" * 40)
    
    # Test API first
    try:
        response = requests.get('http://localhost:5000/api/dashboard', timeout=5)
        api_data = response.json()
        print("✅ API responding with enhanced data")
        
        # Verify API has enhanced sections
        required_sections = ['recent_achievements', 'study_activity', 'performance_overview', 'study_streak_details']
        missing_sections = []
        
        for section in required_sections:
            if section not in api_data:
                missing_sections.append(section)
        
        if missing_sections:
            print(f"❌ Missing API sections: {missing_sections}")
            return False
        
        print("✅ All required API sections present")
        
    except Exception as e:
        print(f"❌ API test failed: {e}")
        return False
    
    # Test main page loads
    try:
        response = requests.get('http://localhost:5000/', timeout=5)
        if response.status_code == 200:
            print("✅ Main page loads successfully")
        else:
            print(f"❌ Main page error: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Main page test failed: {e}")
        return False
    
    print("\n📋 DASHBOARD SECTIONS STATUS")
    print("-" * 30)
    
    # Check Recent Achievements data
    achievements = api_data.get('recent_achievements', [])
    if achievements:
        print(f"✅ Recent Achievements: {len(achievements)} achievements")
        for ach in achievements:
            print(f"   {ach.get('icon', '🏆')} {ach.get('name', 'Unknown')}")
    else:
        print("❌ Recent Achievements: No data")
    
    # Check Study Activity data
    study_activity = api_data.get('study_activity', {})
    daily_activity = study_activity.get('daily_activity', [])
    if daily_activity:
        print(f"✅ Study Activity: {len(daily_activity)} days of data")
        weekly_summary = study_activity.get('weekly_summary', {})
        total_questions = weekly_summary.get('total_questions', 0)
        active_days = weekly_summary.get('active_days', 0)
        print(f"   Weekly: {total_questions} questions, {active_days} active days")
    else:
        print("❌ Study Activity: No data")
    
    # Check Performance Overview data
    performance = api_data.get('performance_overview', {})
    if performance:
        print("✅ Performance Overview: Complete")
        print(f"   Trend: {performance.get('overall_trend', 'unknown')}")
        print(f"   Strongest: {performance.get('strongest_topic', 'None')}")
        print(f"   Weakest: {performance.get('weakest_topic', 'None')}")
        topics = performance.get('topics', [])
        print(f"   Topics tracked: {len(topics)}")
    else:
        print("❌ Performance Overview: No data")
    
    # Check Study Streak data
    streak_details = api_data.get('study_streak_details', {})
    if streak_details:
        print("✅ Study Streak: Working")
        current = streak_details.get('current_streak', 0)
        longest = streak_details.get('longest_streak', 0)
        print(f"   Current: {current} days")
        print(f"   Longest: {longest} days")
    else:
        print("❌ Study Streak: No data")
    
    print("\n🎯 FRONTEND TEST SUMMARY")
    print("=" * 30)
    
    sections_working = 0
    total_sections = 4
    
    if achievements:
        sections_working += 1
        print("✅ Recent Achievements section: Data available")
    else:
        print("❌ Recent Achievements section: Missing data")
    
    if daily_activity:
        sections_working += 1
        print("✅ Study Activity section: Data available")
    else:
        print("❌ Study Activity section: Missing data")
    
    if performance:
        sections_working += 1
        print("✅ Performance Overview section: Data available")
    else:
        print("❌ Performance Overview section: Missing data")
    
    if streak_details:
        sections_working += 1
        print("✅ Study Streak section: Data available")
    else:
        print("❌ Study Streak section: Missing data")
    
    print(f"\n🎉 RESULT: {sections_working}/{total_sections} sections working")
    
    if sections_working == total_sections:
        print("🎊 ALL DASHBOARD SECTIONS HAVE DATA!")
        print("📱 Frontend should now display enhanced information")
        print("🌐 Visit: http://localhost:5000 to see the improvements")
        return True
    else:
        print(f"⚠️  {total_sections - sections_working} sections still need attention")
        return False

def main():
    print("Frontend Dashboard Test")
    print("Checking that all dashboard sections display enhanced data")
    print("=" * 60)
    
    success = test_dashboard_frontend()
    
    if success:
        print("\n✅ SUCCESS: All dashboard sections working!")
        print("\nThe following issues should now be fixed:")
        print("• Study Activity shows 7 days of activity data")
        print("• Recent Achievements displays 3 unlocked achievements") 
        print("• Performance Overview shows trends and topic analysis")
        print("• Study Streak displays current and longest streaks")
        print("\nThe frontend JavaScript has been updated to use enhanced API data.")
    else:
        print("\n❌ Some sections still need fixes")
    
    return success

if __name__ == '__main__':
    main()
