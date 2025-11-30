"""
Flow Statistics Analyzer
Polls and analyzes flow statistics from SDN switches
"""

import logging
import time
from typing import Dict, List, Optional

# Try to import Ryu, but make it optional
try:
    from ryu.controller import ofp_event
    from ryu.controller.handler import MAIN_DISPATCHER, set_ev_cls
    from ryu.ofproto import ofproto_v1_3
    from ryu.lib.packet import ethernet, ipv4
    RYU_AVAILABLE = True
except ImportError:
    RYU_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("Ryu not available. Flow analysis features will be limited.")
    # Create dummy classes
    class ofp_event:
        class EventOFPFlowStatsReply:
            pass
    MAIN_DISPATCHER = None
    def set_ev_cls(*args, **kwargs):
        def decorator(func):
            return func
        return decorator

logger = logging.getLogger(__name__)

class FlowAnalyzer:
    """Analyzes flow statistics from SDN switches"""
    
    def __init__(self, datapath, polling_interval=10):
        """
        Initialize flow analyzer
        
        Args:
            datapath: Ryu datapath object
            polling_interval: Interval in seconds to poll flow statistics
        """
        self.datapath = datapath
        self.polling_interval = polling_interval
        self.ofproto = datapath.ofproto
        self.parser = datapath.ofproto_parser
        
        # Flow statistics storage
        self.flow_stats = {}  # {device_id: flow_statistics}
        self.historical_stats = {}  # {device_id: [stats_history]}
        
        # Start polling thread
        self.running = True
        self.polling_thread = None
        
    def start_polling(self):
        """Start polling flow statistics"""
        import threading
        self.polling_thread = threading.Thread(target=self._polling_loop, daemon=True)
        self.polling_thread.start()
        logger.info("Flow statistics polling started")
    
    def stop_polling(self):
        """Stop polling flow statistics"""
        self.running = False
        if self.polling_thread:
            self.polling_thread.join()
        logger.info("Flow statistics polling stopped")
    
    def _polling_loop(self):
        """Main polling loop"""
        while self.running:
            try:
                self.request_flow_stats()
                time.sleep(self.polling_interval)
            except Exception as e:
                logger.error(f"Error in polling loop: {e}")
                time.sleep(5)
    
    def request_flow_stats(self):
        """Request flow statistics from switch"""
        try:
            req = self.parser.OFPFlowStatsRequest(self.datapath)
            self.datapath.send_msg(req)
        except Exception as e:
            logger.error(f"Failed to request flow stats: {e}")
    
    if RYU_AVAILABLE:
        @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
        def flow_stats_reply_handler(self, ev):
            """Handle flow statistics reply from switch"""
            self._handle_flow_stats_reply(ev)
    else:
        def flow_stats_reply_handler(self, ev):
            """Placeholder when Ryu not available"""
            pass
    
    def _handle_flow_stats_reply(self, ev):
        """
        Handle flow statistics reply from switch (internal method)
        
        Args:
            ev: Flow statistics reply event
        """
        if not RYU_AVAILABLE:
            return
            
        body = ev.msg.body
        
        current_time = time.time()
        
        for stat in body:
            # Extract flow information
            match = stat.match
            packet_count = stat.packet_count
            byte_count = stat.byte_count
            duration_sec = stat.duration_sec
            duration_nsec = stat.duration_nsec
            duration = duration_sec + duration_nsec / 1e9
            
            # Get device identifier from match fields
            device_id = self._extract_device_id(match)
            if not device_id:
                continue
            
            # Calculate flow metrics
            if duration > 0:
                packets_per_second = packet_count / duration
                bytes_per_second = byte_count / duration
            else:
                packets_per_second = 0
                bytes_per_second = 0
            
            flow_stat = {
                'device_id': device_id,
                'timestamp': current_time,
                'packet_count': packet_count,
                'byte_count': byte_count,
                'duration': duration,
                'packets_per_second': packets_per_second,
                'bytes_per_second': bytes_per_second,
                'match_fields': {
                    'eth_src': match.get('eth_src', ''),
                    'eth_dst': match.get('eth_dst', ''),
                    'ipv4_src': match.get('ipv4_src', ''),
                    'ipv4_dst': match.get('ipv4_dst', ''),
                    'ip_proto': match.get('ip_proto', 0),
                    'tcp_src': match.get('tcp_src', 0),
                    'tcp_dst': match.get('tcp_dst', 0),
                    'udp_src': match.get('udp_src', 0),
                    'udp_dst': match.get('udp_dst', 0)
                }
            }
            
            # Store statistics
            if device_id not in self.flow_stats:
                self.flow_stats[device_id] = []
                self.historical_stats[device_id] = []
            
            self.flow_stats[device_id].append(flow_stat)
            self.historical_stats[device_id].append(flow_stat)
            
            # Keep only recent history (last 100 entries)
            if len(self.historical_stats[device_id]) > 100:
                self.historical_stats[device_id] = self.historical_stats[device_id][-100:]
    
    def _extract_device_id(self, match) -> Optional[str]:
        """
        Extract device ID from match fields
        
        Args:
            match: OFPMatch object
            
        Returns:
            Device ID or None
        """
        # Try to get MAC address from match
        eth_src = match.get('eth_src', None)
        if eth_src:
            # In real implementation, map MAC to device_id via identity module
            # For now, use MAC as device identifier
            return eth_src
        return None
    
    def get_device_stats(self, device_id: str, window_seconds: int = 60) -> Dict:
        """
        Get aggregated statistics for a device over a time window
        
        Args:
            device_id: Device identifier
            window_seconds: Time window in seconds
            
        Returns:
            Aggregated statistics dictionary
        """
        if device_id not in self.historical_stats:
            return {}
        
        current_time = time.time()
        window_start = current_time - window_seconds
        
        # Filter stats within window
        recent_stats = [
            s for s in self.historical_stats[device_id]
            if s['timestamp'] >= window_start
        ]
        
        if not recent_stats:
            return {}
        
        # Aggregate statistics
        total_packets = sum(s['packet_count'] for s in recent_stats)
        total_bytes = sum(s['byte_count'] for s in recent_stats)
        avg_pps = sum(s['packets_per_second'] for s in recent_stats) / len(recent_stats)
        avg_bps = sum(s['bytes_per_second'] for s in recent_stats) / len(recent_stats)
        
        # Count unique destinations
        destinations = set()
        ports = set()
        for s in recent_stats:
            if s['match_fields'].get('ipv4_dst'):
                destinations.add(s['match_fields']['ipv4_dst'])
            if s['match_fields'].get('tcp_dst'):
                ports.add(s['match_fields']['tcp_dst'])
            if s['match_fields'].get('udp_dst'):
                ports.add(s['match_fields']['udp_dst'])
        
        return {
            'device_id': device_id,
            'window_seconds': window_seconds,
            'total_packets': total_packets,
            'total_bytes': total_bytes,
            'packets_per_second': avg_pps,
            'bytes_per_second': avg_bps,
            'unique_destinations': len(destinations),
            'unique_ports': len(ports),
            'destinations': list(destinations),
            'ports': list(ports),
            'flow_count': len(recent_stats)
        }
    
    def get_all_device_stats(self, window_seconds: int = 60) -> Dict[str, Dict]:
        """
        Get statistics for all devices
        
        Args:
            window_seconds: Time window in seconds
            
        Returns:
            Dictionary mapping device_id to statistics
        """
        all_stats = {}
        for device_id in self.historical_stats.keys():
            all_stats[device_id] = self.get_device_stats(device_id, window_seconds)
        return all_stats

