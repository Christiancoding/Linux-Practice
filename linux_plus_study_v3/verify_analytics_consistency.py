#!/usr/bin/env python3
"""
Verify that all analytics data is consistent across all APIs and pages
"""

import requests
import json
from colorama import init, Fore, Style

init(autoreset=True)

def verify_analytics_consistency():
    """Check that all APIs return consistent data"""
    base_url = "http://localhost:5000"
    
    print(f"{Fore.CYAN}=== Analytics Consistency Verification ==={Style.RESET_ALL}\n")
    
    # Fetch data from all endpoints
    endpoints = {
        "Dashboard": "/api/dashboard",
        "Analytics": "/api/analytics",
        "Statistics": "/api/statistics",
        "Achievements": "/api/achievements"
    }
    
    data = {}
    for name, endpoint in endpoints.items():
        try:
            response = requests.get(f"{base_url}{endpoint}")
            if response.status_code == 200:
                data[name] = response.json()
                print(f"{Fore.GREEN}✓{Style.RESET_ALL} {name} API: Connected")
            else:
                print(f"{Fore.RED}✗{Style.RESET_ALL} {name} API: Failed (Status {response.status_code})")
        except Exception as e:
            print(f"{Fore.RED}✗{Style.RESET_ALL} {name} API: Error - {e}")
    
    print(f"\n{Fore.CYAN}=== Data Consistency Check ==={Style.RESET_ALL}\n")
    
    # Check key metrics across all endpoints
    metrics_to_check = [
        ("Total Questions", [
            ("Dashboard", "total_questions"),
            ("Analytics", "stats.total_questions"),
            ("Statistics", "overall.total_attempts")
        ]),
        ("Correct Answers", [
            ("Dashboard", "total_correct"),
            ("Analytics", "stats.total_correct"),
            ("Statistics", "overall.total_correct")
        ]),
        ("Accuracy", [
            ("Dashboard", "accuracy"),
            ("Analytics", "stats.accuracy"),
            ("Statistics", "overall.overall_accuracy")
        ]),
        ("Level", [
            ("Dashboard", "level"),
            ("Analytics", "stats.level"),
            ("Achievements", "level")
        ]),
        ("XP", [
            ("Dashboard", "xp"),
            ("Analytics", "stats.xp"),
            ("Achievements", "total_points")
        ])
    ]
    
    all_consistent = True
    
    for metric_name, paths in metrics_to_check:
        print(f"\n{Fore.YELLOW}{metric_name}:{Style.RESET_ALL}")
        values = []
        
        for api_name, path in paths:
            if api_name not in data:
                continue
                
            # Navigate the path
            value = data[api_name]
            for key in path.split('.'):
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    value = None
                    break
            
            if value is not None:
                # Round floats for comparison
                if isinstance(value, float):
                    value = round(value, 1)
                values.append((api_name, value))
                print(f"  {api_name}: {value}")
        
        # Check consistency
        if values:
            unique_values = set(v[1] for v in values)
            if len(unique_values) == 1:
                print(f"  {Fore.GREEN}✓ Consistent{Style.RESET_ALL}")
            else:
                print(f"  {Fore.RED}✗ INCONSISTENT! Values: {unique_values}{Style.RESET_ALL}")
                all_consistent = False
    
    print(f"\n{Fore.CYAN}=== Final Result ==={Style.RESET_ALL}")
    if all_consistent:
        print(f"{Fore.GREEN}✓ All analytics data is CONSISTENT across all pages!{Style.RESET_ALL}")
    else:
        print(f"{Fore.RED}✗ Analytics data is INCONSISTENT - needs fixing!{Style.RESET_ALL}")
    
    return all_consistent

if __name__ == "__main__":
    verify_analytics_consistency()