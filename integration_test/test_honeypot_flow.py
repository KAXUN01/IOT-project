"""
Honeypot Flow Integration Tests
Tests honeypot redirection and threat intelligence extraction
"""

import unittest
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestHoneypotFlow(unittest.TestCase):
    """Test honeypot redirection and intelligence extraction"""
    
    def setUp(self):
        """Set up test environment"""
        from honeypot_manager.honeypot_deployer import HoneypotDeployer
        from honeypot_manager.log_parser import HoneypotLogParser
        from honeypot_manager.threat_intelligence import ThreatIntelligence
        from honeypot_manager.mitigation_generator import MitigationGenerator
        
        self.honeypot_deployer = HoneypotDeployer()
        self.log_parser = HoneypotLogParser()
        self.threat_intel = ThreatIntelligence()
        self.mitigation_generator = MitigationGenerator()
    
    def test_log_parsing(self):
        """Test honeypot log parsing"""
        logger.info("Testing log parsing...")
        
        # Sample Cowrie log entry
        log_entry = '''{"eventid": "cowrie.login.success", "timestamp": "2025-01-01T12:00:00Z", "src_ip": "192.168.1.100", "username": "admin", "password": "password123"}'''
        
        threats = self.log_parser.parse_logs(log_entry)
        
        self.assertGreater(len(threats), 0)
        self.assertEqual(threats[0]['source_ip'], '192.168.1.100')
        self.assertEqual(threats[0]['event_type'], 'cowrie.login.success')
        
        logger.info("✓ Log parsing test passed")
    
    def test_threat_intelligence(self):
        """Test threat intelligence extraction"""
        logger.info("Testing threat intelligence...")
        
        # Process logs
        log_entry = '''{"eventid": "cowrie.login.success", "timestamp": "2025-01-01T12:00:00Z", "src_ip": "192.168.1.100", "username": "admin"}'''
        threats = self.threat_intel.process_logs(log_entry)
        
        self.assertGreater(len(threats), 0)
        
        # Check if IP is blocked
        self.assertTrue(self.threat_intel.is_blocked('192.168.1.100'))
        
        # Get statistics
        stats = self.threat_intel.get_statistics()
        self.assertGreater(stats['blocked_ips'], 0)
        
        logger.info("✓ Threat intelligence test passed")
    
    def test_mitigation_rule_generation(self):
        """Test mitigation rule generation"""
        logger.info("Testing mitigation rule generation...")
        
        # Create sample threats
        threats = [
            {
                'source_ip': '192.168.1.100',
                'event_type': 'cowrie.login.success',
                'timestamp': '2025-01-01T12:00:00Z'
            },
            {
                'source_ip': '192.168.1.100',
                'event_type': 'cowrie.command.input',
                'command': 'rm -rf /',
                'timestamp': '2025-01-01T12:01:00Z'
            }
        ]
        
        rules = self.mitigation_generator.generate_rules_from_threats(threats)
        
        self.assertGreater(len(rules), 0)
        self.assertEqual(rules[0]['type'], 'deny')
        self.assertEqual(rules[0]['match_fields']['ipv4_src'], '192.168.1.100')
        
        logger.info("✓ Mitigation rule generation test passed")

def run_tests():
    """Run all honeypot flow tests"""
    logger.info("=" * 60)
    logger.info("Running Honeypot Flow Integration Tests")
    logger.info("=" * 60)
    
    unittest.main(verbosity=2, exit=False)

if __name__ == '__main__':
    run_tests()

