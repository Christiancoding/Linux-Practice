#!/usr/bin/env python3
"""
Test script for profile API functionality
"""

import requests
import json

BASE_URL = "http://127.0.0.1:5000"

def test_profile_api():
    """Test all profile API endpoints"""
    
    print("=== Testing Profile API ===")
    
    # Test 1: Get all profiles
    print("\n1. Testing GET /api/profiles")
    response = requests.get(f"{BASE_URL}/api/profiles")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
        if data.get('success'):
            print("✓ GET profiles successful")
        else:
            print("✗ GET profiles failed:", data.get('error'))
    else:
        print(f"✗ GET profiles failed with status {response.status_code}")
    
    # Test 2: Create a new profile
    print("\n2. Testing POST /api/profiles (Create Profile)")
    test_profile_name = "Test User"
    response = requests.post(f"{BASE_URL}/api/profiles", 
                           headers={'Content-Type': 'application/json'},
                           json={'name': test_profile_name})
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
        if data.get('success'):
            print("✓ Create profile successful")
            created_user_id = data.get('user_id')
        else:
            print("✗ Create profile failed:", data.get('error'))
            return
    else:
        print(f"✗ Create profile failed with status {response.status_code}")
        return
    
    # Test 3: Get profiles again to see the new one
    print("\n3. Testing GET /api/profiles (After Create)")
    response = requests.get(f"{BASE_URL}/api/profiles")
    if response.status_code == 200:
        data = response.json()
        print(f"Profiles count: {len(data.get('profiles', {}))}")
        for profile_id, profile_data in data.get('profiles', {}).items():
            print(f"  - {profile_id}: {profile_data.get('name')}")
    
    # Test 4: Rename the profile
    print(f"\n4. Testing PUT /api/profiles/{created_user_id}/rename")
    new_name = "Renamed Test User"
    response = requests.put(f"{BASE_URL}/api/profiles/{created_user_id}/rename",
                          headers={'Content-Type': 'application/json'},
                          json={'name': new_name})
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
        if data.get('success'):
            print("✓ Rename profile successful")
        else:
            print("✗ Rename profile failed:", data.get('error'))
    
    # Test 5: Switch to the new profile
    print(f"\n5. Testing POST /api/profiles/switch")
    response = requests.post(f"{BASE_URL}/api/profiles/switch",
                           headers={'Content-Type': 'application/json'},
                           json={'profile_id': created_user_id})
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
        if data.get('success'):
            print("✓ Switch profile successful")
        else:
            print("✗ Switch profile failed:", data.get('error'))
    
    # Test 6: Reset the profile
    print(f"\n6. Testing POST /api/profiles/{created_user_id}/reset")
    response = requests.post(f"{BASE_URL}/api/profiles/{created_user_id}/reset",
                           headers={'Content-Type': 'application/json'})
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
        if data.get('success'):
            print("✓ Reset profile successful")
        else:
            print("✗ Reset profile failed:", data.get('error'))
    
    # Test 7: Delete the profile
    print(f"\n7. Testing DELETE /api/profiles/{created_user_id}")
    response = requests.delete(f"{BASE_URL}/api/profiles/{created_user_id}",
                             headers={'Content-Type': 'application/json'})
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
        if data.get('success'):
            print("✓ Delete profile successful")
        else:
            print("✗ Delete profile failed:", data.get('error'))
    
    print("\n=== Profile API Test Complete ===")

if __name__ == "__main__":
    test_profile_api()
