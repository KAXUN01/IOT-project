"""
Zero Trust SDN Framework - Main Integration Module
Integrates all components into a unified system
"""

import logging
import threading
import time
from typing import Optional

# Import all modules
try:
    from ryu_controller.sdn_policy_engine import SDNPolicyEngine
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.warning(f"Ryu controller not available: {e}")
    SDNPolicyEngine = None

from identity_manager.device_onboarding import DeviceOnboarding
from trust_evaluator.trust_scorer import TrustScorer
from trust_evaluator.device_attestation import DeviceAttestation
from trust_evaluator.policy_adapter import PolicyAdapter
from heuristic_analyst.flow_analyzer import FlowAnalyzer
from heuristic_analyst.anomaly_detector import AnomalyDetector
from heuristic_analyst.baseline_manager import BaselineManager
from ryu_controller.traffic_orchestrator import TrafficOrchestrator
from honeypot_manager.honeypot_deployer import HoneypotDeployer
from honeypot_manager.threat_intelligence import ThreatIntelligence
from honeypot_manager.mitigation_generator import MitigationGenerator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ZeroTrustFramework:
    """Main Zero Trust Framework integration class"""
    
    def __init__(self, config: Optional[dict] = None):
        """
        Initialize Zero Trust Framework
        
        Args:
            config: Configuration dictionary (optional)
        """
        self.config = config or {}
        
        # Initialize components
        logger.info("Initializing Zero Trust Framework...")
        
        # Identity Management
        self.onboarding = DeviceOnboarding(
            certs_dir=self.config.get('certs_dir', 'certs'),
            db_path=self.config.get('db_path', 'identity.db')
        )
        
        # Trust Evaluation
        self.trust_scorer = TrustScorer(
            initial_score=self.config.get('initial_trust_score', 70)
        )
        self.attestation = DeviceAttestation(
            attestation_interval=self.config.get('attestation_interval', 300)
        )
        self.policy_adapter = PolicyAdapter(
            trust_scorer=self.trust_scorer
        )
        
        # Heuristic Analyst
        self.baseline_manager = BaselineManager(
            identity_db=self.onboarding.identity_db
        )
        self.anomaly_detector = AnomalyDetector()
        
        # Honeypot Management
        self.honeypot_deployer = HoneypotDeployer(
            honeypot_type=self.config.get('honeypot_type', 'cowrie')
        )
        self.threat_intelligence = ThreatIntelligence()
        self.mitigation_generator = MitigationGenerator()
        
        # SDN Policy Engine (will be set when Ryu controller starts)
        self.sdn_policy_engine = None
        
        # Traffic Orchestrator
        self.traffic_orchestrator = TrafficOrchestrator(
            identity_module=self.onboarding,
            trust_module=self.trust_scorer
        )
        
        # Background threads
        self.running = False
        self.threads = []
        
        logger.info("Zero Trust Framework initialized")
    
    def set_sdn_policy_engine(self, sdn_policy_engine: SDNPolicyEngine):
        """
        Set SDN policy engine and connect all modules
        
        Args:
            sdn_policy_engine: SDN policy engine instance
        """
        self.sdn_policy_engine = sdn_policy_engine
        
        # Connect modules to SDN policy engine
        self.sdn_policy_engine.set_identity_module(self.onboarding)
        self.sdn_policy_engine.set_trust_module(self.trust_scorer)
        self.sdn_policy_engine.set_analyst_module(self.anomaly_detector)
        self.sdn_policy_engine.set_onboarding_module(self.onboarding)  # For traffic recording during profiling
        
        # Connect SDN policy engine to onboarding for policy application
        self.onboarding.set_sdn_policy_engine(sdn_policy_engine)
        
        # Connect modules to policy adapter and mitigation generator
        self.policy_adapter.set_sdn_policy_engine(sdn_policy_engine)
        self.mitigation_generator.set_sdn_policy_engine(sdn_policy_engine)
        
        # Connect traffic orchestrator
        self.traffic_orchestrator.set_sdn_policy_engine(sdn_policy_engine)
        self.traffic_orchestrator.set_identity_module(self.onboarding)
        self.traffic_orchestrator.set_trust_module(self.trust_scorer)
        self.traffic_orchestrator.set_analyst_module(self.anomaly_detector)
        
        logger.info("SDN policy engine connected")
    
    def start(self):
        """Start the Zero Trust Framework"""
        logger.info("Starting Zero Trust Framework...")
        
        self.running = True
        
        # Deploy honeypot
        logger.info("Deploying honeypot...")
        self.honeypot_deployer.deploy()
        
        # Start background monitoring threads
        self._start_monitoring_threads()
        
        logger.info("Zero Trust Framework started")
    
    def stop(self):
        """Stop the Zero Trust Framework"""
        logger.info("Stopping Zero Trust Framework...")
        
        self.running = False
        
        # Stop all threads
        for thread in self.threads:
            thread.join(timeout=5)
        
        # Stop honeypot
        self.honeypot_deployer.stop()
        
        logger.info("Zero Trust Framework stopped")
    
    def _start_monitoring_threads(self):
        """Start background monitoring threads"""
        # Thread 1: Honeypot log monitoring
        def monitor_honeypot_logs():
            while self.running:
                try:
                    if self.honeypot_deployer.is_running():
                        logs = self.honeypot_deployer.get_logs(tail=50)
                        if logs:
                            threats = self.threat_intelligence.process_logs(logs)
                            if threats:
                                # Generate mitigation rules
                                rules = self.mitigation_generator.generate_rules_from_threats(threats)
                                logger.info(f"Generated {len(rules)} mitigation rules from honeypot")
                except Exception as e:
                    logger.error(f"Error monitoring honeypot logs: {e}")
                
                time.sleep(10)  # Check every 10 seconds
        
        # Thread 2: Device attestation
        def perform_attestations():
            while self.running:
                try:
                    devices = self.onboarding.identity_db.get_all_devices()
                    for device in devices:
                        device_id = device['device_id']
                        cert_path = device.get('certificate_path')
                        
                        if cert_path:
                            result = self.attestation.perform_attestation(
                                device_id,
                                cert_path,
                                self.onboarding.cert_manager
                            )
                            
                            if not result['passed']:
                                # Lower trust score
                                self.trust_scorer.record_attestation_failure(device_id)
                                # Adapt policy
                                self.policy_adapter.adapt_policy_for_device(device_id)
                except Exception as e:
                    logger.error(f"Error performing attestations: {e}")
                
                time.sleep(300)  # Check every 5 minutes
        
        # Thread 3: Policy adaptation based on trust scores
        def adapt_policies():
            while self.running:
                try:
                    devices = self.onboarding.identity_db.get_all_devices()
                    for device in devices:
                        device_id = device['device_id']
                        self.policy_adapter.adapt_policy_for_device(device_id)
                except Exception as e:
                    logger.error(f"Error adapting policies: {e}")
                
                time.sleep(60)  # Check every minute
        
        # Thread 4: Analyst monitoring - poll flow stats and detect anomalies
        def monitor_analyst_alerts():
            processed_alerts = set()  # Track processed alerts to avoid duplicates
            
            while self.running:
                try:
                    if not self.sdn_policy_engine:
                        time.sleep(10)
                        continue
                    
                    # Get all devices
                    devices = self.onboarding.identity_db.get_all_devices()
                    
                    for device in devices:
                        device_id = device['device_id']
                        
                        # Load baseline for device if not already set
                        baseline = self.baseline_manager.get_baseline(device_id)
                        if baseline:
                            self.anomaly_detector.set_baseline(device_id, baseline)
                        
                        # Get recent alerts for this device
                        recent_alerts = self.anomaly_detector.get_recent_alerts(limit=100)
                        device_alerts = [a for a in recent_alerts if a.get('device_id') == device_id]
                        
                        # Process any new alerts (not yet processed)
                        for alert in device_alerts:
                            if not alert.get('is_anomaly'):
                                continue
                            
                            # Create unique alert ID
                            alert_id = f"{device_id}_{alert.get('timestamp', 0)}_{alert.get('anomaly_type', 'unknown')}"
                            
                            # Skip if already processed
                            if alert_id in processed_alerts:
                                continue
                            
                            alert_type = alert.get('anomaly_type', 'anomaly')
                            severity = alert.get('severity', 'low')
                            
                            logger.warning(f"Analyst alert detected: {device_id} - {alert_type} (severity: {severity})")
                            
                            # Mark as processed
                            processed_alerts.add(alert_id)
                            
                            # Keep only recent processed alerts (last 1000)
                            if len(processed_alerts) > 1000:
                                processed_alerts = set(list(processed_alerts)[-1000:])
                            
                            # Handle alert through framework
                            self.handle_analyst_alert(device_id, alert_type, severity)
                            
                            # Use traffic orchestrator for intelligent policy decision
                            if self.traffic_orchestrator:
                                threat_intel = {
                                    'severity': severity,
                                    'alert_type': alert_type,
                                    'indicators': alert.get('indicators', [])
                                }
                                self.traffic_orchestrator.orchestrate_policy(
                                    device_id, threat_intelligence=threat_intel
                                )
                
                except Exception as e:
                    logger.error(f"Error monitoring analyst alerts: {e}")
                
                time.sleep(30)  # Check every 30 seconds
        
        # Start threads
        threads = [
            threading.Thread(target=monitor_honeypot_logs, daemon=True, name="HoneypotMonitor"),
            threading.Thread(target=perform_attestations, daemon=True, name="Attestation"),
            threading.Thread(target=adapt_policies, daemon=True, name="PolicyAdapter"),
            threading.Thread(target=monitor_analyst_alerts, daemon=True, name="AnalystMonitor")
        ]
        
        for thread in threads:
            thread.start()
            self.threads.append(thread)
        
        logger.info(f"Started {len(threads)} monitoring threads")
    
    def handle_analyst_alert(self, device_id: str, alert_type: str, severity: str):
        """
        Handle alert from heuristic analyst
        
        Args:
            device_id: Device identifier
            alert_type: Type of alert
            severity: Alert severity
        """
        # Record in trust scorer
        self.trust_scorer.record_security_alert(device_id, alert_type, severity)
        
        # Notify SDN policy engine
        if self.sdn_policy_engine:
            self.sdn_policy_engine.handle_analyst_alert(device_id, alert_type, severity)
        
        # Adapt policy
        self.policy_adapter.adapt_policy_for_device(device_id)
    
    def get_status(self) -> dict:
        """
        Get framework status
        
        Returns:
            Status dictionary
        """
        devices = self.onboarding.identity_db.get_all_devices()
        
        return {
            'devices': len(devices),
            'honeypot': {
                'running': self.honeypot_deployer.is_running(),
                'status': self.honeypot_deployer.get_status()
            },
            'trust_scores': self.trust_scorer.get_all_scores(),
            'threat_intelligence': self.threat_intelligence.get_statistics(),
            'mitigation_rules': len(self.mitigation_generator.get_generated_rules())
        }

if __name__ == '__main__':
    # Example usage
    framework = ZeroTrustFramework()
    framework.start()
    
    try:
        # Keep running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        framework.stop()

