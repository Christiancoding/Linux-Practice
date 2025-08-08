#!/usr/bin/env python3
"""
Test settings page profile functionality
"""

import requests
import json
import time

BASE_URL = "http://127.0.0.1:5000"

def test_settings_page_functionality():
    """Test the settings page profile management functionality"""
    
    print("=== Testing Settings Page Profile Functionality ===")
    
    # Create a session to maintain cookies
    session = requests.Session()
    
    # Test 1: Load the settings page to ensure it loads
    print("\n1. Loading settings page...")
    response = session.get(f"{BASE_URL}/settings")
    if response.status_code == 200:
        print("✓ Settings page loaded successfully")
    else:
        print(f"✗ Settings page failed to load: {response.status_code}")
        return
    
    # Test 2: Test profile loading API
    print("\n2. Testing profile loading via frontend API...")
    response = session.get(f"{BASE_URL}/api/profiles")
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            print("✓ Profile API successful")
            print(f"Current profiles: {list(data.get('profiles', {}).keys())}")
            current_profile = data.get('current_profile', 'anonymous')
            print(f"Current active profile: {current_profile}")
        else:
            print("✗ Profile API failed:", data.get('error'))
    else:
        print(f"✗ Profile API request failed: {response.status_code}")
        
    # Test 3: Create a new profile via the frontend API
    print("\n3. Creating a new profile...")
    test_name = f"Frontend Test User {int(time.time())}"
    response = session.post(f"{BASE_URL}/api/profiles",
                          headers={'Content-Type': 'application/json'},
                          json={'name': test_name})
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            new_user_id = data.get('user_id')
            print(f"✓ Profile created successfully: {new_user_id}")
            
            # Test 4: Switch to the new profile
            print(f"\n4. Switching to new profile...")
            response = session.post(f"{BASE_URL}/api/profiles/switch",
                                  headers={'Content-Type': 'application/json'},
                                  json={'profile_id': new_user_id})
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    print("✓ Profile switch successful")
                    
                    # Test 5: Verify the switch worked
                    print("\n5. Verifying profile switch...")
                    response = session.get(f"{BASE_URL}/api/profiles")
                    if response.status_code == 200:
                        data = response.json()
                        current_profile = data.get('current_profile')
                        if current_profile == new_user_id:
                            print("✓ Profile switch verified")
                        else:
                            print(f"✗ Profile switch not verified. Expected: {new_user_id}, Got: {current_profile}")
                else:
                    print("✗ Profile switch failed:", data.get('error'))
            else:
                print(f"✗ Profile switch request failed: {response.status_code}")
                
            # Test 6: Rename the profile
            print(f"\n6. Renaming the profile...")
            new_name = f"Renamed {test_name}"
            response = session.put(f"{BASE_URL}/api/profiles/{new_user_id}/rename",
                                 headers={'Content-Type': 'application/json'},
                                 json={'name': new_name})
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    print("✓ Profile rename successful")
                else:
                    print("✗ Profile rename failed:", data.get('error'))
            else:
                print(f"✗ Profile rename request failed: {response.status_code}")
                
            # Test 7: Delete the test profile (cleanup)
            print(f"\n7. Cleaning up test profile...")
            
            # First switch back to anonymous
            session.post(f"{BASE_URL}/api/profiles/switch",
                        headers={'Content-Type': 'application/json'},
                        json={'profile_id': 'anonymous'})
            
            # Then delete the test profile
            response = session.delete(f"{BASE_URL}/api/profiles/{new_user_id}")
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    print("✓ Test profile deleted successfully")
                else:
                    print("✗ Test profile deletion failed:", data.get('error'))
            else:
                print(f"✗ Test profile deletion request failed: {response.status_code}")
                
        else:
            print("✗ Profile creation failed:", data.get('error'))
    else:
        print(f"✗ Profile creation request failed: {response.status_code}")
    
    print("\n=== Settings Page Test Complete ===")

if __name__ == "__main__":
    test_settings_page_functionality()
