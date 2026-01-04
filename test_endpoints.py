#!/usr/bin/env python3
"""Test script to verify topology endpoint works"""

import sys
import time
sys.path.insert(0, '/d/Projects/Research/iot/IOT-project')

try:
    from controller import app
    
    with app.test_client() as client:
        print("Testing /get_data endpoint...")
        response = client.get('/get_data')
        print(f"  Status: {response.status_code}")
        print(f"  Data length: {len(response.data)}")
        if response.status_code == 200:
            print("  ✅ /get_data works")
        else:
            print(f"  ❌ /get_data failed: {response.data}")
        
        print("\nTesting /get_topology_with_mac endpoint...")
        response = client.get('/get_topology_with_mac')
        print(f"  Status: {response.status_code}")
        print(f"  Data length: {len(response.data)}")
        if response.status_code == 200:
            import json
            data = json.loads(response.data)
            print(f"  Nodes: {len(data.get('nodes', []))}")
            print(f"  Edges: {len(data.get('edges', []))}")
            print("  ✅ /get_topology_with_mac works")
        else:
            print(f"  ❌ /get_topology_with_mac failed: {response.data}")
        
        print("\nTesting /get_health_metrics endpoint...")
        response = client.get('/get_health_metrics')
        print(f"  Status: {response.status_code}")
        print(f"  Data length: {len(response.data)}")
        if response.status_code == 200:
            print("  ✅ /get_health_metrics works")
        else:
            print(f"  ❌ /get_health_metrics failed: {response.data}")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
