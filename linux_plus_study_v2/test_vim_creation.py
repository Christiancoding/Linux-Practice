#!/usr/bin/env python3
"""
Test script to verify vim file creation through web interface.
"""

import requests
import json
import time

def test_vim_file_creation():
    """Test vim file creation through web interface."""
    
    api_url = 'http://localhost:5000/api/vm/execute'
    
    print("Testing vim file creation through web interface...")
    
    # Test 1: Check current directory contents before
    print("\n1. Checking current directory before vim...")
    payload = {
        'vm_name': 'ubuntu-practice',
        'command': 'pwd && ls -la test_vim_web*.txt 2>/dev/null || echo "No test files found"'
    }
    
    try:
        response = requests.post(api_url, json=payload, timeout=10)
        result = response.json()
        print(f"Before: {result.get('output', '').strip()}")
    except Exception as e:
        print(f"❌ Check failed: {e}")
    
    # Test 2: Use vim to create and edit a file
    print("\n2. Using vim to create a file...")
    # This will use our interactive SSH method with TTY
    payload = {
        'vm_name': 'ubuntu-practice',
        'command': 'vim test_vim_web_created.txt'
    }
    
    try:
        response = requests.post(api_url, json=payload, timeout=30)
        result = response.json()
        
        print(f"Vim execution success: {result.get('success', False)}")
        print(f"Exit status: {result.get('exit_status', 'N/A')}")
        print(f"Output length: {len(result.get('output', ''))}")
        print(f"Stderr: {result.get('error', 'None')}")
        
        # Show first few lines of output to see what happened
        output = result.get('output', '')
        if output:
            lines = output.split('\n')[:10]  # First 10 lines
            print("Output preview:")
            for line in lines:
                print(f"  {line}")
                
    except Exception as e:
        print(f"❌ Vim test failed: {e}")
    
    # Test 3: Check if file was created
    print("\n3. Checking if file was created...")
    payload = {
        'vm_name': 'ubuntu-practice',
        'command': 'ls -la test_vim_web_created.txt 2>/dev/null && echo "File exists!" || echo "File not found"'
    }
    
    try:
        response = requests.post(api_url, json=payload, timeout=10)
        result = response.json()
        print(f"File check: {result.get('output', '').strip()}")
    except Exception as e:
        print(f"❌ File check failed: {e}")
    
    # Test 4: Test other interactive commands
    print("\n4. Testing nano command...")
    payload = {
        'vm_name': 'ubuntu-practice',
        'command': 'nano --version'
    }
    
    try:
        response = requests.post(api_url, json=payload, timeout=10)
        result = response.json()
        print(f"Nano test success: {result.get('success', False)}")
        print(f"Nano version info: {result.get('output', '').strip()[:100]}...")
    except Exception as e:
        print(f"❌ Nano test failed: {e}")

if __name__ == '__main__':
    test_vim_file_creation()
