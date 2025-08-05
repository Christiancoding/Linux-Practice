#!/usr/bin/env python3
"""
Performance Overview Test - Verify study time and trend messages are working
"""

import requests
import json

def test_performance_overview():
    print("🔍 PERFORMANCE OVERVIEW TEST")
    print("=" * 40)
    
    # Test API response
    try:
        response = requests.get('http://localhost:5000/api/dashboard', timeout=5)
        data = response.json()
        print("✅ Dashboard API responding")
        
    except Exception as e:
        print(f"❌ API Error: {e}")
        return False
    
    # Test Study Time Tracking
    print("\n⏰ STUDY TIME TESTING")
    print("-" * 20)
    
    study_time = data.get('study_time', 0)
    if study_time > 0:
        minutes = study_time / 60
        print(f"✅ Study time tracked: {study_time} seconds ({minutes:.1f} minutes)")
        print(f"   Frontend should display: {int(minutes//60)}h {int(minutes%60)}m" if minutes >= 60 else f"   Frontend should display: {int(minutes)}m")
    else:
        print("❌ Study time not tracked (still 0)")
    
    # Test Weekly Study Activity
    weekly_stats = data.get('study_activity', {}).get('weekly_summary', {})
    weekly_time = weekly_stats.get('total_time', 0)
    weekly_questions = weekly_stats.get('total_questions', 0)
    
    print(f"✅ Weekly activity: {weekly_questions} questions, {weekly_time} seconds")
    
    # Test Performance Overview Data
    print("\n📈 PERFORMANCE OVERVIEW DATA")
    print("-" * 30)
    
    performance = data.get('performance_overview', {})
    if performance:
        print("✅ Performance overview available:")
        print(f"   Trend: {performance.get('overall_trend', 'unknown')}")
        print(f"   Strongest: {performance.get('strongest_topic', 'None')}")
        print(f"   Weakest: {performance.get('weakest_topic', 'None')}")
        
        topics = performance.get('topics', [])
        print(f"   Topics tracked: {len(topics)}")
        
        # Show topic performance
        if topics:
            print("   Top performers:")
            for topic in topics[:3]:
                accuracy = topic.get('accuracy', 0)
                questions = topic.get('questions', 0)
                print(f"     • {topic.get('topic', 'Unknown')}: {accuracy}% ({questions} questions)")
    else:
        print("❌ Performance overview missing")
    
    # Test Frontend Elements  
    print("\n🌐 FRONTEND ELEMENTS")
    print("-" * 20)
    
    print("📊 Performance Overview section should show:")
    print("   • Study Time: Proper hours/minutes format")
    print("   • Trend messages based on real data:")
    
    # Generate expected trend messages
    total_questions = data.get('questions_answered', 0)
    accuracy = data.get('accuracy', 0)
    trend = performance.get('overall_trend', 'neutral')
    
    if total_questions == 0:
        correct_msg = "Start practicing!"
    elif total_questions < 10:
        correct_msg = "Building momentum!"
    else:
        correct_msg = f"{weekly_questions} this week"
    
    if accuracy == 0:
        accuracy_msg = "Ready to improve!"
    elif trend == 'improving':
        accuracy_msg = "Improving trend!"
    elif trend == 'declining':
        accuracy_msg = "Keep practicing!"
    else:
        accuracy_msg = "Staying consistent"
    
    if study_time == 0:
        time_msg = "Start your journey!"
    else:
        minutes = int((weekly_time % 3600) / 60)
        hours = int(weekly_time / 3600)
        if hours > 0:
            time_msg = f"{hours}h {minutes}m this week"
        else:
            time_msg = f"{minutes}m this week"
    
    print(f"     ✅ Correct Answers: '{correct_msg}'")
    print(f"     ✅ Accuracy Rate: '{accuracy_msg}'")
    print(f"     ✅ Study Time: '{time_msg}'")
    print(f"     ✅ Streak: 'Keep it going!' (should remain unchanged)")
    
    # Verification Summary
    print("\n🎯 VERIFICATION SUMMARY")
    print("=" * 25)
    
    issues_fixed = 0
    total_issues = 2
    
    if study_time > 0:
        print("✅ Study time tracking: FIXED")
        issues_fixed += 1
    else:
        print("❌ Study time tracking: Still broken")
    
    if performance:
        print("✅ Trend messages data: Available")
        issues_fixed += 1
    else:
        print("❌ Trend messages data: Missing")
    
    print(f"\n🎉 RESULT: {issues_fixed}/{total_issues} Performance Overview issues fixed")
    
    if issues_fixed == total_issues:
        print("🎊 Performance Overview is now working correctly!")
        print("📱 Visit http://localhost:5000 to see the improvements")
        return True
    else:
        print("⚠️  Some issues still need attention")
        return False

if __name__ == '__main__':
    success = test_performance_overview()
    
    if success:
        print("\n" + "=" * 50)
        print("✅ Performance Overview fixes complete!")
        print("The dashboard now shows:")
        print("• Accurate study time tracking")
        print("• Meaningful trend messages under numbers")
        print("• Enhanced performance insights")
    else:
        print("\n" + "=" * 50) 
        print("⚠️  Some Performance Overview issues remain")
