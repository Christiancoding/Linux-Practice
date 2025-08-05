#!/usr/bin/env python3
"""
Validation script to test all API endpoints and ensure correct data flow
"""

import requests
import json

def test_endpoints():
    base_url = "http://127.0.0.1:8081"
    
    endpoints = {
        "dashboard": f"{base_url}/api/dashboard",
        "achievements": f"{base_url}/api/achievements", 
        "statistics": f"{base_url}/api/statistics",
        "leaderboard": f"{base_url}/api/leaderboard"
    }
    
    print("API Endpoint Validation")
    print("=" * 50)
    
    for name, url in endpoints.items():
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                print(f"✓ {name:<12}: SUCCESS")
                
                # Show key metrics for dashboard
                if name == "dashboard":
                    print(f"  Level: {data.get('level', 'N/A')}")
                    print(f"  XP: {data.get('xp', 'N/A')}")
                    print(f"  Progress: {data.get('level_progress', 'N/A'):.1f}%")
                    print(f"  Streak: {data.get('streak', 'N/A')}")
                elif name == "achievements":
                    stats = data.get('stats', {})
                    print(f"  Unlocked: {stats.get('unlocked', 'N/A')}/{stats.get('total', 'N/A')}")
                    print(f"  Level: {stats.get('level', 'N/A')}")
                    print(f"  XP: {stats.get('xp', 'N/A')}")
                elif name == "statistics":
                    overall = data.get('overall', {})
                    print(f"  Accuracy: {overall.get('overall_accuracy', 'N/A'):.1f}%")
                    print(f"  Total Correct: {overall.get('total_correct', 'N/A')}")
                
            else:
                print(f"✗ {name:<12}: FAILED (Status: {response.status_code})")
                
        except Exception as e:
            print(f"✗ {name:<12}: ERROR - {str(e)}")
        
        print()

if __name__ == "__main__":
    test_endpoints()
