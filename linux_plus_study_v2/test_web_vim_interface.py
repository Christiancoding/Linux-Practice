#!/usr/bin/env python3
"""
Test script to verify vim works through the web interface API.
"""

import requests
import json
import time

def test_web_interface_vim():
    """Test vim command execution through the web interface."""
    
    # Web interface API endpoint
    api_url = 'http://localhost:5000/api/vm/execute'
    
    print("Testing vim command through web interface...")
    
    # Test 1: Simple vim command that should auto-quit
    print("\n1. Testing vim command with auto-quit...")
    payload = {
        'vm_name': 'ubuntu-practice',
        'command': 'vim test_web_vim.txt'
    }
    
    try:
        response = requests.post(api_url, json=payload, timeout=30)
        result = response.json()
        
        print(f"Status Code: {response.status_code}")
        print(f"Success: {result.get('success', False)}")
        print(f"Exit Status: {result.get('exit_status', 'N/A')}")
        print(f"Output Length: {len(result.get('output', ''))}")
        print(f"Error: {result.get('error', 'None')}")
        
        if result.get('success'):
            print("✅ Vim command executed successfully through web interface!")
        else:
            print("❌ Vim command failed through web interface")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    
    # Test 2: Verify the file was touched (even if not edited)
    print("\n2. Checking if file was created...")
    payload = {
        'vm_name': 'ubuntu-practice',
        'command': 'ls -la test_web_vim.txt 2>/dev/null || echo "File not found"'
    }
    
    try:
        response = requests.post(api_url, json=payload, timeout=10)
        result = response.json()
        
        print(f"File check result: {result.get('output', 'N/A').strip()}")
        
    except Exception as e:
        print(f"❌ File check failed: {e}")
    
    # Test 3: Test a non-interactive command for comparison
    print("\n3. Testing non-interactive command for comparison...")
    payload = {
        'vm_name': 'ubuntu-practice',
        'command': 'echo "This is a test" && ls -la /tmp'
    }
    
    try:
        response = requests.post(api_url, json=payload, timeout=10)
        result = response.json()
        
        print(f"Non-interactive command success: {result.get('success', False)}")
        print(f"Non-interactive output length: {len(result.get('output', ''))}")
        
    except Exception as e:
        print(f"❌ Non-interactive test failed: {e}")

if __name__ == '__main__':
    test_web_interface_vim()
