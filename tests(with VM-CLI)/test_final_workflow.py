#!/usr/bin/env python3
"""
Final test script to verify profile management works correctly
"""

import requests
import time
import json

BASE_URL = "http://127.0.0.1:5000"

def test_complete_user_workflow():
    """Test a complete user workflow for profile management"""
    
    print("🧪 Testing Complete User Workflow for Profile Management")
    print("=" * 60)
    
    session = requests.Session()
    
    # Step 1: Load settings page
    print("\n1️⃣ Loading settings page...")
    response = session.get(f"{BASE_URL}/settings")
    if response.status_code == 200:
        print("✅ Settings page loaded successfully")
    else:
        print(f"❌ Settings page failed: {response.status_code}")
        return False
    
    # Step 2: Load profiles (simulating what happens when page loads)
    print("\n2️⃣ Loading profiles (automatic on page load)...")
    response = session.get(f"{BASE_URL}/api/profiles")
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            print(f"✅ Profiles loaded: {list(data.get('profiles', {}).keys())}")
            print(f"📍 Current profile: {data.get('current_profile')}")
        else:
            print(f"❌ Profile loading failed: {data.get('error')}")
            return False
    else:
        print(f"❌ Profile API failed: {response.status_code}")
        return False
    
    # Step 3: Create a new profile (simulating user input)
    print("\n3️⃣ Creating a new profile...")
    test_profile_name = f"Test User {int(time.time())}"
    
    response = session.post(f"{BASE_URL}/api/profiles", 
                          headers={'Content-Type': 'application/json'},
                          json={'name': test_profile_name})
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            new_user_id = data.get('user_id')
            print(f"✅ Profile created: {new_user_id}")
        else:
            print(f"❌ Profile creation failed: {data.get('error')}")
            return False
    else:
        print(f"❌ Profile creation request failed: {response.status_code}")
        return False
    
    # Step 4: Verify the new profile appears in the list
    print("\n4️⃣ Verifying new profile appears in list...")
    response = session.get(f"{BASE_URL}/api/profiles")
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            profiles = data.get('profiles', {})
            if new_user_id in profiles:
                profile_data = profiles[new_user_id]
                print(f"✅ New profile found: {profile_data.get('name')}")
            else:
                print(f"❌ New profile not found in list")
                return False
        else:
            print(f"❌ Failed to verify profiles: {data.get('error')}")
            return False
    
    # Step 5: Switch to the new profile
    print("\n5️⃣ Switching to new profile...")
    response = session.post(f"{BASE_URL}/api/profiles/switch",
                          headers={'Content-Type': 'application/json'},
                          json={'profile_id': new_user_id})
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            print("✅ Profile switch successful")
        else:
            print(f"❌ Profile switch failed: {data.get('error')}")
            return False
    else:
        print(f"❌ Profile switch request failed: {response.status_code}")
        return False
    
    # Step 6: Verify the switch worked
    print("\n6️⃣ Verifying profile switch...")
    response = session.get(f"{BASE_URL}/api/profiles")
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            current_profile = data.get('current_profile')
            if current_profile == new_user_id:
                print(f"✅ Switch verified: Current profile is {current_profile}")
            else:
                print(f"❌ Switch failed: Expected {new_user_id}, got {current_profile}")
                return False
    
    # Step 7: Rename the profile
    print("\n7️⃣ Renaming the profile...")
    new_name = f"Renamed {test_profile_name}"
    response = session.put(f"{BASE_URL}/api/profiles/{new_user_id}/rename",
                         headers={'Content-Type': 'application/json'},
                         json={'name': new_name})
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            print(f"✅ Profile renamed to: {new_name}")
        else:
            print(f"❌ Profile rename failed: {data.get('error')}")
            return False
    
    # Step 8: Verify the rename worked
    print("\n8️⃣ Verifying profile rename...")
    response = session.get(f"{BASE_URL}/api/profiles")
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            profiles = data.get('profiles', {})
            if new_user_id in profiles:
                profile_name = profiles[new_user_id].get('name')
                if profile_name == new_name:
                    print(f"✅ Rename verified: {profile_name}")
                else:
                    print(f"❌ Rename failed: Expected '{new_name}', got '{profile_name}'")
                    return False
    
    # Step 9: Switch back to anonymous profile before cleanup
    print("\n9️⃣ Switching back to anonymous profile...")
    response = session.post(f"{BASE_URL}/api/profiles/switch",
                          headers={'Content-Type': 'application/json'},
                          json={'profile_id': 'anonymous'})
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            print("✅ Switched back to anonymous")
        else:
            print(f"❌ Switch back failed: {data.get('error')}")
    
    # Step 10: Clean up - delete the test profile
    print("\n🔟 Cleaning up test profile...")
    response = session.delete(f"{BASE_URL}/api/profiles/{new_user_id}")
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            print("✅ Test profile deleted successfully")
        else:
            print(f"❌ Test profile deletion failed: {data.get('error')}")
    
    # Final verification
    print("\n🎯 Final verification...")
    response = session.get(f"{BASE_URL}/api/profiles")
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            profiles = data.get('profiles', {})
            if new_user_id not in profiles:
                print("✅ Test profile successfully removed")
                print(f"📊 Final profile count: {len(profiles)}")
            else:
                print("❌ Test profile still exists after deletion")
                return False
    
    print("\n" + "=" * 60)
    print("🎉 ALL TESTS PASSED! Profile management is working correctly!")
    print("\n📋 Summary of what works:")
    print("   ✅ Loading settings page")
    print("   ✅ Loading profiles automatically") 
    print("   ✅ Creating new profiles")
    print("   ✅ Switching between profiles")
    print("   ✅ Renaming profiles")
    print("   ✅ Deleting profiles")
    print("   ✅ Session persistence")
    print("\n💡 If users are having issues, they should:")
    print("   1. Go to Settings page")
    print("   2. Click on the 'Profiles' tab")
    print("   3. Profiles will load automatically")
    print("   4. Use the 'Create' button to add new profiles")
    print("   5. Use the action buttons to manage profiles")
    
    return True

if __name__ == "__main__":
    try:
        success = test_complete_user_workflow()
        if success:
            print("\n✅ TEST SUITE COMPLETED SUCCESSFULLY")
        else:
            print("\n❌ TEST SUITE FAILED")
    except Exception as e:
        print(f"\n💥 TEST SUITE ERROR: {e}")
        import traceback
        traceback.print_exc()
