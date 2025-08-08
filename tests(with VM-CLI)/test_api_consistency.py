#!/usr/bin/env python3
"""
Comprehensive API Consistency Test

This test verifies that all dashboard tabs show consistent data by:
1. Simulating quiz activity 
2. Testing all API endpoints
3. Verifying data consistency across tabs
"""

import json
import requests
import time
from services.simple_analytics import get_analytics_manager

def simulate_quiz_activity():
    """Simulate some quiz activity to generate test data"""
    print("📊 Simulating Quiz Activity...")
    
    analytics = get_analytics_manager()
    
    # Simulate answering questions
    test_data = [
        ("Linux Commands", True, "beginner"),
        ("File Permissions", False, "intermediate"), 
        ("Shell Scripting", True, "advanced"),
        ("Process Management", True, "intermediate"),
        ("Network Configuration", False, "advanced"),
    ]
    
    for topic, correct, difficulty in test_data:
        analytics.update_quiz_results("anonymous", correct, topic, difficulty)
        print(f"  {'✓' if correct else '✗'} {topic} ({difficulty})")
    
    print(f"✅ Simulated {len(test_data)} questions")
    return len(test_data)

def test_api_endpoint(endpoint, description):
    """Test a single API endpoint"""
    try:
        print(f"\n🔍 Testing {description}")
        response = requests.get(f'http://localhost:5000{endpoint}', timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ {endpoint}: Success")
            return data
        else:
            print(f"❌ {endpoint}: HTTP {response.status_code}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ {endpoint}: Request failed - {e}")
        return None

def extract_key_metrics(data, source):
    """Extract key metrics from API response"""
    metrics = {}
    
    try:
        if source == "dashboard":
            metrics = {
                'questions_answered': data.get('questions_answered', 0),
                'total_correct': data.get('total_correct', 0),
                'accuracy': data.get('accuracy', 0),
                'level': data.get('level', 1),
                'xp': data.get('xp', 0),
                'total_sessions': data.get('total_sessions', 0)
            }
        elif source == "analytics":
            metrics = {
                'questions_answered': data.get('total_questions', 0),
                'total_correct': data.get('correct_answers', 0),
                'accuracy': data.get('accuracy', 0),
                'total_sessions': data.get('total_sessions', 0)
            }
        elif source == "achievements":
            stats = data.get('stats', {})
            metrics = {
                'questions_answered': data.get('questions_answered', 0),
                'accuracy': stats.get('accuracy', 0),
                'level': stats.get('level', 1),
                'xp': stats.get('xp', 0)
            }
        elif source == "statistics":
            overall = data.get('overall', {})
            metrics = {
                'questions_answered': overall.get('total_questions', 0),
                'total_correct': overall.get('correct_answers', 0),
                'accuracy': overall.get('overall_accuracy', 0),
                'level': overall.get('level', 1),
                'xp': overall.get('xp', 0)
            }
        elif source == "review":
            stats = data.get('stats', {})
            metrics = {
                'questions_answered': stats.get('total_questions', 0),
                'total_correct': stats.get('correct_answers', 0),
                'accuracy': stats.get('accuracy', 0)
            }
            
    except Exception as e:
        print(f"⚠️  Error extracting metrics from {source}: {e}")
        
    return metrics

def compare_metrics(metrics_dict):
    """Compare metrics across all sources"""
    print("\n📊 CONSISTENCY ANALYSIS")
    print("=" * 50)
    
    # Get all unique metric keys
    all_keys = set()
    for metrics in metrics_dict.values():
        all_keys.update(metrics.keys())
    
    consistent = True
    
    for key in sorted(all_keys):
        values = {}
        for source, metrics in metrics_dict.items():
            if key in metrics:
                values[source] = metrics[key]
        
        if len(set(values.values())) <= 1:
            # All values are the same
            value = list(values.values())[0] if values else "N/A"
            print(f"✅ {key:20} | {value} (consistent)")
        else:
            # Values differ
            print(f"❌ {key:20} | INCONSISTENT:")
            for source, value in values.items():
                print(f"   └─ {source:15}: {value}")
            consistent = False
    
    return consistent

def main():
    """Run comprehensive API consistency test"""
    print("🔍 COMPREHENSIVE API CONSISTENCY TEST")
    print("=" * 60)
    
    # Wait for server to start
    print("⏳ Waiting for server to start...")
    time.sleep(3)
    
    # Simulate quiz activity to generate test data
    total_questions = simulate_quiz_activity()
    
    # Test all API endpoints
    api_tests = [
        ('/api/dashboard', "Dashboard API"),
        ('/api/analytics', "Analytics API"), 
        ('/api/achievements', "Achievements API"),
        ('/api/statistics', "Statistics API"),
        ('/api/review_incorrect', "Review API")
    ]
    
    api_data = {}
    
    for endpoint, description in api_tests:
        data = test_api_endpoint(endpoint, description)
        if data:
            api_data[description.replace(" API", "").lower()] = data
    
    if not api_data:
        print("❌ No API endpoints responded successfully!")
        return
    
    # Extract key metrics from each API
    print("\n📋 EXTRACTING KEY METRICS")
    print("-" * 30)
    
    metrics_by_source = {}
    
    for source, data in api_data.items():
        metrics = extract_key_metrics(data, source)
        metrics_by_source[source] = metrics
        print(f"{source:15}: {len(metrics)} metrics extracted")
    
    # Compare consistency
    consistent = compare_metrics(metrics_by_source)
    
    # Final report
    print("\n🎯 FINAL REPORT")
    print("=" * 30)
    
    if consistent:
        print("✅ ALL APIS ARE CONSISTENT!")
        print("   All dashboard tabs should show the same data")
    else:
        print("❌ INCONSISTENCIES DETECTED!")
        print("   Different tabs will show conflicting data")
    
    # Show expected values
    print(f"\n📊 Expected Values (from simulation):")
    print(f"   Questions: {total_questions}")
    print(f"   Correct: 3 (60% accuracy)")
    print(f"   Incorrect: 2")
    
    # Show actual dashboard values
    if 'dashboard' in metrics_by_source:
        dashboard = metrics_by_source['dashboard']
        print(f"\n📱 Actual Dashboard Values:")
        print(f"   Questions: {dashboard.get('questions_answered', 'N/A')}")
        print(f"   Correct: {dashboard.get('total_correct', 'N/A')}")
        print(f"   Accuracy: {dashboard.get('accuracy', 'N/A')}%")
        print(f"   Level: {dashboard.get('level', 'N/A')}")
        print(f"   XP: {dashboard.get('xp', 'N/A')}")

if __name__ == '__main__':
    main()
    print("\n" + "=" * 60)
    print("Test complete! Check your browser tabs for consistency.")
