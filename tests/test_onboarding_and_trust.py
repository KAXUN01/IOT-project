
import pytest
import os
import time
from identity_manager.device_onboarding import DeviceOnboarding
from trust_evaluator.trust_scorer import TrustScorer

class TestOnboardingAndTrust:
    """
    Demonstration of Device Onboarding and Trust Score Mechanism.
    
    This test suite runs through a complete scenario:
    1. A new device requests onboarding.
    2. The system provisions a certificate and identity.
    3. The device is assigned an initial trust score.
    4. Behavior events (anomalies, positive behavior) impact the trust score.
    
    Usage:
        Run this script using pytest from the project root:
        $ python3 -m pytest tests/test_onboarding_and_trust.py -s
        
        Or from the tests directory:
        $ pytest test_onboarding_and_trust.py -s
    """

    def test_onboarding_and_trust_lifecycle(self, clean_onboarding_system, test_device_id, test_mac_address):
        """
        Scenario: Full lifecycle from onboarding to trust score updates.
        """
        print(f"\n\n=== STARTING DEMO: Onboarding & Trust Score for {test_device_id} ===")
        
        # -------------------------------------------------------------------------
        # Step 1: Device Onboarding
        # -------------------------------------------------------------------------
        print(f"[Step 1] Onboarding new device: {test_device_id} ({test_mac_address})")
        
        # The 'clean_onboarding_system' fixture provides a fresh DeviceOnboarding instance
        # with temporary database and certificate storage.
        onboarding_result = clean_onboarding_system.onboard_device(
            device_id=test_device_id,
            mac_address=test_mac_address,
            device_type='sensor',
            device_info='Demo Temperature Sensor'
        )
        
        assert onboarding_result['status'] == 'success'
        print(f"  -> Onboarding successful! Certificate created at: {onboarding_result['certificate_path']}")
        
        # Verify the device is in the database
        device_info = clean_onboarding_system.get_device_info(test_device_id)
        assert device_info is not None
        assert device_info['mac_address'] == test_mac_address
        print(f"  -> Device found in Identity Database.")

        # -------------------------------------------------------------------------
        # Step 2: Trust Score Initialization
        # -------------------------------------------------------------------------
        print(f"\n[Step 2] Initializing Trust Score")
        
        # Connect Trust Scorer to the same identity database
        trust_scorer = TrustScorer(initial_score=70, identity_db=clean_onboarding_system.identity_db)
        
        # Initialize the device's score (usually happens automatically or via event)
        trust_scorer.initialize_device(test_device_id)
        
        initial_score = trust_scorer.get_trust_score(test_device_id)
        print(f"  -> Initial Trust Score: {initial_score} (Level: {trust_scorer.get_trust_level(test_device_id)})")
        assert initial_score == 70

        # -------------------------------------------------------------------------
        # Step 3: Simulating Trust Events
        # -------------------------------------------------------------------------
        print(f"\n[Step 3] Simulating Behavioral Events")

        # Scenario A: Device behaves well
        print("  [Event] Device transmits valid data consistently.")
        trust_scorer.record_positive_behavior(test_device_id, "Consistent valid data transmission")
        new_score = trust_scorer.get_trust_score(test_device_id)
        print(f"  -> Trust Score increased to: {new_score}")
        assert new_score > 70
        
        # Scenario B: Minor Behavioral Anomaly
        print("  [Event] WARNING: Minor behavioral anomaly detected (unusual port usage).")
        # record_behavioral_anomaly(device_id, severity) -> severity: 'low', 'medium', 'high'
        trust_scorer.record_behavioral_anomaly(test_device_id, severity='low')
        current_score = trust_scorer.get_trust_score(test_device_id)
        print(f"  -> Trust Score decreased to: {current_score} (Level: {trust_scorer.get_trust_level(test_device_id)})")
        
        # Scenario C: Critical Security Alert
        print("  [Event] CRITICAL: Security alert! Known malware signature detected.")
        trust_scorer.record_security_alert(test_device_id, alert_type="Malware Signature", severity='high')
        final_score = trust_scorer.get_trust_score(test_device_id)
        print(f"  -> Trust Score PLUMMETED to: {final_score} (Level: {trust_scorer.get_trust_level(test_device_id)})")
        
        assert final_score < current_score
        assert trust_scorer.get_trust_level(test_device_id) in ['suspicious', 'untrusted']

        # -------------------------------------------------------------------------
        # Step 4: Verification of Factors
        # -------------------------------------------------------------------------
        print(f"\n[Step 4] Analyzing Trust Factors")
        factors = trust_scorer.get_score_factors(test_device_id)
        print(f"  -> Factors contributing to score reduction: {factors}")
        
        assert factors['alerts'] > 0
        assert factors['behavioral'] > 0
        
        print("\n=== DEMO COMPLETE ===")
