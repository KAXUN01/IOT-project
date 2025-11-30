"""
Identity Database Module
SQLite database for device identity management
"""

import sqlite3
import logging
from datetime import datetime
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

class IdentityDatabase:
    """Manages device identity database using SQLite"""
    
    def __init__(self, db_path="identity.db"):
        """
        Initialize identity database
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize database schema"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Devices table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS devices (
                    device_id TEXT PRIMARY KEY,
                    mac_address TEXT UNIQUE NOT NULL,
                    certificate_path TEXT,
                    key_path TEXT,
                    onboarded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_seen TIMESTAMP,
                    status TEXT DEFAULT 'active',
                    device_type TEXT,
                    device_info TEXT
                )
            ''')
            
            # Behavioral baselines table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS behavioral_baselines (
                    device_id TEXT PRIMARY KEY,
                    baseline_data TEXT,
                    established_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP,
                    FOREIGN KEY (device_id) REFERENCES devices(device_id)
                )
            ''')
            
            # Policies table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS device_policies (
                    device_id TEXT PRIMARY KEY,
                    policy_data TEXT,
                    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP,
                    FOREIGN KEY (device_id) REFERENCES devices(device_id)
                )
            ''')
            
            conn.commit()
            conn.close()
            
            logger.info(f"Identity database initialized: {self.db_path}")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def add_device(self, device_id: str, mac_address: str, certificate_path: str = None,
                   key_path: str = None, device_type: str = None, device_info: str = None) -> bool:
        """
        Add a new device to the database
        
        Args:
            device_id: Device identifier
            mac_address: Device MAC address
            certificate_path: Path to device certificate
            key_path: Path to device private key
            device_type: Type of device
            device_info: Additional device information (JSON string)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO devices 
                (device_id, mac_address, certificate_path, key_path, device_type, device_info, last_seen)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (device_id, mac_address, certificate_path, key_path, device_type, device_info, datetime.utcnow()))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Device added: {device_id} ({mac_address})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add device {device_id}: {e}")
            return False
    
    def get_device(self, device_id: str) -> Optional[Dict]:
        """
        Get device information
        
        Args:
            device_id: Device identifier
            
        Returns:
            Device information dictionary or None
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM devices WHERE device_id = ?', (device_id,))
            row = cursor.fetchone()
            
            conn.close()
            
            if row:
                return dict(row)
            return None
            
        except Exception as e:
            logger.error(f"Failed to get device {device_id}: {e}")
            return None
    
    def get_device_by_mac(self, mac_address: str) -> Optional[Dict]:
        """
        Get device by MAC address
        
        Args:
            mac_address: MAC address
            
        Returns:
            Device information dictionary or None
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM devices WHERE mac_address = ?', (mac_address,))
            row = cursor.fetchone()
            
            conn.close()
            
            if row:
                return dict(row)
            return None
            
        except Exception as e:
            logger.error(f"Failed to get device by MAC {mac_address}: {e}")
            return None
    
    def update_device_status(self, device_id: str, status: str) -> bool:
        """
        Update device status
        
        Args:
            device_id: Device identifier
            status: New status ('active', 'inactive', 'revoked', 'quarantined')
            
        Returns:
            True if successful, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('UPDATE devices SET status = ? WHERE device_id = ?', (status, device_id))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Device {device_id} status updated to {status}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update device status: {e}")
            return False
    
    def update_last_seen(self, device_id: str) -> bool:
        """
        Update device last seen timestamp
        
        Args:
            device_id: Device identifier
            
        Returns:
            True if successful, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('UPDATE devices SET last_seen = ? WHERE device_id = ?', 
                          (datetime.utcnow(), device_id))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Failed to update last seen: {e}")
            return False
    
    def get_all_devices(self) -> List[Dict]:
        """
        Get all devices
        
        Returns:
            List of device dictionaries
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM devices')
            rows = cursor.fetchall()
            
            conn.close()
            
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Failed to get all devices: {e}")
            return []
    
    def save_behavioral_baseline(self, device_id: str, baseline_data: str) -> bool:
        """
        Save behavioral baseline for a device
        
        Args:
            device_id: Device identifier
            baseline_data: Baseline data (JSON string)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO behavioral_baselines 
                (device_id, baseline_data, updated_at)
                VALUES (?, ?, ?)
            ''', (device_id, baseline_data, datetime.utcnow()))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Behavioral baseline saved for {device_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save baseline: {e}")
            return False
    
    def get_behavioral_baseline(self, device_id: str) -> Optional[str]:
        """
        Get behavioral baseline for a device
        
        Args:
            device_id: Device identifier
            
        Returns:
            Baseline data (JSON string) or None
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT baseline_data FROM behavioral_baselines WHERE device_id = ?', (device_id,))
            row = cursor.fetchone()
            
            conn.close()
            
            if row:
                return row[0]
            return None
            
        except Exception as e:
            logger.error(f"Failed to get baseline: {e}")
            return None
    
    def save_device_policy(self, device_id: str, policy_data: str) -> bool:
        """
        Save device policy
        
        Args:
            device_id: Device identifier
            policy_data: Policy data (JSON string)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO device_policies 
                (device_id, policy_data, updated_at)
                VALUES (?, ?, ?)
            ''', (device_id, policy_data, datetime.utcnow()))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Policy saved for {device_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save policy: {e}")
            return False
    
    def get_device_policy(self, device_id: str) -> Optional[str]:
        """
        Get device policy
        
        Args:
            device_id: Device identifier
            
        Returns:
            Policy data (JSON string) or None
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT policy_data FROM device_policies WHERE device_id = ?', (device_id,))
            row = cursor.fetchone()
            
            conn.close()
            
            if row:
                return row[0]
            return None
            
        except Exception as e:
            logger.error(f"Failed to get policy: {e}")
            return None

