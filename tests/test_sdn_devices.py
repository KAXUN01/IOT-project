#!/usr/bin/env python3
"""
SDN Test Script for IoT Security Framework
Simulates IoT devices to test SDN functionality
"""

import requests
import json
import time
import random
import threading
from datetime import datetime

class IoTDeviceSimulator:
    def __init__(self, device_id, controller_url="http://localhost:5000"):
        self.device_id = device_id
        self.controller_url = controller_url
        self.token = None
        self.mac_address = f"AA:BB:CC:DD:EE:{device_id[-1]}{device_id[-1]}"
        self.running = False
        
    def get_token(self):
        """Request authentication token from controller"""
        try:
            response = requests.post(f"{self.controller_url}/get_token", 
                                  json={"device_id": self.device_id, "mac_address": self.mac_address})
            if response.status_code == 200:
                data = response.json()
                self.token = data.get('token')
                print(f"[{self.device_id}] Token received: {self.token[:8]}...")
                return True
            else:
                print(f"[{self.device_id}] Token request failed: {response.text}")
                return False
        except Exception as e:
            print(f"[{self.device_id}] Token request error: {e}")
            return False
    
    def send_data(self):
        """Send sensor data to controller"""
        if not self.token:
            return False
            
        try:
            sensor_data = {
                "device_id": self.device_id,
                "token": self.token,
                "timestamp": str(int(time.time())),
                "data": str(random.uniform(20.0, 30.0))  # Simulated temperature
            }
            
            response = requests.post(f"{self.controller_url}/data", json=sensor_data)
            if response.status_code == 200:
                result = response.json()
                if result.get('status') == 'accepted':
                    print(f"[{self.device_id}] Data accepted: {sensor_data['data']}°C")
                    return True
                else:
                    print(f"[{self.device_id}] Data rejected: {result.get('reason', 'Unknown')}")
                    return False
            else:
                print(f"[{self.device_id}] Data send failed: {response.text}")
                return False
        except Exception as e:
            print(f"[{self.device_id}] Data send error: {e}")
            return False
    
    def run_device(self, interval=5, max_retries=3):
        """Run device simulation"""
        print(f"[{self.device_id}] Starting device simulation...")
        
        retry_count = 0
        while retry_count < max_retries:
            if self.get_token():
                break
            print(f"[{self.device_id}] Retrying token request ({retry_count + 1}/{max_retries})")
            retry_count += 1
            time.sleep(5)  # Wait 5 seconds between retries
        
        if not self.token:
            print(f"[{self.device_id}] Failed to get token after {max_retries} attempts, stopping device")
            return
        
        self.running = True
        while self.running:
            if not self.send_data():
                # If data send fails, try to get a new token
                if not self.get_token():
                    print(f"[{self.device_id}] Token refresh failed, stopping device")
                    self.running = False
                    return
            time.sleep(interval)
    
    def stop_device(self):
        """Stop device simulation"""
        self.running = False
        print(f"[{self.device_id}] Device stopped")

class SDNTester:
    def __init__(self, controller_url="http://localhost:5000"):
        self.controller_url = controller_url
        self.devices = []
        
    def create_test_topology(self):
        """Create a test network topology with multiple devices"""
        print("🔧 Creating SDN Test Topology...")
        
        # Create simulated IoT devices
        device_ids = ["ESP32_2", "ESP32_3"]  # Removed ESP32_4 as it's not authorized
        
        for device_id in device_ids:
            device = IoTDeviceSimulator(device_id, self.controller_url)
            self.devices.append(device)
        
        print(f"✅ Created {len(self.devices)} test devices")
        return self.devices
    
    def start_devices(self):
        """Start all devices in separate threads"""
        print("🚀 Starting test devices...")
        
        threads = []
        for device in self.devices:
            thread = threading.Thread(target=device.run_device, args=(5,))
            thread.daemon = True
            thread.start()
            threads.append(thread)
            time.sleep(1)  # Stagger device starts
        
        return threads
    
    def test_sdn_policies(self):
        """Test SDN policy enforcement"""
        print("🧪 Testing SDN Policies...")
        
        # Test rate limiting
        print("Testing rate limiting...")
        device = self.devices[0]
        for i in range(65):  # Exceed rate limit of 60 packets/minute
            device.send_data()
            time.sleep(0.1)
        
        # Test session timeout
        print("Testing session timeout...")
        time.sleep(310)  # Wait for 5-minute session timeout
        device.send_data()
        
    def monitor_dashboard(self):
        """Monitor dashboard metrics"""
        print("📊 Monitoring Dashboard Metrics...")
        
        try:
            # Get device data
            response = requests.get(f"{self.controller_url}/get_data")
            if response.status_code == 200:
                data = response.json()
                print("Device Status:")
                for device_id, status in data.items():
                    print(f"  {device_id}: {status['packets']} packets, Rate: {status['rate_limit_status']}")
            
            # Get topology
            response = requests.get(f"{self.controller_url}/get_topology_with_mac")
            if response.status_code == 200:
                topology = response.json()
                print(f"Network Topology: {len(topology['nodes'])} nodes, {len(topology['edges'])} edges")
            
            # Get SDN metrics
            response = requests.get(f"{self.controller_url}/get_sdn_metrics")
            if response.status_code == 200:
                metrics = response.json()
                print(f"SDN Metrics: Latency={metrics['control_plane_latency']}ms, "
                      f"Throughput={metrics['data_plane_throughput']}Mbps, "
                      f"Enforcement={metrics['policy_enforcement_rate']}%")
                      
        except Exception as e:
            print(f"Dashboard monitoring error: {e}")
    
    def test_device_authorization(self):
        """Test device authorization/revocation"""
        print("🔐 Testing Device Authorization...")
        
        # Test revoking device access
        print("Revoking ESP32_4 access...")
        try:
            response = requests.post(f"{self.controller_url}/update", 
                                  data={"device_id": "ESP32_4", "action": "revoke"})
            if response.status_code == 200:
                print("✅ ESP32_4 access revoked")
            
            # Try to get token for revoked device
            device = IoTDeviceSimulator("ESP32_4", self.controller_url)
            if not device.get_token():
                print("✅ Revoked device cannot get token")
            
        except Exception as e:
            print(f"Authorization test error: {e}")
    
    def run_comprehensive_test(self):
        """Run comprehensive SDN test"""
        print("🎯 Starting Comprehensive SDN Test")
        print("=" * 50)
        
        # Create topology
        self.create_test_topology()
        
        # Start devices
        threads = self.start_devices()
        
        print("📈 Monitoring system continuously...")
        print("Press Ctrl+C to stop the devices...")
        
        try:
            while True:
                self.monitor_dashboard()
                time.sleep(5)
        except KeyboardInterrupt:
            # Stop devices when Ctrl+C is pressed
            print("\n🛑 Stopping test devices...")
            for device in self.devices:
                device.stop_device()
            
            print("✅ SDN Test Complete!")
            print("🌐 Check the dashboard at: http://localhost:5000")

def main():
    print("🔐 IoT Security Framework Test Suite")
    print("=" * 40)
    
    # Check if controller is running
    try:
        response = requests.get("http://localhost:5000")
        if response.status_code == 200:
            print("✅ IoT Security Controller is running")
        else:
            print("❌ IoT Security Controller is not responding")
            return
    except:
        print("❌ Cannot connect to IoT Security Controller")
        print("Please start the controller first: python controller.py")
        return
    
    # Create and run SDN tester
    tester = SDNTester()
    tester.run_comprehensive_test()

if __name__ == "__main__":
    main()
