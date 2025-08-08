#!/usr/bin/env python3
"""
Test Dashboard API Data

Debug the dashboard API to see what data it's returning.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from services.analytics_integration import get_user_analytics_summary
import requests

def test_dashboard_api():
    """Test the dashboard API endpoint."""
    print("🧪 Testing Dashboard API")
    print("=" * 50)
    
    try:
        # Test the analytics integration function directly
        print("📊 Testing Analytics Integration Function:")
        analytics_result = get_user_analytics_summary('anonymous')
        print(f"   Analytics Result: {analytics_result}")
        
        # Test the API endpoint
        print("\n🌐 Testing Dashboard API Endpoint:")
        response = requests.get('http://127.0.0.1:8081/api/dashboard')
        if response.status_code == 200:
            api_result = response.json()
            print(f"   API Result: {api_result}")
        else:
            print(f"   API Error: {response.status_code} - {response.text}")
        
        # Test analytics integration with demo user
        print("\n📊 Testing Analytics Integration with Demo User:")
        demo_analytics = get_user_analytics_summary('demo_user_001')
        print(f"   Demo User Result: {demo_analytics}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing dashboard API: {e}")
        return False

if __name__ == "__main__":
    success = test_dashboard_api()
    sys.exit(0 if success else 1)
