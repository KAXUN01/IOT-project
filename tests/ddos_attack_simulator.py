#!/usr/bin/env python3
"""
DDoS Attack Simulation Script
Simulates various types of DDoS attacks to test ML-based detection
"""

import requests
import time
import random
import threading
import json
from datetime import datetime
import argparse

class DDoSAttackSimulator:
    def __init__(self, target_url="http://localhost:5000", device_id="ESP32_2"):
        self.target_url = target_url
        self.device_id = device_id
        self.attack_running = False
        self.attack_threads = []
        
    def authenticate_device(self):
        """Authenticate the attacking device"""
        try:
            response = requests.post(f"{self.target_url}/get_token", 
                                  json={"device_id": self.device_id})
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Device {self.device_id} authenticated. Token: {data['token'][:10]}...")
                return data['token']
            else:
                print(f"❌ Authentication failed: {response.status_code}")
                return None
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            return None
    
    def send_normal_packet(self, token):
        """Send a normal packet"""
        packet_data = {
            "device_id": self.device_id,
            "token": token,
            "data": 1,  # Required field
            "timestamp": datetime.now().isoformat(),
            "size": random.randint(64, 512),
            "protocol": 6,  # TCP
            "src_port": random.randint(1024, 65535),
            "dst_port": 80,
            "rate": 1.0,  # Normal packet rate
            "duration": 1.0,  # Normal duration
            "bps": 1000,  # Normal bits per second
            "pps": 1.0,  # Normal packets per second
            "tcp_flags": 16,  # ACK flag
            "window_size": 8192,
            "ttl": 64,
            "fragment_offset": 0,
            "ip_length": random.randint(64, 512),
            "tcp_length": random.randint(20, 40),
            "udp_length": 0
        }
        
        try:
            response = requests.post(f"{self.target_url}/data", 
                                  json=packet_data,
                                  headers={"Authorization": f"Bearer {token}"})
            return response.status_code == 200
        except:
            return False
    
    def send_attack_packet(self, token, attack_type="volume"):
        """Send an attack packet with malicious characteristics"""
        
        if attack_type == "volume":
            # High volume attack - many large packets
            packet_data = {
                "device_id": self.device_id,
                "token": token,
                "data": 1,  # Required field
                "timestamp": datetime.now().isoformat(),
                "size": random.randint(1000, 1500),  # Large packets
                "protocol": 6,  # TCP
                "src_port": random.randint(1024, 65535),
                "dst_port": 80,
                "rate": 1000.0,  # High packet rate
                "duration": 0.1,  # Short duration bursts
                "bps": 10000000,  # High bits per second
                "pps": 10000.0,  # High packets per second
                "tcp_flags": 2,  # SYN flag
                "window_size": 8192,
                "ttl": 64,
                "fragment_offset": 0,
                "ip_length": random.randint(1000, 1500),
                "tcp_length": random.randint(20, 40),
                "udp_length": 0
            }
            
        elif attack_type == "rate":
            # High rate attack - rapid packet sending
            packet_data = {
                "device_id": self.device_id,
                "token": token,
                "data": 1,  # Required field
                "timestamp": datetime.now().isoformat(),
                "size": random.randint(64, 128),
                "protocol": 6,  # TCP
                "src_port": random.randint(1024, 65535),
                "dst_port": 80,
                "rate": 2000.0,  # Very high packet rate
                "duration": 0.05,  # Very short duration bursts
                "bps": 20000000,  # Very high bits per second
                "pps": 20000.0,  # Very high packets per second
                "tcp_flags": 2,  # SYN flag
                "window_size": 8192,
                "ttl": 64,
                "fragment_offset": 0,
                "ip_length": random.randint(64, 128),
                "tcp_length": random.randint(20, 40),
                "udp_length": 0
            }
            
        elif attack_type == "protocol":
            # Protocol attack - unusual packet characteristics
            packet_data = {
                "device_id": self.device_id,
                "sensor_data": {
                    "temperature": random.uniform(20, 30),
                    "humidity": random.uniform(40, 60),
                    "pressure": random.uniform(1000, 1020)
                },
                "packet_size": random.randint(64, 512),
                "protocol": 6,  # TCP
                "src_port": random.randint(1024, 65535),
                "dst_port": 80,
                "flags": "SYN",
                "rate": 1500.0,  # High packet rate
                "duration": 0.08,  # Short duration bursts
                "bps": 15000000,  # High bits per second
                "pps": 15000.0,  # High packets per second
                "timestamp": datetime.now().isoformat()
            }
            
        elif attack_type == "amplification":
            # Amplification attack - spoofed source with large response
            packet_data = {
                "device_id": self.device_id,
                "sensor_data": {
                    "temperature": random.uniform(20, 30),
                    "humidity": random.uniform(40, 60),
                    "pressure": random.uniform(1000, 1020)
                },
                "packet_size": random.randint(64, 128),
                "protocol": 6,  # TCP
                "src_port": random.randint(1024, 65535),
                "dst_port": 80,
                "amplification_factor": random.uniform(10, 50),
                "spoofed_source": f"192.168.{random.randint(1,254)}.{random.randint(1,254)}",
                "rate": 1200.0,  # High packet rate
                "duration": 0.1,  # Short duration bursts
                "bps": 12000000,  # High bits per second
                "pps": 12000.0,  # High packets per second
                "timestamp": datetime.now().isoformat()
            }
        
        try:
            response = requests.post(f"{self.target_url}/data", 
                                  json=packet_data,
                                  headers={"Authorization": f"Bearer {token}"})
            return response.status_code == 200
        except:
            return False
    
    def volume_attack(self, token, duration=30, intensity="medium"):
        """Simulate volume-based DDoS attack"""
        print(f"🚨 Starting VOLUME DDoS Attack ({intensity} intensity) for {duration}s")
        
        if intensity == "low":
            packets_per_second = 10
            packet_size_range = (800, 1200)
        elif intensity == "medium":
            packets_per_second = 25
            packet_size_range = (1000, 1500)
        else:  # high
            packets_per_second = 50
            packet_size_range = (1200, 1500)
        
        start_time = time.time()
        packet_count = 0
        
        while time.time() - start_time < duration and self.attack_running:
            # Send burst of large packets
            for _ in range(packets_per_second):
                if self.send_attack_packet(token, "volume"):
                    packet_count += 1
                time.sleep(0.1)  # Small delay between bursts
            
            time.sleep(0.1)  # Brief pause between bursts
        
        print(f"✅ Volume attack completed. Sent {packet_count} packets")
    
    def rate_attack(self, token, duration=30, intensity="medium"):
        """Simulate rate-based DDoS attack"""
        print(f"🚨 Starting RATE DDoS Attack ({intensity} intensity) for {duration}s")
        
        if intensity == "low":
            packets_per_second = 20
        elif intensity == "medium":
            packets_per_second = 50
        else:  # high
            packets_per_second = 100
        
        start_time = time.time()
        packet_count = 0
        
        while time.time() - start_time < duration and self.attack_running:
            # Send rapid burst of packets
            for _ in range(packets_per_second):
                if self.send_attack_packet(token, "rate"):
                    packet_count += 1
                time.sleep(1/packets_per_second)  # Maintain rate
            
            time.sleep(0.1)  # Brief pause
        
        print(f"✅ Rate attack completed. Sent {packet_count} packets")
    
    def protocol_attack(self, token, duration=30, intensity="medium"):
        """Simulate protocol-based DDoS attack"""
        print(f"🚨 Starting PROTOCOL DDoS Attack ({intensity} intensity) for {duration}s")
        
        if intensity == "low":
            packets_per_second = 15
        elif intensity == "medium":
            packets_per_second = 30
        else:  # high
            packets_per_second = 60
        
        start_time = time.time()
        packet_count = 0
        
        while time.time() - start_time < duration and self.attack_running:
            # Send protocol-specific attack packets
            for _ in range(packets_per_second):
                if self.send_attack_packet(token, "protocol"):
                    packet_count += 1
                time.sleep(1/packets_per_second)
            
            time.sleep(0.1)
        
        print(f"✅ Protocol attack completed. Sent {packet_count} packets")
    
    def amplification_attack(self, token, duration=30, intensity="medium"):
        """Simulate amplification-based DDoS attack"""
        print(f"🚨 Starting AMPLIFICATION DDoS Attack ({intensity} intensity) for {duration}s")
        
        if intensity == "low":
            packets_per_second = 10
        elif intensity == "medium":
            packets_per_second = 25
        else:  # high
            packets_per_second = 40
        
        start_time = time.time()
        packet_count = 0
        
        while time.time() - start_time < duration and self.attack_running:
            # Send amplification attack packets
            for _ in range(packets_per_second):
                if self.send_attack_packet(token, "amplification"):
                    packet_count += 1
                time.sleep(1/packets_per_second)
            
            time.sleep(0.1)
        
        print(f"✅ Amplification attack completed. Sent {packet_count} packets")
    
    def mixed_attack(self, token, duration=60):
        """Simulate mixed attack combining multiple techniques"""
        print(f"🚨 Starting MIXED DDoS Attack for {duration}s")
        
        start_time = time.time()
        total_packets = 0
        
        while time.time() - start_time < duration and self.attack_running:
            # Alternate between different attack types
            attack_types = ["volume", "rate", "protocol", "amplification"]
            attack_type = random.choice(attack_types)
            
            # Run each attack for 10-15 seconds
            attack_duration = random.randint(10, 15)
            attack_start = time.time()
            
            print(f"   Switching to {attack_type.upper()} attack for {attack_duration}s")
            
            while time.time() - attack_start < attack_duration and self.attack_running:
                if self.send_attack_packet(token, attack_type):
                    total_packets += 1
                time.sleep(random.uniform(0.01, 0.1))  # Variable timing
        
        print(f"✅ Mixed attack completed. Sent {total_packets} packets")
    
    def stealth_attack(self, token, duration=120):
        """Simulate stealth attack that gradually increases intensity"""
        print(f"🚨 Starting STEALTH DDoS Attack for {duration}s")
        
        start_time = time.time()
        packet_count = 0
        
        while time.time() - start_time < duration and self.attack_running:
            # Gradually increase attack intensity
            progress = (time.time() - start_time) / duration
            intensity = min(progress * 100, 50)  # Max 50 packets per second
            
            packets_per_second = max(1, int(intensity))
            
            for _ in range(packets_per_second):
                if self.send_attack_packet(token, "volume"):
                    packet_count += 1
                time.sleep(1/packets_per_second)
            
            time.sleep(0.1)
        
        print(f"✅ Stealth attack completed. Sent {packet_count} packets")
    
    def check_ml_detections(self):
        """Check ML engine detections"""
        try:
            response = requests.get(f"{self.target_url}/ml/detections")
            if response.status_code == 200:
                data = response.json()
                detections = data.get('detections', [])
                
                # Count recent attacks
                recent_attacks = [d for d in detections if d.get('is_attack', False)]
                print(f"📊 ML Engine Status: {len(recent_attacks)} recent attacks detected")
                
                if recent_attacks:
                    print("🚨 Recent Attack Detections:")
                    for attack in recent_attacks[-5:]:  # Show last 5
                        print(f"   - {attack.get('attack_type', 'Unknown')} "
                              f"(Confidence: {attack.get('confidence', 0)*100:.1f}%)")
                
                return len(recent_attacks)
        except Exception as e:
            print(f"❌ Error checking ML detections: {e}")
        
        return 0
    
    def run_attack(self, attack_type="volume", duration=30, intensity="medium"):
        """Run the specified attack type"""
        print(f"\n🔐 DDoS Attack Simulator Starting...")
        print(f"Target: {self.target_url}")
        print(f"Device: {self.device_id}")
        print(f"Attack Type: {attack_type.upper()}")
        print(f"Duration: {duration}s")
        print(f"Intensity: {intensity}")
        print("="*50)
        
        # Authenticate device
        token = self.authenticate_device()
        if not token:
            print("❌ Cannot proceed without authentication")
            return
        
        # Send some normal traffic first
        print("📡 Sending normal traffic for 5 seconds...")
        for _ in range(5):
            self.send_normal_packet(token)
            time.sleep(1)
        
        # Check initial ML status
        print("\n📊 Checking ML Engine Status...")
        initial_attacks = self.check_ml_detections()
        
        # Start attack
        self.attack_running = True
        
        if attack_type == "volume":
            self.volume_attack(token, duration, intensity)
        elif attack_type == "rate":
            self.rate_attack(token, duration, intensity)
        elif attack_type == "protocol":
            self.protocol_attack(token, duration, intensity)
        elif attack_type == "amplification":
            self.amplification_attack(token, duration, intensity)
        elif attack_type == "mixed":
            self.mixed_attack(token, duration)
        elif attack_type == "stealth":
            self.stealth_attack(token, duration)
        else:
            print(f"❌ Unknown attack type: {attack_type}")
            return
        
        self.attack_running = False
        
        # Check final ML status
        print("\n📊 Checking ML Engine Status After Attack...")
        final_attacks = self.check_ml_detections()
        
        print(f"\n📈 Attack Summary:")
        print(f"   Initial Detections: {initial_attacks}")
        print(f"   Final Detections: {final_attacks}")
        print(f"   New Detections: {final_attacks - initial_attacks}")
        
        if final_attacks > initial_attacks:
            print("✅ ML Engine successfully detected the attack!")
        else:
            print("⚠️  ML Engine may not have detected the attack")
        
        print("\n🎯 Attack simulation completed!")

def main():
    parser = argparse.ArgumentParser(description="DDoS Attack Simulator for ML Testing")
    parser.add_argument("--target", default="http://localhost:5000", 
                       help="Target URL (default: http://localhost:5000)")
    parser.add_argument("--device", default="ESP32_2", 
                       help="Device ID (default: ESP32_2)")
    parser.add_argument("--attack", default="volume", 
                       choices=["volume", "rate", "protocol", "amplification", "mixed", "stealth"],
                       help="Attack type (default: volume)")
    parser.add_argument("--duration", type=int, default=30, 
                       help="Attack duration in seconds (default: 30)")
    parser.add_argument("--intensity", default="medium", 
                       choices=["low", "medium", "high"],
                       help="Attack intensity (default: medium)")
    
    args = parser.parse_args()
    
    simulator = DDoSAttackSimulator(args.target, args.device)
    
    try:
        simulator.run_attack(args.attack, args.duration, args.intensity)
    except KeyboardInterrupt:
        print("\n🛑 Attack simulation interrupted by user")
        simulator.attack_running = False
    except Exception as e:
        print(f"\n❌ Error during attack simulation: {e}")

if __name__ == "__main__":
    main()
