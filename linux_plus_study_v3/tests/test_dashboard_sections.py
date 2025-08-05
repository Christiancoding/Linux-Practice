#!/usr/bin/env python3
"""
Dashboard Sections Verification Test

This test verifies that all dashboard sections have the data they need:
- Study Activity
- Recent Achievements  
- Performance Overview
- Study Streak
"""

import json
import requests
from services.simple_analytics import get_analytics_manager

def test_dashboard_sections():
    """Test all dashboard sections have proper data"""
    print("🔍 DASHBOARD SECTIONS VERIFICATION")
    print("=" * 50)
    
    # Get current dashboard data
    try:
        response = requests.get('http://localhost:5000/api/dashboard', timeout=5)
        if response.status_code != 200:
            print(f"❌ Dashboard API failed: {response.status_code}")
            return
        
        data = response.json()
        print("✅ Dashboard API responding")
        
    except Exception as e:
        print(f"❌ Error getting dashboard data: {e}")
        return
    
    # Test Study Activity Section
    print("\n📊 STUDY ACTIVITY")
    print("-" * 20)
    
    study_activity = data.get('study_activity', {})
    if study_activity:
        daily_activity = study_activity.get('daily_activity', [])
        weekly_summary = study_activity.get('weekly_summary', {})
        
        print(f"✅ Daily activity data: {len(daily_activity)} days")
        print(f"✅ Weekly summary: {weekly_summary.get('total_questions', 0)} questions, {weekly_summary.get('active_days', 0)} active days")
        
        # Show today's activity
        if daily_activity:
            today = daily_activity[-1]
            print(f"📅 Today: {today.get('questions', 0)} questions, {today.get('accuracy', 0)}% accuracy")
    else:
        print("❌ No study activity data")
    
    # Test Recent Achievements Section
    print("\n🏆 RECENT ACHIEVEMENTS")
    print("-" * 20)
    
    recent_achievements = data.get('recent_achievements', [])
    if recent_achievements:
        print(f"✅ {len(recent_achievements)} recent achievements:")
        for achievement in recent_achievements:
            print(f"   {achievement.get('icon', '🏆')} {achievement.get('name', 'Unknown')}: {achievement.get('description', 'No description')}")
    else:
        print("❌ No recent achievements data")
    
    # Test Performance Overview Section
    print("\n📈 PERFORMANCE OVERVIEW")
    print("-" * 20)
    
    performance_overview = data.get('performance_overview', {})
    if performance_overview:
        topics = performance_overview.get('topics', [])
        difficulty_breakdown = performance_overview.get('difficulty_breakdown', [])
        trend = performance_overview.get('overall_trend', 'unknown')
        strongest = performance_overview.get('strongest_topic', 'None')
        weakest = performance_overview.get('weakest_topic', 'None')
        
        print(f"✅ Overall trend: {trend}")
        print(f"✅ Strongest topic: {strongest}")
        print(f"✅ Weakest topic: {weakest}")
        print(f"✅ Topic breakdown: {len(topics)} topics tracked")
        print(f"✅ Difficulty breakdown: {len(difficulty_breakdown)} levels")
        
        if topics:
            print("📋 Top topics:")
            for topic in topics[:3]:
                print(f"   • {topic.get('topic', 'Unknown')}: {topic.get('accuracy', 0)}% ({topic.get('correct', 0)}/{topic.get('questions', 0)})")
                
        if difficulty_breakdown:
            print("📊 Difficulty distribution:")
            for diff in difficulty_breakdown:
                print(f"   • {diff.get('difficulty', 'Unknown')}: {diff.get('questions', 0)} questions ({diff.get('percentage', 0)}%)")
    else:
        print("❌ No performance overview data")
    
    # Test Study Streak Section  
    print("\n🔥 STUDY STREAK")
    print("-" * 20)
    
    streak_details = data.get('study_streak_details', {})
    streak = data.get('streak', 0)
    
    if streak_details:
        current_streak = streak_details.get('current_streak', 0)
        longest_streak = streak_details.get('longest_streak', 0)
        last_activity = streak_details.get('last_activity', 'Never')
        
        print(f"✅ Current streak: {current_streak} days")
        print(f"✅ Longest streak: {longest_streak} days")
        print(f"✅ Last activity: {last_activity}")
        
        if current_streak > 0:
            print(f"🔥 You're on a {current_streak}-day study streak!")
        else:
            print("💡 Start your study streak by answering questions daily!")
    else:
        print("❌ No study streak data")
    
    # Summary Report
    print("\n📋 SUMMARY REPORT")
    print("=" * 30)
    
    sections_working = 0
    total_sections = 4
    
    if study_activity:
        sections_working += 1
        print("✅ Study Activity: Working")
    else:
        print("❌ Study Activity: Missing data")
    
    if recent_achievements:
        sections_working += 1
        print("✅ Recent Achievements: Working")
    else:
        print("❌ Recent Achievements: Missing data")
    
    if performance_overview:
        sections_working += 1  
        print("✅ Performance Overview: Working")
    else:
        print("❌ Performance Overview: Missing data")
    
    if streak_details:
        sections_working += 1
        print("✅ Study Streak: Working")
    else:
        print("❌ Study Streak: Missing data")
    
    print(f"\n🎯 RESULT: {sections_working}/{total_sections} dashboard sections working")
    
    if sections_working == total_sections:
        print("🎉 ALL DASHBOARD SECTIONS ARE WORKING!")
    else:
        print(f"⚠️  {total_sections - sections_working} sections need attention")
    
    return sections_working == total_sections

def simulate_more_activity():
    """Simulate more quiz activity to test features"""
    print("\n🎮 SIMULATING MORE ACTIVITY")
    print("-" * 30)
    
    analytics = get_analytics_manager()
    
    # Add more quiz results
    new_questions = [
        ("User Management", True, "intermediate"),
        ("Networking", False, "advanced"),
        ("Security", True, "advanced"),
        ("System Monitoring", True, "beginner"),
    ]
    
    for topic, correct, difficulty in new_questions:
        analytics.update_quiz_results("anonymous", correct, topic, difficulty)
        print(f"  {'✓' if correct else '✗'} {topic} ({difficulty})")
    
    print(f"✅ Added {len(new_questions)} more questions")

if __name__ == '__main__':
    # Test current state
    success = test_dashboard_sections()
    
    if success:
        print("\n" + "=" * 50)
        print("✅ All dashboard sections verified!")
        print("Check your browser - all sections should have data")
    else:
        print("\n" + "=" * 50)
        print("⚠️  Some sections missing data. Simulating more activity...")
        simulate_more_activity()
        
        print("\n🔄 Re-testing after adding more data...")
        test_dashboard_sections()
    
    print("\n" + "=" * 50)
    print("Dashboard sections test complete!")
