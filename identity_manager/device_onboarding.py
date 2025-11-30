"""
Secure Device Onboarding Module
Handles secure onboarding process with certificate provisioning and behavioral profiling
"""

import logging
import time
from typing import Dict, Optional

import json
from .certificate_manager import CertificateManager
from .identity_database import IdentityDatabase
from .behavioral_profiler import BehavioralProfiler
from .policy_generator import PolicyGenerator

logger = logging.getLogger(__name__)

class DeviceOnboarding:
    """Manages secure device onboarding process"""
    
    def __init__(self, certs_dir="certs", db_path="identity.db"):
        """
        Initialize device onboarding system
        
        Args:
            certs_dir: Directory for certificates
            db_path: Path to identity database
        """
        self.cert_manager = CertificateManager(certs_dir=certs_dir)
        self.identity_db = IdentityDatabase(db_path=db_path)
        self.profiler = BehavioralProfiler(profiling_duration=300)  # 5 minutes
        self.policy_generator = PolicyGenerator()
        
        logger.info("Device onboarding system initialized")
    
    def onboard_device(self, device_id: str, mac_address: str, device_type: str = None,
                     device_info: str = None) -> Dict:
        """
        Onboard a new device with secure certificate provisioning
        
        Args:
            device_id: Device identifier
            mac_address: Device MAC address
            device_type: Type of device
            device_info: Additional device information
            
        Returns:
            Onboarding result dictionary with certificate paths and status
        """
        try:
            logger.info(f"Starting onboarding for device {device_id} ({mac_address})...")
            
            # Check if device already exists
            existing = self.identity_db.get_device(device_id)
            if existing:
                logger.warning(f"Device {device_id} already onboarded")
                return {
                    'status': 'error',
                    'message': 'Device already onboarded',
                    'device_id': device_id
                }
            
            # Generate certificate
            cert_path, key_path = self.cert_manager.generate_device_certificate(
                device_id, mac_address
            )
            
            # Add device to database
            success = self.identity_db.add_device(
                device_id=device_id,
                mac_address=mac_address,
                certificate_path=cert_path,
                key_path=key_path,
                device_type=device_type,
                device_info=device_info
            )
            
            if not success:
                raise Exception("Failed to add device to database")
            
            # Start behavioral profiling
            self.profiler.start_profiling(device_id)
            
            # Get CA certificate for device
            ca_cert = self.cert_manager.get_ca_certificate()
            
            result = {
                'status': 'success',
                'device_id': device_id,
                'mac_address': mac_address,
                'certificate_path': cert_path,
                'key_path': key_path,
                'ca_certificate': ca_cert,
                'profiling': True,
                'message': 'Device onboarded successfully. Behavioral profiling started.'
            }
            
            logger.info(f"Device {device_id} onboarded successfully")
            return result
            
        except Exception as e:
            logger.error(f"Onboarding failed for {device_id}: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'device_id': device_id
            }
    
    def record_traffic(self, device_id: str, packet_info: Dict):
        """
        Record traffic for behavioral profiling
        
        Args:
            device_id: Device identifier
            packet_info: Packet information dictionary
        """
        self.profiler.record_traffic(device_id, packet_info)
        self.identity_db.update_last_seen(device_id)
    
    def finalize_onboarding(self, device_id: str) -> Dict:
        """
        Finalize onboarding by establishing baseline and generating policy
        
        Args:
            device_id: Device identifier
            
        Returns:
            Finalization result with baseline and policy
        """
        try:
            # Finish profiling
            baseline = self.profiler.finish_profiling(device_id)
            if not baseline:
                return {
                    'status': 'error',
                    'message': 'No profiling data available'
                }
            
            # Save baseline to database
            baseline_json = json.dumps(baseline)
            self.identity_db.save_behavioral_baseline(device_id, baseline_json)
            
            # Generate least-privilege policy
            policy = self.policy_generator.generate_least_privilege_policy(device_id, baseline)
            policy_json = self.policy_generator.policy_to_json(policy)
            self.identity_db.save_device_policy(device_id, policy_json)
            
            result = {
                'status': 'success',
                'device_id': device_id,
                'baseline': baseline,
                'policy': policy,
                'message': 'Onboarding finalized. Baseline and policy generated.'
            }
            
            logger.info(f"Onboarding finalized for {device_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to finalize onboarding for {device_id}: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def get_device_info(self, device_id: str) -> Optional[Dict]:
        """
        Get device information
        
        Args:
            device_id: Device identifier
            
        Returns:
            Device information dictionary or None
        """
        return self.identity_db.get_device(device_id)
    
    def get_device_id_from_mac(self, mac_address: str) -> Optional[str]:
        """
        Get device ID from MAC address
        
        Args:
            mac_address: MAC address
            
        Returns:
            Device ID or None
        """
        device = self.identity_db.get_device_by_mac(mac_address)
        if device:
            return device['device_id']
        return None
    
    def verify_device_certificate(self, device_id: str) -> bool:
        """
        Verify device certificate
        
        Args:
            device_id: Device identifier
            
        Returns:
            True if certificate is valid, False otherwise
        """
        device = self.identity_db.get_device(device_id)
        if not device or not device.get('certificate_path'):
            return False
        
        return self.cert_manager.verify_certificate(device['certificate_path'])
    
    def revoke_device(self, device_id: str) -> bool:
        """
        Revoke device access
        
        Args:
            device_id: Device identifier
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Revoke certificate
            self.cert_manager.revoke_certificate(device_id)
            
            # Update device status
            self.identity_db.update_device_status(device_id, 'revoked')
            
            logger.info(f"Device {device_id} revoked")
            return True
            
        except Exception as e:
            logger.error(f"Failed to revoke device {device_id}: {e}")
            return False

