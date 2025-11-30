"""
Zero Trust Integration Tests
Tests the complete Zero Trust flow
"""

import unittest
import logging
import os
import time
import json

# Import all modules
from identity_manager.device_onboarding import DeviceOnboarding
from identity_manager.certificate_manager import CertificateManager
from identity_manager.identity_database import IdentityDatabase
from trust_evaluator.trust_scorer import TrustScorer
from trust_evaluator.device_attestation import DeviceAttestation
from trust_evaluator.policy_adapter import PolicyAdapter
from heuristic_analyst.anomaly_detector import AnomalyDetector
from heuristic_analyst.baseline_manager import BaselineManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestZeroTrustFlow(unittest.TestCase):
    """Test complete Zero Trust flow"""
    
    def setUp(self):
        """Set up test environment"""
        # Use test database
        self.test_db = "test_identity.db"
        self.test_certs_dir = "test_certs"
        
        # Initialize components
        self.onboarding = DeviceOnboarding(
            certs_dir=self.test_certs_dir,
            db_path=self.test_db
        )
        self.trust_scorer = TrustScorer()
        self.attestation = DeviceAttestation()
        self.policy_adapter = PolicyAdapter(
            trust_scorer=self.trust_scorer
        )
        self.anomaly_detector = AnomalyDetector()
        self.baseline_manager = BaselineManager(
            identity_db=self.onboarding.identity_db
        )
    
    def tearDown(self):
        """Clean up test environment"""
        # Remove test database
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
        
        # Remove test certificates
        import shutil
        if os.path.exists(self.test_certs_dir):
            shutil.rmtree(self.test_certs_dir)
    
    def test_device_onboarding(self):
        """Test device onboarding process"""
        logger.info("Testing device onboarding...")
        
        device_id = "TEST_DEVICE_1"
        mac_address = "AA:BB:CC:DD:EE:01"
        
        # Onboard device
        result = self.onboarding.onboard_device(
            device_id=device_id,
            mac_address=mac_address,
            device_type="sensor"
        )
        
        self.assertEqual(result['status'], 'success')
        self.assertTrue(os.path.exists(result['certificate_path']))
        self.assertTrue(os.path.exists(result['key_path']))
        
        # Verify device in database
        device_info = self.onboarding.get_device_info(device_id)
        self.assertIsNotNone(device_info)
        self.assertEqual(device_info['mac_address'], mac_address)
        
        logger.info("✓ Device onboarding test passed")
    
    def test_behavioral_profiling(self):
        """Test behavioral profiling"""
        logger.info("Testing behavioral profiling...")
        
        device_id = "TEST_DEVICE_2"
        mac_address = "AA:BB:CC:DD:EE:02"
        
        # Onboard device
        self.onboarding.onboard_device(device_id, mac_address)
        
        # Record some traffic
        for i in range(10):
            self.onboarding.record_traffic(device_id, {
                'size': 64 + i * 10,
                'dst_ip': f'192.168.1.{i+1}',
                'dst_port': 80 + i,
                'protocol': 6
            })
            time.sleep(0.1)
        
        # Finalize onboarding
        result = self.onboarding.finalize_onboarding(device_id)
        
        self.assertEqual(result['status'], 'success')
        self.assertIn('baseline', result)
        self.assertIn('policy', result)
        
        baseline = result['baseline']
        self.assertGreater(baseline['packet_count'], 0)
        self.assertIn('packets_per_second', baseline)
        
        logger.info("✓ Behavioral profiling test passed")
    
    def test_trust_scoring(self):
        """Test trust scoring system"""
        logger.info("Testing trust scoring...")
        
        device_id = "TEST_DEVICE_3"
        self.trust_scorer.initialize_device(device_id)
        
        initial_score = self.trust_scorer.get_trust_score(device_id)
        self.assertEqual(initial_score, 70)
        
        # Record anomaly
        self.trust_scorer.record_behavioral_anomaly(device_id, 'high')
        new_score = self.trust_scorer.get_trust_score(device_id)
        self.assertLess(new_score, initial_score)
        
        # Record positive behavior
        self.trust_scorer.record_positive_behavior(device_id, "Normal operation")
        final_score = self.trust_scorer.get_trust_score(device_id)
        self.assertGreater(final_score, new_score)
        
        logger.info("✓ Trust scoring test passed")
    
    def test_device_attestation(self):
        """Test device attestation"""
        logger.info("Testing device attestation...")
        
        device_id = "TEST_DEVICE_4"
        self.attestation.start_attestation(device_id)
        
        # Record heartbeat
        self.attestation.record_heartbeat(device_id)
        
        # Perform attestation
        result = self.attestation.perform_attestation(device_id)
        
        self.assertIn('passed', result)
        self.assertIn('checks', result)
        
        logger.info("✓ Device attestation test passed")
    
    def test_anomaly_detection(self):
        """Test anomaly detection"""
        logger.info("Testing anomaly detection...")
        
        device_id = "TEST_DEVICE_5"
        
        # Set baseline
        baseline = {
            'packets_per_second': 10.0,
            'bytes_per_second': 10000.0,
            'common_destinations': {'192.168.1.1': 10},
            'common_ports': {80: 10}
        }
        self.anomaly_detector.set_baseline(device_id, baseline)
        
        # Test normal traffic
        normal_stats = {
            'packets_per_second': 12.0,
            'bytes_per_second': 12000.0,
            'unique_destinations': 1,
            'unique_ports': 1
        }
        result = self.anomaly_detector.detect_anomalies(device_id, normal_stats)
        self.assertFalse(result['is_anomaly'])
        
        # Test attack traffic
        attack_stats = {
            'packets_per_second': 5000.0,
            'bytes_per_second': 5000000.0,
            'unique_destinations': 100,
            'unique_ports': 50
        }
        result = self.anomaly_detector.detect_anomalies(device_id, attack_stats)
        self.assertTrue(result['is_anomaly'])
        self.assertEqual(result['anomaly_type'], 'dos')
        
        logger.info("✓ Anomaly detection test passed")
    
    def test_policy_adaptation(self):
        """Test policy adaptation"""
        logger.info("Testing policy adaptation...")
        
        device_id = "TEST_DEVICE_6"
        self.trust_scorer.initialize_device(device_id)
        
        # High trust score -> allow
        self.trust_scorer.set_trust_score(device_id, 80)
        action = self.policy_adapter.adapt_policy_for_device(device_id)
        self.assertEqual(action, 'allow')
        
        # Medium trust score -> redirect
        self.trust_scorer.set_trust_score(device_id, 60)
        action = self.policy_adapter.adapt_policy_for_device(device_id)
        self.assertEqual(action, 'redirect')
        
        # Low trust score -> deny
        self.trust_scorer.set_trust_score(device_id, 40)
        action = self.policy_adapter.adapt_policy_for_device(device_id)
        self.assertEqual(action, 'deny')
        
        # Very low trust score -> quarantine
        self.trust_scorer.set_trust_score(device_id, 20)
        action = self.policy_adapter.adapt_policy_for_device(device_id)
        self.assertEqual(action, 'quarantine')
        
        logger.info("✓ Policy adaptation test passed")

def run_tests():
    """Run all integration tests"""
    logger.info("=" * 60)
    logger.info("Running Zero Trust Integration Tests")
    logger.info("=" * 60)
    
    unittest.main(verbosity=2, exit=False)

if __name__ == '__main__':
    run_tests()

