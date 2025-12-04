#!/usr/bin/env python3
"""
ML Model Test Script
Test the ML model directly to verify it can detect attacks
"""

import numpy as np
import tensorflow as tf
from tensorflow import keras
import json

def test_ml_model():
    """Test the ML model directly"""
    print("🧪 Testing ML Model Directly...")
    
    try:
        # Load the model
        model_path = "models/ddos_model_retrained.keras"
        model = keras.models.load_model(model_path)
        print(f"✅ Model loaded from {model_path}")
        
        # Test normal packet
        print("\n📦 Testing Normal Packet...")
        normal_features = np.array([[
            64,    # packet_size
            6,     # protocol (TCP)
            1024,  # src_port
            80,    # dst_port
            1.0,   # packet_rate
            1.0,   # duration
            1000,  # bps
            1.0,   # pps
            16,    # tcp_flags (ACK)
            8192,  # window_size
            64,    # ttl
            0,     # fragment_offset
            64,    # ip_length
            20,    # tcp_length
            0      # udp_length
        ] + [0.0] * 62])  # Additional features
        
        normal_prediction = model.predict(normal_features, verbose=0)
        normal_class = int(np.argmax(normal_prediction))
        normal_confidence = float(np.max(normal_prediction))
        
        print(f"   Normal Packet Prediction: Class {normal_class}, Confidence: {normal_confidence:.3f}")
        
        # Test attack packet
        print("\n🚨 Testing Attack Packet...")
        attack_features = np.array([[
            1500,  # packet_size (large)
            6,     # protocol (TCP)
            12345, # src_port
            80,    # dst_port
            10000.0, # packet_rate (very high)
            0.001, # duration (very short)
            100000000, # bps (very high)
            10000.0, # pps (very high)
            2,     # tcp_flags (SYN)
            0,     # window_size (suspicious)
            1,     # ttl (suspicious)
            8191,  # fragment_offset (suspicious)
            1500,  # ip_length
            0,     # tcp_length (suspicious)
            0      # udp_length
        ] + [1.0] * 62])  # Additional features (all high)
        
        attack_prediction = model.predict(attack_features, verbose=0)
        attack_class = int(np.argmax(attack_prediction))
        attack_confidence = float(np.max(attack_prediction))
        
        print(f"   Attack Packet Prediction: Class {attack_class}, Confidence: {attack_confidence:.3f}")
        
        # Test multiple attack patterns
        print("\n🔍 Testing Multiple Attack Patterns...")
        attack_patterns = [
            ("Volume Attack", [1500, 6, 1024, 80, 1000, 0.1, 10000000, 1000, 2, 8192, 64, 0, 1500, 20, 0]),
            ("Rate Attack", [64, 6, 1024, 80, 50000, 0.001, 50000000, 50000, 2, 8192, 64, 0, 64, 20, 0]),
            ("Protocol Attack", [512, 6, 1024, 80, 1000, 0.1, 1000000, 1000, 2, 0, 1, 8191, 512, 0, 0]),
        ]
        
        for pattern_name, features in attack_patterns:
            pattern_features = np.array([features + [1.0] * 62])
            prediction = model.predict(pattern_features, verbose=0)
            class_id = int(np.argmax(prediction))
            confidence = float(np.max(prediction))
            
            print(f"   {pattern_name}: Class {class_id}, Confidence: {confidence:.3f}")
        
        # Check model output shape
        print(f"\n📊 Model Info:")
        print(f"   Input Shape: {model.input_shape}")
        print(f"   Output Shape: {model.output_shape}")
        print(f"   Number of Classes: {model.output_shape[1]}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing model: {e}")
        return False

if __name__ == "__main__":
    test_ml_model()
