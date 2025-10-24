#!/usr/bin/env python3
"""
Simple DDoS Detection System
A rule-based system that can actually detect DDoS attacks
"""

import numpy as np
import json
import time
from datetime import datetime
from collections import deque

class SimpleDDoSDetector:
    def __init__(self):
        self.detection_history = deque(maxlen=1000)
        self.device_stats = {}
        
    def detect_attack(self, packet_data):
        """Detect DDoS attacks using rule-based approach"""
        device_id = packet_data.get('device_id', 'unknown')
        
        # Initialize device stats if not exists
        if device_id not in self.device_stats:
            self.device_stats[device_id] = {
                'packet_count': 0,
                'total_size': 0,
                'total_rate': 0,
                'last_seen': time.time(),
                'attack_score': 0
            }
        
        stats = self.device_stats[device_id]
        stats['packet_count'] += 1
        stats['last_seen'] = time.time()
        
        # Extract packet features
        packet_size = packet_data.get('size', 64)
        packet_rate = packet_data.get('rate', 1.0)
        bps = packet_data.get('bps', 1000)
        pps = packet_data.get('pps', 1.0)
        duration = packet_data.get('duration', 1.0)
        tcp_flags = packet_data.get('tcp_flags', 16)
        window_size = packet_data.get('window_size', 8192)
        ttl = packet_data.get('ttl', 64)
        
        # Calculate attack indicators
        attack_indicators = []
        attack_score = 0
        
        # 1. Volume Attack Detection
        if packet_size > 1000:
            attack_indicators.append("Large packet size")
            attack_score += 30
        
        # 2. Rate Attack Detection
        if packet_rate > 100:
            attack_indicators.append("High packet rate")
            attack_score += 25
        
        if pps > 1000:
            attack_indicators.append("High packets per second")
            attack_score += 25
        
        if bps > 1000000:
            attack_indicators.append("High bandwidth")
            attack_score += 20
        
        # 3. Protocol Attack Detection
        if tcp_flags == 2:  # SYN flag
            attack_indicators.append("SYN flood pattern")
            attack_score += 15
        
        if window_size == 0:
            attack_indicators.append("Zero window size")
            attack_score += 10
        
        if ttl < 10:
            attack_indicators.append("Suspicious TTL")
            attack_score += 10
        
        # 4. Duration-based detection
        if duration < 0.01:  # Very short bursts
            attack_indicators.append("Short burst pattern")
            attack_score += 15
        
        # 5. Combined attack patterns
        if packet_size > 1000 and packet_rate > 100:
            attack_indicators.append("Volume + Rate attack")
            attack_score += 20
        
        if pps > 1000 and duration < 0.1:
            attack_indicators.append("High frequency burst")
            attack_score += 25
        
        # Determine if it's an attack
        is_attack = attack_score >= 50
        confidence = min(attack_score / 100, 1.0)
        
        # Determine attack type
        if is_attack:
            if packet_size > 1000 and packet_rate > 100:
                attack_type = "Volume DDoS"
            elif pps > 1000:
                attack_type = "Rate DDoS"
            elif tcp_flags == 2:
                attack_type = "SYN Flood"
            elif duration < 0.01:
                attack_type = "Burst Attack"
            else:
                attack_type = "DDoS Attack"
        else:
            attack_type = "Normal"
        
        # Store detection
        detection = {
            'timestamp': datetime.now().isoformat(),
            'device_id': device_id,
            'is_attack': is_attack,
            'attack_type': attack_type,
            'confidence': confidence,
            'attack_score': attack_score,
            'indicators': attack_indicators,
            'packet_features': {
                'size': packet_size,
                'rate': packet_rate,
                'bps': bps,
                'pps': pps,
                'duration': duration,
                'tcp_flags': tcp_flags,
                'window_size': window_size,
                'ttl': ttl
            }
        }
        
        self.detection_history.append(detection)
        
        return {
            'prediction': attack_type,
            'is_attack': is_attack,
            'confidence': confidence,
            'attack_type': attack_type,
            'attack_score': attack_score,
            'indicators': attack_indicators
        }
    
    def get_recent_detections(self, limit=20):
        """Get recent attack detections"""
        return list(self.detection_history)[-limit:]
    
    def get_attack_statistics(self):
        """Get attack statistics"""
        total_detections = len(self.detection_history)
        attack_detections = [d for d in self.detection_history if d['is_attack']]
        
        return {
            'total_detections': total_detections,
            'attack_detections': len(attack_detections),
            'attack_rate': len(attack_detections) / max(total_detections, 1) * 100,
            'recent_attacks': len([d for d in attack_detections[-10:] if d['is_attack']]),
            'attack_types': list(set([d['attack_type'] for d in attack_detections]))
        }

# Test the detector
if __name__ == "__main__":
    detector = SimpleDDoSDetector()
    
    print("🧪 Testing Simple DDoS Detector...")
    
    # Test normal packet
    print("\n📦 Testing Normal Packet...")
    normal_packet = {
        'device_id': 'ESP32_2',
        'size': 64,
        'rate': 1.0,
        'bps': 1000,
        'pps': 1.0,
        'duration': 1.0,
        'tcp_flags': 16,
        'window_size': 8192,
        'ttl': 64
    }
    
    result = detector.detect_attack(normal_packet)
    print(f"   Result: {result['prediction']} (Attack: {result['is_attack']}, Confidence: {result['confidence']:.2f})")
    
    # Test attack packet
    print("\n🚨 Testing Attack Packet...")
    attack_packet = {
        'device_id': 'ESP32_2',
        'size': 1500,
        'rate': 10000.0,
        'bps': 100000000,
        'pps': 10000.0,
        'duration': 0.001,
        'tcp_flags': 2,
        'window_size': 0,
        'ttl': 1
    }
    
    result = detector.detect_attack(attack_packet)
    print(f"   Result: {result['prediction']} (Attack: {result['is_attack']}, Confidence: {result['confidence']:.2f})")
    print(f"   Indicators: {', '.join(result['indicators'])}")
    
    # Test multiple attacks
    print("\n🔍 Testing Multiple Attack Patterns...")
    attack_patterns = [
        ("Volume Attack", {'size': 1500, 'rate': 1000, 'bps': 10000000, 'pps': 1000, 'duration': 0.1, 'tcp_flags': 2}),
        ("Rate Attack", {'size': 64, 'rate': 50000, 'bps': 50000000, 'pps': 50000, 'duration': 0.001, 'tcp_flags': 2}),
        ("SYN Flood", {'size': 64, 'rate': 1000, 'bps': 1000000, 'pps': 1000, 'duration': 0.1, 'tcp_flags': 2, 'window_size': 0}),
    ]
    
    for pattern_name, features in attack_patterns:
        packet = {'device_id': 'ESP32_2', **features}
        result = detector.detect_attack(packet)
        print(f"   {pattern_name}: {result['prediction']} (Confidence: {result['confidence']:.2f})")
    
    # Show statistics
    stats = detector.get_attack_statistics()
    print(f"\n📊 Statistics:")
    print(f"   Total Detections: {stats['total_detections']}")
    print(f"   Attack Detections: {stats['attack_detections']}")
    print(f"   Attack Rate: {stats['attack_rate']:.1f}%")
    print(f"   Attack Types: {', '.join(stats['attack_types'])}")
