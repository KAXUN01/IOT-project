"""
SDN Policy Engine - Main Ryu Application
Central policy enforcement point for Zero Trust SDN Framework
"""

import logging
import threading
import time

# Try to import Ryu, but make it optional for testing
try:
    from ryu.base import app_manager
    from ryu.controller import ofp_event
    from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
    from ryu.ofproto import ofproto_v1_3
    from ryu.lib.packet import packet, ethernet, ipv4, arp
    RYU_AVAILABLE = True
except ImportError:
    RYU_AVAILABLE = False
    # Create dummy classes for testing
    class app_manager:
        class RyuApp:
            pass
    class ofp_event:
        class EventOFPSwitchFeatures:
            pass
        class EventOFPPacketIn:
            pass
    CONFIG_DISPATCHER = MAIN_DISPATCHER = 0
    def set_ev_cls(*args, **kwargs):
        def decorator(func):
            return func
        return decorator
    ofproto_v1_3 = type('obj', (object,), {'OFP_VERSION': 0x04})

from ryu_controller.openflow_rules import OpenFlowRuleGenerator
from ryu_controller.traffic_redirector import TrafficRedirector

logger = logging.getLogger(__name__)

class SDNPolicyEngine:
    """
    Main SDN Policy Engine Ryu Application
    Enforces Zero Trust policies through OpenFlow rules
    """
    
    if RYU_AVAILABLE:
        OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    else:
        OFP_VERSIONS = []
    
    def __init__(self, *args, **kwargs):
        if RYU_AVAILABLE:
            super(SDNPolicyEngine, self).__init__(*args, **kwargs)
        
        # Policy storage
        self.device_policies = {}  # {device_id: {'action': 'allow'|'deny'|'redirect'|'quarantine', 'match_fields': {...}}}
        self.switch_datapaths = {}  # {dpid: datapath}
        self.rule_generators = {}  # {dpid: OpenFlowRuleGenerator}
        self.traffic_redirectors = {}  # {dpid: TrafficRedirector}
        
        # Policy callbacks from other modules
        self.identity_module = None
        self.analyst_module = None
        self.trust_module = None
        
        # Honeypot port (default)
        self.honeypot_port = 3
        self.quarantine_port = 4
        
        logger.info("SDN Policy Engine initialized")
    
    def set_identity_module(self, identity_module):
        """Set reference to identity management module"""
        self.identity_module = identity_module
        logger.info("Identity module connected")
    
    def set_analyst_module(self, analyst_module):
        """Set reference to heuristic analyst module"""
        self.analyst_module = analyst_module
        logger.info("Analyst module connected")
    
    def set_trust_module(self, trust_module):
        """Set reference to trust evaluation module"""
        self.trust_module = trust_module
        logger.info("Trust module connected")
    
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        """
        Handle switch connection and initialize flow tables
        """
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        
        # Store datapath
        dpid = datapath.id
        self.switch_datapaths[dpid] = datapath
        self.rule_generators[dpid] = OpenFlowRuleGenerator(datapath)
        self.traffic_redirectors[dpid] = TrafficRedirector(datapath, self.honeypot_port)
        
        logger.info(f"Switch {dpid} connected")
        
        # Install default rule: send to controller for unknown packets
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(
            datapath=datapath,
            match=match,
            cookie=0,
            command=ofproto.OFPFC_ADD,
            idle_timeout=0,
            hard_timeout=0,
            priority=0,
            instructions=inst
        )
        datapath.send_msg(mod)
        
        logger.info(f"Default rule installed on switch {dpid}")
    
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        """
        Handle packets sent to controller (unknown flows)
        """
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']
        
        dpid = datapath.id
        
        # Parse packet
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)
        
        if eth is None:
            return
        
        eth_src = eth.src
        eth_dst = eth.dst
        
        # Get device policy
        device_id = self._get_device_id_from_mac(eth_src)
        policy = self._get_device_policy(device_id, eth_src)
        
        # Apply policy
        if policy['action'] == 'allow':
            # Install allow rule and forward
            match = parser.OFPMatch(eth_src=eth_src, eth_dst=eth_dst)
            actions = [parser.OFPActionOutput(ofproto.OFPP_FLOOD)]
            inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
            mod = parser.OFPFlowMod(
                datapath=datapath,
                match=match,
                cookie=0,
                command=ofproto.OFPFC_ADD,
                idle_timeout=0,
                hard_timeout=0,
                priority=100,
                instructions=inst
            )
            datapath.send_msg(mod)
            
        elif policy['action'] == 'deny':
            # Drop packet (no rule installed)
            logger.warning(f"Denied packet from {device_id} ({eth_src})")
            return
            
        elif policy['action'] == 'redirect':
            # Redirect to honeypot
            match_fields = {'eth_src': eth_src}
            if dpid in self.traffic_redirectors:
                self.traffic_redirectors[dpid].redirect_to_honeypot(
                    device_id, match_fields
                )
            logger.warning(f"Redirected packet from {device_id} ({eth_src}) to honeypot")
            
        elif policy['action'] == 'quarantine':
            # Redirect to quarantine network
            match = parser.OFPMatch(eth_src=eth_src)
            actions = [parser.OFPActionOutput(self.quarantine_port)]
            inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
            mod = parser.OFPFlowMod(
                datapath=datapath,
                match=match,
                cookie=0,
                command=ofproto.OFPFC_ADD,
                idle_timeout=0,
                hard_timeout=0,
                priority=180,
                instructions=inst
            )
            datapath.send_msg(mod)
            logger.warning(f"Quarantined device {device_id} ({eth_src})")
    
    def apply_policy(self, device_id, action, match_fields=None, priority=100):
        """
        Apply a policy to a device across all switches
        
        Args:
            device_id: Device identifier
            action: Policy action ('allow', 'deny', 'redirect', 'quarantine')
            match_fields: Match fields for the rule (default: device MAC)
            priority: Rule priority
        """
        if match_fields is None:
            # Get device MAC from identity module
            if self.identity_module:
                device_info = self.identity_module.get_device_info(device_id)
                if device_info and 'mac_address' in device_info:
                    match_fields = {'eth_src': device_info['mac_address']}
                else:
                    logger.error(f"Cannot apply policy: device {device_id} not found")
                    return
            else:
                logger.error("Identity module not connected")
                return
        
        # Store policy
        self.device_policies[device_id] = {
            'action': action,
            'match_fields': match_fields,
            'priority': priority
        }
        
        # Apply to all switches
        for dpid, rule_generator in self.rule_generators.items():
            try:
                if action == 'allow':
                    flow_mod = rule_generator.create_allow_rule(match_fields, priority)
                elif action == 'deny':
                    flow_mod = rule_generator.create_deny_rule(match_fields, priority)
                elif action == 'redirect':
                    if dpid in self.traffic_redirectors:
                        self.traffic_redirectors[dpid].redirect_to_honeypot(
                            device_id, match_fields, priority
                        )
                    continue
                elif action == 'quarantine':
                    flow_mod = rule_generator.create_quarantine_rule(
                        match_fields, self.quarantine_port, priority
                    )
                else:
                    logger.error(f"Unknown policy action: {action}")
                    continue
                
                if action != 'redirect':
                    rule_generator.install_rule(flow_mod)
                
                logger.info(f"Applied {action} policy to {device_id} on switch {dpid}")
                
            except Exception as e:
                logger.error(f"Failed to apply policy to {device_id} on switch {dpid}: {e}")
    
    def remove_policy(self, device_id):
        """
        Remove policy for a device
        
        Args:
            device_id: Device identifier
        """
        if device_id not in self.device_policies:
            return
        
        policy = self.device_policies[device_id]
        match_fields = policy['match_fields']
        
        # Remove from all switches
        for dpid, rule_generator in self.rule_generators.items():
            try:
                flow_mod = rule_generator.delete_rule(match_fields)
                rule_generator.install_rule(flow_mod)
                
                # Remove redirect if active
                if dpid in self.traffic_redirectors:
                    self.traffic_redirectors[dpid].remove_redirect(device_id)
                
            except Exception as e:
                logger.error(f"Failed to remove policy for {device_id} on switch {dpid}: {e}")
        
        del self.device_policies[device_id]
        logger.info(f"Removed policy for {device_id}")
    
    def _get_device_policy(self, device_id, eth_src):
        """
        Get policy for a device
        
        Args:
            device_id: Device identifier
            eth_src: Ethernet source address
            
        Returns:
            Policy dictionary
        """
        if device_id in self.device_policies:
            return self.device_policies[device_id]
        
        # Default: check trust score if trust module available
        if self.trust_module:
            trust_score = self.trust_module.get_trust_score(device_id)
            if trust_score is not None:
                if trust_score < 30:
                    return {'action': 'quarantine', 'match_fields': {'eth_src': eth_src}}
                elif trust_score < 50:
                    return {'action': 'deny', 'match_fields': {'eth_src': eth_src}}
                elif trust_score < 70:
                    return {'action': 'redirect', 'match_fields': {'eth_src': eth_src}}
        
        # Default: allow
        return {'action': 'allow', 'match_fields': {'eth_src': eth_src}}
    
    def _get_device_id_from_mac(self, mac_address):
        """
        Get device ID from MAC address
        
        Args:
            mac_address: MAC address
            
        Returns:
            Device ID or None
        """
        if self.identity_module:
            return self.identity_module.get_device_id_from_mac(mac_address)
        return None
    
    def handle_analyst_alert(self, device_id, alert_type, severity):
        """
        Handle alert from heuristic analyst module
        
        Args:
            device_id: Device identifier
            alert_type: Type of alert (e.g., 'dos', 'scanning', 'anomaly')
            severity: Alert severity ('low', 'medium', 'high')
        """
        logger.warning(f"Analyst alert: {device_id} - {alert_type} (severity: {severity})")
        
        # Apply redirect policy for suspicious activity
        if severity in ['medium', 'high']:
            self.apply_policy(device_id, 'redirect')
            
            # Notify trust module to lower trust score
            if self.trust_module:
                self.trust_module.adjust_trust_score(device_id, -20, f"Analyst alert: {alert_type}")
    
    def handle_trust_score_change(self, device_id, new_score):
        """
        Handle trust score change from trust evaluation module
        
        Args:
            device_id: Device identifier
            new_score: New trust score (0-100)
        """
        # Adjust policy based on trust score
        if new_score < 30:
            self.apply_policy(device_id, 'quarantine')
        elif new_score < 50:
            self.apply_policy(device_id, 'deny')
        elif new_score < 70:
            self.apply_policy(device_id, 'redirect')
        else:
            self.apply_policy(device_id, 'allow')

