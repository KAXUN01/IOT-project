"""
ML Security Engine for IoT DDoS Attack Detection
Real-time network traffic analysis using pre-trained ML models
"""

import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow import keras
import json
import time
from datetime import datetime
from collections import deque
import threading
import logging
import os

# Module-level constants for health checks
HEALTH_CHECK_INTERVAL = 60  # seconds
MAX_RELOAD_ATTEMPTS = 3
INIT_TIMEOUT = 30  # seconds

# Global ML engine instance placeholder (set by controller)
ml_engine = None

class MLSecurityEngine:
    def __init__(self, model_path="models/ddos_model_retrained.keras"):
        """
        Initialize ML Security Engine with pre-trained DDoS detection model
        """
        self.model = None
        self.model_path = model_path
        self.is_loaded = False
        self.initialization_time = time.time()
        self.last_health_check = time.time()
        self.reload_attempts = 0
        self.health_check_thread = None
        self.is_running = True
        self.attack_detections = deque(maxlen=1000)  # Store last 1000 detections
        self.blocked_ips = {}  # Dictionary to track blocked IPs and their block duration
        
        # Statistics tracking
        self.detection_window = deque(maxlen=1000)  # Store recent detections for statistics
        self.last_processing_times = deque(maxlen=100)  # Store last 100 processing times
        self.false_positives = deque(maxlen=1000)  # Store known false positives
        
        self.network_stats = {
            'total_packets': 0,
            'attack_packets': 0,
            'normal_packets': 0,
            'attack_rate': 0.0,
            'detection_rate': 0.0,
            'false_positive_rate': 0.0,
            'model_confidence': 0.0,
            'processing_rate': 0.0,
            'uptime': 0,
            'last_health_check': None,
            'model_status': 'initializing'
        }
        self.real_time_features = deque(maxlen=100)  # Store last 100 feature vectors
        self.attack_types = {
            0: 'Normal',
            1: 'DDoS Attack',
            2: 'Botnet Attack',
            3: 'Flood Attack'
        }
        
        # Initialize logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Load the model
        if not self.load_model():
            self.logger.error("❌ Initial model load failed")
            return
            
        # Start health check thread
        self.start_health_checks()

    def start_health_checks(self):
        """Start periodic health checks"""
        def health_check_loop():
            while self.is_running:
                try:
                    self.check_health()
                    time.sleep(HEALTH_CHECK_INTERVAL)
                except Exception as e:
                    self.logger.error(f"Health check error: {e}")
                    time.sleep(5)  # Wait before retry
        
        self.health_check_thread = threading.Thread(
            target=health_check_loop,
            name="ML_HealthCheck",
            daemon=True
        )
        self.health_check_thread.start()

    def update_detection_stats(self, prediction_time):
        """
        Update detection statistics based on recent detections
        """
        try:
            current_time = time.time()
            window_start = current_time - 300  # 5 minutes window

            # Filter detections within the time window
            recent_detections = [d for d in self.detection_window 
                               if d['timestamp'] > window_start]

            if recent_detections:
                # Calculate detection rate
                total_detections = len(recent_detections)
                attack_detections = sum(1 for d in recent_detections 
                                     if d['type'] != 'Normal')
                
                self.network_stats['detection_rate'] = round(
                    (attack_detections / total_detections) * 100, 2)

                # Calculate false positive rate (if ground truth is available)
                false_positives = sum(1 for d in self.false_positives 
                                    if d > window_start)
                if attack_detections > 0:
                    self.network_stats['false_positive_rate'] = round(
                        (false_positives / attack_detections) * 100, 2)
                else:
                    self.network_stats['false_positive_rate'] = 0.0

                # Calculate average model confidence
                avg_confidence = np.mean([d['confidence'] for d in recent_detections])
                self.network_stats['model_confidence'] = round(avg_confidence, 2)

            # Update processing rate
            if self.last_processing_times:
                avg_processing_time = np.mean(self.last_processing_times)
                self.network_stats['processing_rate'] = round(
                    1.0 / avg_processing_time if avg_processing_time > 0 else 0, 2)
            
            # Update packet statistics
            self.network_stats['total_packets'] += 1
            if prediction_time is not None:
                self.last_processing_times.append(prediction_time)

        except Exception as e:
            self.logger.error(f"Error updating detection stats: {e}")

    def get_detection_stats(self):
        """Get current detection statistics"""
        return {
            'detection_rate': self.network_stats['detection_rate'],
            'false_positive_rate': self.network_stats['false_positive_rate'],
            'model_confidence': self.network_stats['model_confidence'],
            'processing_rate': self.network_stats['processing_rate'],
            'total_packets': self.network_stats['total_packets'],
            'attack_packets': self.network_stats['attack_packets'],
            'normal_packets': self.network_stats['normal_packets']
        }

    def check_health(self) -> bool:
        """
        Check ML engine health and reload if necessary
        Returns True if healthy, False otherwise
        """
        try:
            self.last_health_check = time.time()
            self.network_stats['last_health_check'] = datetime.now().isoformat()
            
            # Update uptime
            self.network_stats['uptime'] = time.time() - self.initialization_time
            
            # Check if model is loaded
            if not self.is_loaded or self.model is None:
                self.logger.warning("❗ Model not loaded during health check")
                if self.reload_attempts < MAX_RELOAD_ATTEMPTS:
                    self.reload_attempts += 1
                    self.logger.info(f"Attempting model reload ({self.reload_attempts}/{MAX_RELOAD_ATTEMPTS})")
                    return self.load_model()
                return False
            
            # Test model with dummy data
            test_input = np.random.rand(1, 77)  # Match model input shape
            try:
                _ = self.model.predict(test_input, verbose=0)
                self.network_stats['model_status'] = 'healthy'
                self.reload_attempts = 0  # Reset counter on successful predict
                return True
            except Exception as e:
                self.logger.error(f"Model prediction failed during health check: {e}")
                self.network_stats['model_status'] = 'error'
                return False
                
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            self.network_stats['model_status'] = 'error'
            return False
    
    def load_model(self):
        """
        Load the pre-trained ML model
        Returns True if successful, False otherwise
        """
        try:
            # Try absolute path first
            model_path = self.model_path
            if not os.path.isabs(model_path):
                # Try relative to script location
                script_dir = os.path.dirname(os.path.abspath(__file__))
                model_path = os.path.join(script_dir, self.model_path)
                
                # If not there, try current working directory
                if not os.path.exists(model_path):
                    cwd = os.getcwd()
                    model_path = os.path.join(cwd, self.model_path)
                    
                    # Also try parent directory of working dir
                    if not os.path.exists(model_path):
                        parent_dir = os.path.dirname(cwd)
                        model_path = os.path.join(parent_dir, self.model_path)

            self.logger.info(f"🔍 Attempting to load model from: {model_path}")
            
            if not os.path.exists(model_path):
                self.logger.error(f"❌ Model file not found at: {model_path}")
                self.logger.error(f"Tried paths:")
                self.logger.error(f"- Original: {self.model_path}")
                self.logger.error(f"- Script dir: {os.path.join(script_dir, self.model_path)}")
                self.logger.error(f"- Working dir: {os.path.join(os.getcwd(), self.model_path)}")
                return False

            # Try loading the model with error capture
            try:
                self.model = keras.models.load_model(model_path)
            except Exception as load_error:
                self.logger.error(f"❌ Model load error: {str(load_error)}")
                # Try alternate model if available
                if "retrained" in model_path:
                    alt_path = model_path.replace("retrained", "")
                    self.logger.info(f"🔄 Trying alternate model: {alt_path}")
                    if os.path.exists(alt_path):
                        self.model = keras.models.load_model(alt_path)
                    else:
                        raise load_error
                else:
                    raise load_error

            self.is_loaded = True
            self.network_stats['model_status'] = 'loaded'
            self.logger.info(f"✅ ML model loaded successfully from {model_path}")
            self.logger.info(f"Model input shape: {self.model.input_shape}")
            self.logger.info(f"Model output shape: {self.model.output_shape}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to load ML model: {str(e)}")
            self.logger.error(f"Current working directory: {os.getcwd()}")
            self.logger.error(f"Python path: {os.getenv('PYTHONPATH', 'Not set')}")
            self.is_loaded = False
            self.network_stats['model_status'] = 'error'
            return False
    
    def extract_features(self, packet_data):
        """
        Extract features from network packet data for ML model
        This function simulates feature extraction from real network traffic
        """
        try:
            # Generate 77 features to match the model's expected input
            # This simulates comprehensive network traffic analysis
            features = {}
            
            # Basic packet features (15 features)
            features['packet_size'] = packet_data.get('size', np.random.randint(64, 1500))
            features['protocol'] = packet_data.get('protocol', np.random.randint(1, 4))
            features['src_port'] = packet_data.get('src_port', np.random.randint(1, 65535))
            features['dst_port'] = packet_data.get('dst_port', np.random.randint(1, 65535))
            features['packet_rate'] = packet_data.get('rate', np.random.uniform(0.1, 100.0))
            features['connection_duration'] = packet_data.get('duration', np.random.uniform(0.1, 3600.0))
            features['bytes_per_second'] = packet_data.get('bps', np.random.uniform(100, 1000000))
            features['packets_per_second'] = packet_data.get('pps', np.random.uniform(0.1, 1000.0))
            features['tcp_flags'] = packet_data.get('tcp_flags', np.random.randint(0, 255))
            features['window_size'] = packet_data.get('window_size', np.random.randint(1024, 65535))
            features['ttl'] = packet_data.get('ttl', np.random.randint(1, 255))
            features['fragment_offset'] = packet_data.get('fragment_offset', np.random.randint(0, 8191))
            features['ip_length'] = packet_data.get('ip_length', np.random.randint(20, 1500))
            features['tcp_length'] = packet_data.get('tcp_length', np.random.randint(20, 1500))
            features['udp_length'] = packet_data.get('udp_length', np.random.randint(8, 1500))
            
            # Generate additional 62 features to reach 77 total
            # These represent various network traffic characteristics
            additional_features = []
            
            # Statistical features (20 features)
            for i in range(20):
                additional_features.append(np.random.uniform(0, 1000))
            
            # Time-based features (15 features)
            for i in range(15):
                additional_features.append(np.random.uniform(0, 3600))
            
            # Protocol-specific features (15 features)
            for i in range(15):
                additional_features.append(np.random.uniform(0, 100))
            
            # Network flow features (12 features)
            for i in range(12):
                additional_features.append(np.random.uniform(0, 10000))
            
            # Combine all features into a 77-dimensional vector
            all_features = [
                features['packet_size'],
                features['protocol'],
                features['src_port'],
                features['dst_port'],
                features['packet_rate'],
                features['connection_duration'],
                features['bytes_per_second'],
                features['packets_per_second'],
                features['tcp_flags'],
                features['window_size'],
                features['ttl'],
                features['fragment_offset'],
                features['ip_length'],
                features['tcp_length'],
                features['udp_length']
            ] + additional_features
            
            # Ensure we have exactly 77 features
            if len(all_features) < 77:
                all_features.extend([0.0] * (77 - len(all_features)))
            elif len(all_features) > 77:
                all_features = all_features[:77]
            
            feature_vector = np.array(all_features).reshape(1, -1)
            
            return feature_vector, features
            
        except Exception as e:
            self.logger.error(f"❌ Feature extraction failed: {e}")
            return None, None
    
    def predict_attack(self, packet_data):
        """
        Predict if the packet represents a DDoS attack
        """
        if not self.is_loaded:
            return {'prediction': 'Model not loaded', 'confidence': 0.0, 'attack_type': 'Unknown'}
        
        try:
            # Extract features
            feature_vector, features = self.extract_features(packet_data)
            if feature_vector is None:
                return {'prediction': 'Feature extraction failed', 'confidence': 0.0, 'attack_type': 'Unknown'}
            
            # Make prediction
            prediction = self.model.predict(feature_vector, verbose=0)
            confidence = float(np.max(prediction))
            predicted_class = int(np.argmax(prediction))
            
            # Determine if it's an attack
            is_attack = predicted_class != 0  # Assuming class 0 is normal
            attack_type = self.attack_types.get(predicted_class, 'Unknown')
            
            # Store detection
            detection = {
                'timestamp': datetime.now().isoformat(),
                'is_attack': is_attack,
                'attack_type': attack_type,
                'confidence': confidence,
                'features': features,
                'prediction_vector': prediction[0].tolist()
            }
            # Attach device context if provided
            if isinstance(packet_data, dict) and 'device_id' in packet_data:
                detection['device_id'] = str(packet_data.get('device_id'))
            
            self.attack_detections.append(detection)
            
            # Update statistics
            self.update_statistics(is_attack)
            
            return {
                'prediction': 'Attack' if is_attack else 'Normal',
                'confidence': confidence,
                'attack_type': attack_type,
                'is_attack': is_attack,
                'detection': detection
            }
            
        except Exception as e:
            self.logger.error(f"❌ Prediction failed: {e}")
            return {'prediction': 'Prediction failed', 'confidence': 0.0, 'attack_type': 'Unknown'}
    
    def update_statistics(self, is_attack):
        """Update network statistics based on detection results"""
        self.network_stats['total_packets'] += 1
        
        if is_attack:
            self.network_stats['attack_packets'] += 1
        else:
            self.network_stats['normal_packets'] += 1
        
        # Calculate attack rate
        if self.network_stats['total_packets'] > 0:
            self.network_stats['attack_rate'] = (
                self.network_stats['attack_packets'] / self.network_stats['total_packets']
            ) * 100
        
        # Calculate detection accuracy (simplified)
        if len(self.attack_detections) > 10:
            recent_detections = list(self.attack_detections)[-10:]
            avg_confidence = np.mean([d['confidence'] for d in recent_detections])
            self.network_stats['detection_accuracy'] = avg_confidence * 100
    
    def get_attack_statistics(self):
        """Get comprehensive attack statistics"""
        if not self.attack_detections:
            return self.network_stats
        
        # Calculate additional statistics
        recent_attacks = [d for d in self.attack_detections if d['is_attack']]
        attack_types_count = {}
        
        for detection in recent_attacks:
            attack_type = detection['attack_type']
            attack_types_count[attack_type] = attack_types_count.get(attack_type, 0) + 1
        
        # Time-based analysis
        now = datetime.now()
        last_hour_attacks = [
            d for d in recent_attacks 
            if (now - datetime.fromisoformat(d['timestamp'])).seconds < 3600
        ]
        
        # Convert numpy types to Python types for JSON serialization
        stats = {
            **self.network_stats,
            'recent_attacks': int(len(recent_attacks)),
            'last_hour_attacks': int(len(last_hour_attacks)),
            'attack_types_distribution': attack_types_count,
            'avg_confidence': float(np.mean([d['confidence'] for d in recent_attacks])) if recent_attacks else 0.0,
            'max_confidence': float(np.max([d['confidence'] for d in recent_attacks])) if recent_attacks else 0.0,
            'min_confidence': float(np.min([d['confidence'] for d in recent_attacks])) if recent_attacks else 0.0
        }
        
        # Convert any remaining numpy types
        for key, value in stats.items():
            if hasattr(value, 'item'):  # numpy scalar
                stats[key] = value.item()
            elif isinstance(value, np.ndarray):
                stats[key] = value.tolist()
                
        return stats
    
    def get_recent_detections(self, limit=10):
        """Get recent attack detections"""
        try:
            detections = list(self.attack_detections)[-limit:]
            # Ensure all detections have proper format and convert numpy types to Python types
            for detection in detections:
                if not isinstance(detection, dict):
                    continue
                # Ensure required fields exist and convert numpy types
                if 'timestamp' not in detection:
                    detection['timestamp'] = datetime.now().isoformat()
                    
                if 'confidence' not in detection:
                    detection['confidence'] = 0.0
                else:
                    detection['confidence'] = float(detection['confidence'])
                    
                if 'attack_type' not in detection:
                    detection['attack_type'] = 'Unknown'
                else:
                    detection['attack_type'] = str(detection['attack_type'])
                    
                if 'is_attack' not in detection:
                    detection['is_attack'] = False
                else:
                    detection['is_attack'] = bool(detection['is_attack'])
                    
                # Convert any remaining numpy types to Python types
                for key, value in detection.items():
                    if hasattr(value, 'item'):  # numpy scalar
                        detection[key] = value.item()
                    elif isinstance(value, np.ndarray):
                        detection[key] = value.tolist()
            return detections
        except Exception as e:
            self.logger.error(f"Error getting recent detections: {e}")
            return []
    
    def simulate_network_traffic(self):
        """Simulate network traffic for testing purposes"""
        while True:
            # Simulate different types of network traffic
            traffic_types = ['normal', 'ddos', 'botnet', 'flood']
            traffic_type = np.random.choice(traffic_types, p=[0.7, 0.1, 0.1, 0.1])
            
            # Generate packet data based on traffic type
            if traffic_type == 'normal':
                packet_data = {
                    'size': np.random.randint(64, 1500),
                    'protocol': np.random.choice([1, 6, 17]),  # ICMP, TCP, UDP
                    'src_port': np.random.randint(1024, 65535),
                    'dst_port': np.random.randint(80, 443),
                    'rate': np.random.uniform(0.1, 10.0),
                    'duration': np.random.uniform(1.0, 3600.0),
                    'bps': np.random.uniform(1000, 100000),
                    'pps': np.random.uniform(0.1, 100.0)
                }
            else:  # Attack traffic
                packet_data = {
                    'size': np.random.randint(64, 1500),
                    'protocol': np.random.choice([1, 6, 17]),
                    'src_port': np.random.randint(1, 65535),
                    'dst_port': np.random.randint(80, 443),
                    'rate': np.random.uniform(50.0, 1000.0),  # Higher rate for attacks
                    'duration': np.random.uniform(0.1, 100.0),
                    'bps': np.random.uniform(100000, 10000000),  # Higher bandwidth
                    'pps': np.random.uniform(100.0, 10000.0)  # Higher packet rate
                }
            
            # Analyze the packet
            result = self.predict_attack(packet_data)
            
            # Log significant detections
            if result.get('is_attack', False) and result.get('confidence', 0) > 0.8:
                self.logger.warning(f"🚨 ATTACK DETECTED: {result['attack_type']} (Confidence: {result['confidence']:.2f})")
            
            time.sleep(0.1)  # Simulate real-time processing
    
    def start_monitoring(self):
        """Start real-time network monitoring"""
        if not self.is_loaded:
            self.logger.error("❌ Cannot start monitoring: Model not loaded")
            return
        
        self.logger.info("🔍 Starting real-time network monitoring...")
        monitor_thread = threading.Thread(target=self.simulate_network_traffic, daemon=True)
        monitor_thread.start()
        self.logger.info("✅ Network monitoring started")

# Global ML Security Engine instance
ml_engine = None

def initialize_ml_engine():
    """Initialize the global ML security engine"""
    global ml_engine
    if ml_engine is None:
        ml_engine = MLSecurityEngine()
    return ml_engine

def get_ml_engine():
    """Get the global ML security engine instance"""
    return ml_engine

if __name__ == "__main__":
    # Test the ML Security Engine
    print("🧪 Testing ML Security Engine...")
    
    engine = MLSecurityEngine()
    
    if engine.is_loaded:
        print("✅ ML Engine initialized successfully")
        
        # Test with sample data
        test_packet = {
            'size': 1024,
            'protocol': 6,  # TCP
            'src_port': 12345,
            'dst_port': 80,
            'rate': 5.0,
            'duration': 10.0,
            'bps': 50000,
            'pps': 5.0
        }
        
        result = engine.predict_attack(test_packet)
        print(f"Test prediction: {result}")
        
        # Start monitoring
        engine.start_monitoring()
        
        # Run for a few seconds to see detections
        time.sleep(5)
        
        stats = engine.get_attack_statistics()
        print(f"Network statistics: {stats}")
        
    else:
        print("❌ Failed to initialize ML Engine")
