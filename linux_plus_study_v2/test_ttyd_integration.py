#!/usr/bin/env python3
"""
Test script for ttyd integration functionality.

This script tests the automatic ttyd startup when the full terminal button is pressed.
"""

import requests
import json
import time

def test_ttyd_integration():
    """Test the ttyd integration API endpoint."""
    
    # API endpoint
    api_url = 'http://localhost:5000/api/vm/start_ttyd'
    
    # Test data
    test_data = {
        'vm_name': 'ubuntu-practice',  # Adjust as needed
        'port': 7682
    }
    
    print("🧪 Testing ttyd integration...")
    print(f"📡 API URL: {api_url}")
    print(f"📊 Test data: {json.dumps(test_data, indent=2)}")
    
    try:
        # Make the API request
        print("\n🔄 Sending request to start ttyd...")
        response = requests.post(
            api_url,
            json=test_data,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        print(f"📡 Response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"📋 Response data: {json.dumps(result, indent=2)}")
            
            if result.get('success'):
                print("✅ ttyd started successfully!")
                print(f"🌐 Terminal URL: {result.get('url', 'N/A')}")
                
                # Test if ttyd is accessible
                if 'url' in result:
                    print("\n🔍 Testing terminal accessibility...")
                    try:
                        terminal_response = requests.get(result['url'], timeout=5)
                        if terminal_response.status_code == 200:
                            print("✅ Terminal is accessible!")
                        else:
                            print(f"⚠️ Terminal returned status: {terminal_response.status_code}")
                    except requests.exceptions.RequestException as e:
                        print(f"⚠️ Could not access terminal: {e}")
                
            else:
                print(f"❌ API returned error: {result.get('error', 'Unknown error')}")
        else:
            print(f"❌ HTTP error: {response.status_code}")
            try:
                error_data = response.json()
                print(f"📋 Error data: {json.dumps(error_data, indent=2)}")
            except:
                print(f"📋 Raw response: {response.text}")
                
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

def test_vm_execution():
    """Test basic VM command execution to verify connectivity."""
    
    api_url = 'http://localhost:5000/api/vm/execute'
    
    test_data = {
        'vm_name': 'ubuntu-practice',  # Adjust as needed
        'command': 'echo "Hello from VM!"'
    }
    
    print("\n🧪 Testing basic VM connectivity...")
    print(f"📡 API URL: {api_url}")
    
    try:
        response = requests.post(
            api_url,
            json=test_data,
            headers={'Content-Type': 'application/json'},
            timeout=15
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("✅ VM is accessible!")
                print(f"📋 Output: {result.get('output', '').strip()}")
            else:
                print(f"❌ VM command failed: {result.get('error', 'Unknown error')}")
        else:
            print(f"❌ HTTP error: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")

if __name__ == "__main__":
    print("🚀 Starting ttyd integration tests...")
    print("=" * 50)
    
    # Test basic VM connectivity first
    test_vm_execution()
    
    # Test ttyd integration
    test_ttyd_integration()
    
    print("\n" + "=" * 50)
    print("🏁 Test completed!")
    print("\n💡 To manually test:")
    print("1. Open http://localhost:5000/vm_playground")
    print("2. Select a VM")
    print("3. Click the 'Full Terminal' button")
    print("4. Check if ttyd starts automatically and terminal opens")
