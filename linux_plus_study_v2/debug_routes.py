#!/usr/bin/env python3
"""
Debug script to check what routes are registered in the Flask app
"""

import requests
import json

def check_flask_routes():
    """Check what routes are registered"""
    base_url = "http://localhost:5001"
    
    print("🔍 Checking Flask Route Registration...")
    print("=" * 50)
    
    # Check various VM endpoints to see which ones work
    endpoints = [
        "/api/vm/list",
        "/api/vm/status", 
        "/api/vm/snapshots?vm_name=ubuntu-practice",
        "/api/vm/create_snapshot",
        "/api/vm/restore_snapshot",
        "/api/vm/delete_snapshot"
    ]
    
    for endpoint in endpoints:
        print(f"\n🔗 Testing: {endpoint}")
        try:
            if endpoint.startswith("/api/vm/create") or endpoint.startswith("/api/vm/restore") or endpoint.startswith("/api/vm/delete"):
                # POST endpoints
                response = requests.post(f"{base_url}{endpoint}", 
                                       json={"test": "data"}, 
                                       timeout=5)
            else:
                # GET endpoints  
                response = requests.get(f"{base_url}{endpoint}", timeout=5)
                
            print(f"   Status: {response.status_code}")
            print(f"   Content-Type: {response.headers.get('content-type', 'unknown')}")
            
            if response.headers.get('content-type', '').startswith('application/json'):
                try:
                    data = response.json()
                    print(f"   Response: {json.dumps(data, indent=2)[:200]}...")
                except:
                    print(f"   Response: {response.text[:200]}...")
            else:
                print(f"   Response (non-JSON): {response.text[:200]}...")
                
        except Exception as e:
            print(f"   Error: {e}")
    
    print("\n" + "=" * 50)
    print("✅ Route check complete!")

if __name__ == "__main__":
    check_flask_routes()
