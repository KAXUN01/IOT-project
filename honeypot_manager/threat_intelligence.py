"""
Threat Intelligence Module
Manages and processes threat intelligence from honeypots
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta

from honeypot_manager.log_parser import HoneypotLogParser

logger = logging.getLogger(__name__)

class ThreatIntelligence:
    """Manages threat intelligence from honeypots"""
    
    def __init__(self):
        """Initialize threat intelligence manager"""
        self.log_parser = HoneypotLogParser()
        self.blocked_ips = {}  # {ip: {'blocked_at': timestamp, 'reason': reason}}
        self.mitigation_rules = []  # List of mitigation rules generated
    
    def process_logs(self, log_content: str) -> List[Dict]:
        """
        Process honeypot logs and extract threat intelligence
        
        Args:
            log_content: Log content as string
            
        Returns:
            List of threat intelligence dictionaries
        """
        threats = self.log_parser.parse_logs(log_content)
        
        # Analyze threats and generate mitigation rules
        for threat in threats:
            self._analyze_threat(threat)
        
        return threats
    
    def _analyze_threat(self, threat: Dict):
        """
        Analyze a threat and determine if mitigation is needed
        
        Args:
            threat: Threat intelligence dictionary
        """
        src_ip = threat.get('source_ip')
        if not src_ip:
            return
        
        event_type = threat.get('event_type', '')
        
        # Determine threat severity
        severity = 'low'
        if event_type in ['cowrie.login.success', 'cowrie.session.file_download']:
            severity = 'high'
        elif event_type in ['cowrie.command.input']:
            # Check for malicious commands
            command = threat.get('command', '').lower()
            malicious_keywords = ['rm', 'delete', 'format', 'dd', 'mkfs', 'shutdown', 'reboot']
            if any(keyword in command for keyword in malicious_keywords):
                severity = 'high'
            else:
                severity = 'medium'
        
        # Block IP if high severity
        if severity == 'high':
            self.block_ip(src_ip, f"High severity threat: {event_type}")
            logger.warning(f"Blocked IP {src_ip} due to {event_type}")
    
    def block_ip(self, ip_address: str, reason: str):
        """
        Block an IP address
        
        Args:
            ip_address: IP address to block
            reason: Reason for blocking
        """
        self.blocked_ips[ip_address] = {
            'blocked_at': datetime.utcnow().isoformat(),
            'reason': reason
        }
        
        # Generate mitigation rule
        rule = {
            'type': 'deny',
            'match_fields': {
                'ipv4_src': ip_address
            },
            'priority': 200,
            'reason': reason,
            'generated_at': datetime.utcnow().isoformat()
        }
        
        self.mitigation_rules.append(rule)
        logger.info(f"Generated mitigation rule for {ip_address}: {reason}")
    
    def is_blocked(self, ip_address: str) -> bool:
        """
        Check if an IP address is blocked
        
        Args:
            ip_address: IP address to check
            
        Returns:
            True if blocked, False otherwise
        """
        return ip_address in self.blocked_ips
    
    def get_blocked_ips(self) -> List[str]:
        """
        Get list of blocked IP addresses
        
        Returns:
            List of blocked IP addresses
        """
        return list(self.blocked_ips.keys())
    
    def get_mitigation_rules(self) -> List[Dict]:
        """
        Get all mitigation rules
        
        Returns:
            List of mitigation rule dictionaries
        """
        return self.mitigation_rules
    
    def get_recent_threats(self, limit: int = 50) -> List[Dict]:
        """
        Get recent threats
        
        Args:
            limit: Maximum number of threats to return
            
        Returns:
            List of threat dictionaries
        """
        return self.log_parser.get_recent_threats(limit)
    
    def get_statistics(self) -> Dict:
        """
        Get threat intelligence statistics
        
        Returns:
            Statistics dictionary
        """
        stats = self.log_parser.get_statistics()
        stats['blocked_ips'] = len(self.blocked_ips)
        stats['mitigation_rules'] = len(self.mitigation_rules)
        return stats

