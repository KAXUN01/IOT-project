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
    from ryu.lib.packet import packet, ethernet, ipv4, arp, tcp, udp
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

from .openflow_rules import OpenFlowRuleGenerator
from .traffic_redirector import TrafficRedirector

logger = logging.getLogger(__name__)

# Define class with proper inheritance based on Ryu availability
if RYU_AVAILABLE:
    class SDNPolicyEngine(app_manager.RyuApp):
        """
        Main SDN Policy Engine Ryu Application
        Enforces Zero Trust policies through OpenFlow rules
        """
        OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
        
        def __init__(self, *args, **kwargs):
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
            self.flow_analyzer_manager = None  # Flow analyzer manager for flow stats
            
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
        
        def set_onboarding_module(self, onboarding_module):
            """Set reference to device onboarding module for traffic recording"""
            self.onboarding_module = onboarding_module
            logger.info("Onboarding module connected for traffic recording")
        
        def set_flow_analyzer_manager(self, flow_analyzer_manager):
            """Set reference to flow analyzer manager for flow statistics"""
            self.flow_analyzer_manager = flow_analyzer_manager
            logger.info("Flow analyzer manager connected")
        
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
            
            # Notify flow analyzer manager of new switch
            if self.flow_analyzer_manager:
                self.flow_analyzer_manager.add_switch(dpid, datapath)
        
        @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
        def flow_stats_reply_handler(self, ev):
            """
            Handle flow statistics reply from switch
            Forward to flow analyzer manager if available
            """
            if self.flow_analyzer_manager:
                dpid = ev.msg.datapath.id
                self.flow_analyzer_manager.handle_flow_stats_reply(dpid, ev)
        
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
            
            # Record traffic for behavioral profiling if device is being profiled
            if device_id and self.onboarding_module:
                try:
                    # Extract packet information for profiling
                    packet_info = {
                        'size': len(msg.data),
                        'src_mac': eth_src,
                        'dst_mac': eth_dst,
                        'in_port': in_port
                    }
                    
                    # Try to extract IP and port information if available
                    ip_pkt = pkt.get_protocol(ipv4.ipv4)
                    if ip_pkt:
                        packet_info['dst_ip'] = ip_pkt.dst
                        packet_info['src_ip'] = ip_pkt.src
                        packet_info['protocol'] = ip_pkt.proto
                        
                        # Try to get TCP/UDP port information
                        tcp_pkt = pkt.get_protocol(tcp.tcp)
                        udp_pkt = pkt.get_protocol(udp.udp)
                        if tcp_pkt:
                            packet_info['dst_port'] = tcp_pkt.dst_port
                            packet_info['src_port'] = tcp_pkt.src_port
                        elif udp_pkt:
                            packet_info['dst_port'] = udp_pkt.dst_port
                            packet_info['src_port'] = udp_pkt.src_port
                    
                    # Record traffic for profiling
                    self.onboarding_module.record_traffic(device_id, packet_info)
                except Exception as e:
                    logger.debug(f"Failed to record traffic for profiling: {e}")
            
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
        
        def apply_policy_from_identity(self, device_id, policy):
            """
            Apply policy from Identity module, translating high-level policy to granular OpenFlow rules
            
            Args:
                device_id: Device identifier
                policy: Policy dictionary from Identity module with structure:
                    {
                        'device_id': str,
                        'action': str,
                        'rules': [{'type': str, 'match': dict, 'priority': int}],
                        'rate_limit': {'packets_per_second': float, 'bytes_per_second': float}
                    }
            """
            if not policy:
                logger.error(f"Empty policy provided for {device_id}")
                return
            
            # Get device MAC address from identity module
            if not self.identity_module:
                logger.error("Identity module not connected")
                return
            
            device_info = self.identity_module.get_device_info(device_id)
            if not device_info or 'mac_address' not in device_info:
                logger.error(f"Cannot apply policy: device {device_id} not found in identity module")
                return
            
            mac_address = device_info['mac_address']
            logger.info(f"Translating policy for {device_id} ({mac_address}) to OpenFlow rules")
            
            # Get policy rules
            policy_rules = policy.get('rules', [])
            if not policy_rules:
                logger.warning(f"No rules in policy for {device_id}, applying default allow")
                self.apply_policy(device_id, 'allow')
                return
            
            # Apply each rule from the policy
            for rule in policy_rules:
                rule_type = rule.get('type', 'allow')
                rule_match = rule.get('match', {})
                rule_priority = rule.get('priority', 100)
                
                # Build match fields starting with device MAC
                match_fields = {'eth_src': mac_address}
                
                # Add policy-specific match fields
                if 'ipv4_dst' in rule_match:
                    match_fields['ipv4_dst'] = rule_match['ipv4_dst']
                if 'ipv4_src' in rule_match:
                    match_fields['ipv4_src'] = rule_match['ipv4_src']
                if 'tcp_dst' in rule_match:
                    match_fields['tcp_dst'] = rule_match['tcp_dst']
                if 'tcp_src' in rule_match:
                    match_fields['tcp_src'] = rule_match['tcp_src']
                if 'udp_dst' in rule_match:
                    match_fields['udp_dst'] = rule_match['udp_dst']
                if 'udp_src' in rule_match:
                    match_fields['udp_src'] = rule_match['udp_src']
                if 'ip_proto' in rule_match:
                    match_fields['ip_proto'] = rule_match['ip_proto']
                
                # Apply rule to all switches
                for dpid, rule_generator in self.rule_generators.items():
                    try:
                        if rule_type == 'allow':
                            flow_mod = rule_generator.create_allow_rule(match_fields, rule_priority)
                            rule_generator.install_rule(flow_mod)
                            logger.debug(f"Installed ALLOW rule for {device_id} on switch {dpid}: {match_fields}")
                        elif rule_type == 'deny':
                            flow_mod = rule_generator.create_deny_rule(match_fields, rule_priority)
                            rule_generator.install_rule(flow_mod)
                            logger.debug(f"Installed DENY rule for {device_id} on switch {dpid}: {match_fields}")
                        else:
                            logger.warning(f"Unknown rule type in policy: {rule_type}")
                    except Exception as e:
                        logger.error(f"Failed to install rule for {device_id} on switch {dpid}: {e}")
            
            # Store policy for reference
            self.device_policies[device_id] = {
                'action': policy.get('action', 'allow'),
                'match_fields': {'eth_src': mac_address},
                'priority': max([r.get('priority', 100) for r in policy_rules], default=100),
                'policy_source': 'identity_module',
                'original_policy': policy
            }
            
            # Handle rate limits (if supported by switch)
            rate_limit = policy.get('rate_limit')
            if rate_limit:
                logger.info(f"Rate limits specified for {device_id}: {rate_limit} (not yet implemented in OpenFlow rules)")
            
            logger.info(f"Successfully applied policy from Identity module for {device_id}: {len(policy_rules)} rules installed")

else:
    class SDNPolicyEngine:
        """
        Main SDN Policy Engine Ryu Application
        Enforces Zero Trust policies through OpenFlow rules
        """
        OFP_VERSIONS = []
        
        def __init__(self, *args, **kwargs):
            # Policy storage
            self.device_policies = {}  # {device_id: {'action': 'allow'|'deny'|'redirect'|'quarantine', 'match_fields': {...}}}
            self.switch_datapaths = {}  # {dpid: datapath}
            self.rule_generators = {}  # {dpid: OpenFlowRuleGenerator}
            self.traffic_redirectors = {}  # {dpid: TrafficRedirector}
            
            # Policy callbacks from other modules
            self.identity_module = None
            self.analyst_module = None
            self.trust_module = None
            self.onboarding_module = None  # For traffic recording during profiling
            
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
        
        def set_onboarding_module(self, onboarding_module):
            """Set reference to device onboarding module for traffic recording"""
            self.onboarding_module = onboarding_module
            logger.info("Onboarding module connected for traffic recording")
        
        def set_flow_analyzer_manager(self, flow_analyzer_manager):
            """Set reference to flow analyzer manager for flow statistics (stub for testing)"""
            self.flow_analyzer_manager = flow_analyzer_manager
            logger.info("Flow analyzer manager connected (stub)")
        
        def apply_policy(self, device_id, action, match_fields=None, priority=100):
            """Apply a policy to a device (stub for testing)"""
            logger.warning("Ryu not available - policy application is a stub")
        
        def remove_policy(self, device_id):
            """Remove policy for a device (stub for testing)"""
            logger.warning("Ryu not available - policy removal is a stub")
        
        def _get_device_policy(self, device_id, eth_src):
            """Get policy for a device (stub for testing)"""
            return {'action': 'allow', 'match_fields': {'eth_src': eth_src}}
        
        def _get_device_id_from_mac(self, mac_address):
            """Get device ID from MAC address (stub for testing)"""
            return None
        
        def handle_analyst_alert(self, device_id, alert_type, severity):
            """Handle alert from heuristic analyst module (stub for testing)"""
            logger.warning(f"Analyst alert (stub): {device_id} - {alert_type} (severity: {severity})")
        
        def handle_trust_score_change(self, device_id, new_score):
            """Handle trust score change (stub for testing)"""
            logger.warning(f"Trust score change (stub): {device_id} - {new_score}")
        
        def apply_policy_from_identity(self, device_id, policy):
            """Apply policy from Identity module (stub for testing)"""
            logger.warning(f"Policy from Identity module (stub): {device_id} - {policy}")
