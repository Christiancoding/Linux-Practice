#!/usr/bin/env python3
"""
Simple test script to verify snapshot API endpoints are working
"""

import requests
import json

def test_snapshot_api():
    """Test the snapshot API endpoints"""
    base_url = "http://localhost:5001"  # Adjust if your server runs on a different port
    
    print("🔍 Testing Snapshot API Endpoints...")
    print("=" * 50)
    
    # Test 1: List snapshots without VM name (should fail)
    print("\n1. Testing snapshots without VM name...")
    try:
        response = requests.get(f"{base_url}/api/vm/snapshots", timeout=5)
        print(f"   Status: {response.status_code}")
        print(f"   Content-Type: {response.headers.get('content-type', 'unknown')}")
        if response.headers.get('content-type', '').startswith('application/json'):
            data = response.json()
            print(f"   Response: {json.dumps(data, indent=2)}")
        else:
            print(f"   Response (HTML): {response.text[:200]}...")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 2: List snapshots with VM name
    print("\n2. Testing snapshots with VM name...")
    try:
        response = requests.get(f"{base_url}/api/vm/snapshots?vm_name=test-vm", timeout=5)
        print(f"   Status: {response.status_code}")
        print(f"   Content-Type: {response.headers.get('content-type', 'unknown')}")
        if response.headers.get('content-type', '').startswith('application/json'):
            data = response.json()
            print(f"   Response: {json.dumps(data, indent=2)}")
        else:
            print(f"   Response (HTML): {response.text[:200]}...")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 3: Test non-existent endpoint
    print("\n3. Testing non-existent endpoint...")
    try:
        response = requests.get(f"{base_url}/api/vm/nonexistent", timeout=5)
        print(f"   Status: {response.status_code}")
        print(f"   Content-Type: {response.headers.get('content-type', 'unknown')}")
        if response.headers.get('content-type', '').startswith('application/json'):
            data = response.json()
            print(f"   Response: {json.dumps(data, indent=2)}")
        else:
            print(f"   Response (HTML): {response.text[:200]}...")
    except Exception as e:
        print(f"   Error: {e}")
    
    print("\n" + "=" * 50)
    print("✅ Testing complete!")
    print("\nIf you see HTML responses instead of JSON, that's the cause of the")
    print("'Unexpected token <' error in the frontend.")

if __name__ == "__main__":
    test_snapshot_api()
