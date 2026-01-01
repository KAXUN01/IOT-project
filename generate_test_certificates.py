"""
Script to generate certificates for test devices and update the database
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from identity_manager.certificate_manager import CertificateManager
from identity_manager.identity_database import IdentityDatabase

# Initialize managers
cert_manager = CertificateManager(
    ca_cert_path='certs/ca_cert.pem',
    ca_key_path='certs/ca_key.pem',
    certs_dir='certs'
)
db = IdentityDatabase('identity.db')

# Test devices  
test_devices = [
    {'device_id': 'Sensor_A', 'mac_address': 'AA:BB:CC:DD:EE:AA'},
    {'device_id': 'Sensor_B', 'mac_address': 'AA:BB:CC:DD:EE:BB'}
]

print("Generating certificates for test devices...")
for device in test_devices:
    device_id = device['device_id']
    mac_address = device['mac_address']
    
    try:
        # Generate certificate
        cert_path, key_path = cert_manager.generate_device_certificate(
            device_id=device_id,
            mac_address=mac_address,
            validity_days=365
        )
        
        # Update database with certificate paths
        import sqlite3
        conn = sqlite3.connect('identity.db')
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE devices 
            SET certificate_path = ?, key_path = ?
            WHERE device_id = ?
        ''', (cert_path, key_path, device_id))
        conn.commit()
        conn.close()
        
        print(f"✅ Generated certificate for {device_id}")
        print(f"   Certificate: {cert_path}")
        print(f"   Key: {key_path}")
        
    except Exception as e:
        print(f"❌ Failed to generate certificate for {device_id}: {e}")
        import traceback
        traceback.print_exc()

print("\nDone! Certificates generated and database updated.")
