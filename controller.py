"""
IoT Security Framework Controller
Advanced IoT Security Framework with Software-Defined Networking
"""

import matplotlib
matplotlib.use('Agg')
from flask import Flask, request, render_template, send_file, jsonify
import json
import matplotlib.pyplot as plt
import io
import time
import uuid
from datetime import datetime
import random
import threading
# Try to import ML engine, but make it optional
try:
    from ml_security_engine import initialize_ml_engine, get_ml_engine
    # Check if TensorFlow is actually available
    try:
        import tensorflow as tf
        ML_ENGINE_AVAILABLE = True
    except ImportError:
        ML_ENGINE_AVAILABLE = False
        print("⚠️  TensorFlow not available. ML model features will be limited.")
        print("   System will run with heuristic-based detection")
except ImportError as e:
    ML_ENGINE_AVAILABLE = False
    print(f"⚠️  ML engine not available: {e}")
    print("   System will run without ML-based detection")
    # Create dummy functions
    def initialize_ml_engine():
        return None
    def get_ml_engine():
        return None

app = Flask(__name__)

# Device authorization (static for now, can be dynamic)
authorized_devices = {
    "ESP32_2": True,
    "ESP32_3": True,
    "ESP32_4": False
}
device_data = {"ESP32_2": [], "ESP32_3": [], "ESP32_4": []}
timestamps = []
last_seen = {"ESP32_2": 0, "ESP32_3": 0, "ESP32_4": 0}
device_tokens = {}  # {device_id: {"token": token, "last_activity": timestamp}}
packet_counts = {"ESP32_2": [], "ESP32_3": [], "ESP32_4": []}  # For rate limiting
SESSION_TIMEOUT = 300  # 5 minutes
RATE_LIMIT = 60  # Max 60 packets per minute per device

# Store MAC addresses dynamically
mac_addresses = {
    "ESP32_Gateway": "A0:B1:C2:D3:E4:F5"  # Hardcoded for gateway
    # ESP32 devices will be populated dynamically
}

# SDN Policies
sdn_policies = {
    "packet_inspection": False,
    "traffic_shaping": False,
    "dynamic_routing": False
}

# Simulated policy logs
policy_logs = []

# Simulated SDN metrics
sdn_metrics = {
    "control_plane_latency": 0,  # ms
    "data_plane_throughput": 0,  # Mbps
    "policy_enforcement_rate": 0  # %
}

# Initialize ML Security Engine
ml_engine = None
ml_monitoring_active = False


@app.route('/ml/health')
def ml_health():
    """Get ML engine health status"""
    if not ML_ENGINE_AVAILABLE:
        return json.dumps({
            'status': 'unavailable',
            'message': 'ML engine not available (TensorFlow not installed)'
        }), 503
    
    try:
        global ml_engine
        if not ml_engine:
            return json.dumps({
                'status': 'error',
                'message': 'ML engine not initialized'
            }), 503

        network_stats = getattr(ml_engine, 'network_stats', {})
        is_loaded = getattr(ml_engine, 'is_loaded', False)
        
        health_data = {
            'status': 'healthy' if is_loaded else 'error',
            'uptime': network_stats.get('uptime'),
            'last_health_check': network_stats.get('last_health_check'),
            'model_status': network_stats.get('model_status'),
            'total_packets_processed': network_stats.get('total_packets'),
            'detection_accuracy': network_stats.get('detection_accuracy')
        }

        return json.dumps(health_data), 200 if is_loaded else 503

    except Exception as e:
        app.logger.error(f"Health check error: {str(e)}")
        return json.dumps({
            'status': 'error',
            'message': str(e)
        }), 500

def is_maintenance_window():
    current_hour = datetime.now().hour
    return 2 <= current_hour < 3  # Simulated maintenance window

def simulate_policy_enforcement(device_id):
    if sdn_policies["packet_inspection"] and random.random() > 0.8:
        policy_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Blocked packet from {device_id} due to packet inspection policy")
        return False
    if sdn_policies["traffic_shaping"] and random.random() > 0.9:
        policy_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Delayed packet from {device_id} due to traffic shaping policy")
        time.sleep(0.1)  # Simulate delay
    if sdn_policies["dynamic_routing"]:
        policy_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Rerouted packet from {device_id} via dynamic routing policy")
    return True

def update_sdn_metrics():
    sdn_metrics["control_plane_latency"] = random.randint(5, 50)
    sdn_metrics["data_plane_throughput"] = random.randint(100, 1000)
    sdn_metrics["policy_enforcement_rate"] = random.randint(80, 100)

@app.route('/get_token', methods=['POST'])
def get_token():
    data = request.json
    device_id = data.get('device_id')
    mac_address = data.get('mac_address')  # Get MAC address from request
    if not device_id:
        return json.dumps({'error': 'Missing device_id'}), 400
    if not authorized_devices.get(device_id, False):
        return json.dumps({'error': 'Device not authorized'}), 403
    token = str(uuid.uuid4())
    device_tokens[device_id] = {"token": token, "last_activity": time.time()}
    if mac_address:  # Store the MAC address if provided
        mac_addresses[device_id] = mac_address
    return json.dumps({'token': token})

@app.route('/auth', methods=['POST'])
def auth():
    data = request.json
    device_id = data.get('device_id')
    token = data.get('token')
    if not device_id or not token:
        return json.dumps({'error': 'Missing device_id or token'}), 400

    if device_id not in device_tokens or device_tokens[device_id]["token"] != token:
        return json.dumps({'device_id': device_id, 'authorized': False})

    current_time = time.time()
    last_activity = device_tokens[device_id]["last_activity"]
    if current_time - last_activity > SESSION_TIMEOUT:
        device_tokens.pop(device_id)
        return json.dumps({'device_id': device_id, 'authorized': False})

    device_tokens[device_id]["last_activity"] = current_time

    # Start per-device ML monitoring on first successful auth in this session
    if ML_ENGINE_AVAILABLE:
        global ml_engine, ml_monitoring_active
        if ml_engine is None:
            ml_engine = initialize_ml_engine()
        if ml_engine and hasattr(ml_engine, 'is_loaded') and ml_engine.is_loaded and not ml_monitoring_active:
            # Begin background monitoring
            if hasattr(ml_engine, 'start_monitoring'):
                ml_engine.start_monitoring()
            ml_monitoring_active = True
    return json.dumps({'device_id': device_id, 'authorized': True})

@app.route('/data', methods=['POST'])
def data():
    data = request.json
    device_id = data.get('device_id')
    token = data.get('token')
    packet_time = data.get('timestamp')
    data_value = data.get('data', 0)

    if not device_id or not token or not packet_time:
        return json.dumps({'status': 'rejected'})

    if device_id not in device_tokens or device_tokens[device_id]["token"] != token:
        return json.dumps({'status': 'rejected'})

    current_time = time.time()
    last_activity = device_tokens[device_id]["last_activity"]
    if current_time - last_activity > SESSION_TIMEOUT:
        device_tokens.pop(device_id)
        return json.dumps({'status': 'rejected'})

    if is_maintenance_window():
        return json.dumps({'status': 'rejected', 'reason': 'Maintenance window'})

    packet_counts[device_id].append(current_time)
    packet_counts[device_id] = [t for t in packet_counts[device_id] if current_time - t <= 60]
    if len(packet_counts[device_id]) > RATE_LIMIT:
        return json.dumps({'status': 'rejected', 'reason': 'Rate limit exceeded'})

    # Apply SDN policies
    if not simulate_policy_enforcement(device_id):
        return json.dumps({'status': 'rejected', 'reason': 'SDN policy violation'})

    device_tokens[device_id]["last_activity"] = current_time
    last_seen[device_id] = current_time
    device_data[device_id].append(1)
    if len(timestamps) == 0 or current_time - timestamps[-1] > 1:
        timestamps.append(current_time)
    # Feed packet to ML engine for anomaly detection with device context
    global ml_engine
    try:
        if ml_engine and ml_engine.is_loaded:
            ml_engine.predict_attack({
                'device_id': device_id,
                'size': data.get('size', 0),
                'protocol': data.get('protocol', 6),
                'src_port': data.get('src_port', 0),
                'dst_port': data.get('dst_port', 0),
                'rate': data.get('rate', 0.0),
                'duration': data.get('duration', 0.0),
                'bps': data.get('bps', 0.0),
                'pps': data.get('pps', 0.0),
                'tcp_flags': data.get('tcp_flags', 0),
                'window_size': data.get('window_size', 0),
                'ttl': data.get('ttl', 64),
                'fragment_offset': data.get('fragment_offset', 0),
                'ip_length': data.get('ip_length', 0),
                'tcp_length': data.get('tcp_length', 0),
                'udp_length': data.get('udp_length', 0)
            })
    except Exception as e:
        # Non-fatal for data ingestion; continue normally
        pass

    return json.dumps({'status': 'accepted'})

def generate_graph():
    plt.figure(figsize=(8, 4))
    has_data = False
    for device in device_data:
        if len(device_data[device]) > 0:
            plt.plot(timestamps[-len(device_data[device]):], device_data[device], label=device)
            has_data = True
    if has_data:
        plt.xlabel('Time (s)')
        plt.ylabel('Packets Received')
        plt.legend()
        plt.grid(True)
    else:
        plt.text(0.5, 0.5, 'No data to display', horizontalalignment='center', verticalalignment='center')
        plt.axis('off')
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()
    return buf

@app.route('/')
def dashboard():
    return render_template('dashboard.html', devices=authorized_devices, data={k: sum(v) for k, v in device_data.items()})

@app.route('/graph')
def graph():
    return send_file(generate_graph(), mimetype='image/png')

@app.route('/get_data')
def get_data():
    current_time = time.time()
    data = {}
    for device in device_data:
        packet_count = sum(device_data[device])
        device_packet_counts = [t for t in packet_counts[device] if current_time - t <= 60]
        rate_limit_status = f"{len(device_packet_counts)}/{RATE_LIMIT}"
        blocked_reason = "Maintenance window" if is_maintenance_window() else None
        data[device] = {
            "packets": packet_count,
            "rate_limit_status": rate_limit_status,
            "blocked_reason": blocked_reason
        }
    return json.dumps(data)

@app.route('/update', methods=['POST'])
def update_auth():
    device_id = request.form['device_id']
    action = request.form['action']
    authorized_devices[device_id] = (action == 'authorize')
    if action == 'revoke' and device_id in device_tokens:
        device_tokens.pop(device_id)
    return dashboard()

@app.route('/update_policy', methods=['POST'])
def update_policy():
    policy = request.form['policy']
    action = request.form['action']
    sdn_policies[policy] = (action == 'enable')
    policy_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] {policy.replace('_', ' ').title()} policy {'enabled' if action == 'enable' else 'disabled'}")
    return dashboard()

@app.route('/get_topology')
def get_topology():
    return json.dumps(last_seen)

@app.route('/get_topology_with_mac')
def get_topology_with_mac():
    current_time = time.time()
    topology = {
        "nodes": [],
        "edges": []
    }
    
    # Add gateway node
    topology["nodes"].append({
        "id": "ESP32_Gateway",
        "label": "Gateway",
        "mac": mac_addresses["ESP32_Gateway"],
        "online": True,
        "last_seen": current_time,
        "packets": 0
    })
    
    # Add ESP32 device nodes and edges to gateway
    for device, last_seen_time in last_seen.items():
        online = (current_time - last_seen_time) < 10
        topology["nodes"].append({
            "id": device,
            "label": device,
            "mac": mac_addresses.get(device, "Unknown"),
            "online": online,
            "last_seen": last_seen_time,
            "packets": sum(device_data.get(device, []))
        })
        topology["edges"].append({
            "from": device,
            "to": "ESP32_Gateway"
        })
    
    return json.dumps(topology)

@app.route('/get_health_metrics')
def get_health_metrics():
    current_time = time.time()
    health_data = {}
    for device in device_data:
        online = (current_time - last_seen.get(device, 0)) < 10
        if online:
            health_data[device] = {
                "cpu_usage": random.randint(20, 80),
                "memory_usage": random.randint(30, 90),
                "uptime": int(current_time - last_seen.get(device, current_time))
            }
        else:
            health_data[device] = {
                "cpu_usage": 0,
                "memory_usage": 0,
                "uptime": 0
            }
    return json.dumps(health_data)

@app.route('/get_policy_logs')
def get_policy_logs():
    return json.dumps(policy_logs[-10:])  # Return last 10 logs


@app.route('/toggle_policy/<policy>', methods=['POST'])
def toggle_policy(policy):
    """Toggle a named SDN policy and return its new state as JSON"""
    if policy not in sdn_policies:
        return json.dumps({'error': 'Unknown policy'}), 400

    # flip the policy
    sdn_policies[policy] = not sdn_policies[policy]
    state = sdn_policies[policy]
    policy_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] {policy.replace('_', ' ').title()} policy {'enabled' if state else 'disabled'}")
    return json.dumps({'enabled': state})


@app.route('/clear_policy_logs', methods=['POST'])
def clear_policy_logs():
    """Clear policy logs (useful for UI testing)"""
    policy_logs.clear()
    return json.dumps({'status': 'ok'})


@app.route('/get_security_alerts')
def get_security_alerts():
    """Return recent security alerts. For now, convert policy logs into structured alerts.

    Each alert contains: message, timestamp, severity (low/medium/high), optional device
    """
    alerts = []
    for entry in reversed(policy_logs[-20:]):
        # entries look like: [HH:MM:SS] Message
        try:
            ts_part, msg_part = entry.split(']', 1)
            ts = ts_part.strip('[')
            message = msg_part.strip()
        except Exception:
            ts = datetime.now().strftime('%H:%M:%S')
            message = entry

        # simple severity heuristic
        severity = 'low'
        low_keywords = ['delayed', 'routed', 'rerouted']
        high_keywords = ['blocked', 'attack', 'ddos', 'denied']
        if any(k in message.lower() for k in high_keywords):
            severity = 'high'
        elif any(k in message.lower() for k in low_keywords):
            severity = 'medium'

        alerts.append({
            'timestamp': datetime.now().isoformat(),
            'message': message,
            'severity': severity,
            'device': None
        })

    return json.dumps(alerts)


@app.route('/get_policies')
def get_policies():
    """Return current policy states"""
    return json.dumps(sdn_policies)

@app.route('/get_sdn_metrics')
def get_sdn_metrics():
    update_sdn_metrics()
    return json.dumps(sdn_metrics)

# ML Security Engine Endpoints
@app.route('/ml/initialize')
def initialize_ml():
    """Initialize the ML security engine"""
    if not ML_ENGINE_AVAILABLE:
        return json.dumps({'status': 'error', 'message': 'ML engine not available (TensorFlow not installed)'})
    
    global ml_engine, ml_monitoring_active
    try:
        # Already initialized and healthy
        if ml_engine and hasattr(ml_engine, 'is_loaded') and ml_engine.is_loaded:
            return json.dumps({'status': 'success', 'message': 'ML engine already running'})

        ml_engine = initialize_ml_engine()
        if ml_engine and hasattr(ml_engine, 'is_loaded') and ml_engine.is_loaded:
            ml_monitoring_active = True
            if hasattr(ml_engine, 'start_monitoring'):
                ml_engine.start_monitoring()
            return json.dumps({'status': 'success', 'message': 'ML engine initialized and monitoring started'})
        else:
            return json.dumps({'status': 'error', 'message': 'Failed to initialize ML engine'})
    except Exception as e:
        return json.dumps({'status': 'error', 'message': f'ML initialization failed: {str(e)}'})

@app.route('/ml/status')
def ml_status():
    """Get ML engine status"""
    if not ML_ENGINE_AVAILABLE:
        return json.dumps({
            'status': 'unavailable',
            'monitoring': False,
            'message': 'ML engine not available (TensorFlow not installed)'
        })
    
    global ml_engine, ml_monitoring_active
    
    # Auto-initialize if not running
    if not ml_engine:
        try:
            ml_engine = initialize_ml_engine()
            if ml_engine and hasattr(ml_engine, 'is_loaded') and ml_engine.is_loaded:
                ml_monitoring_active = True
                if hasattr(ml_engine, 'start_monitoring'):
                    ml_engine.start_monitoring()
                app.logger.info("ML engine auto-initialized from status endpoint")
        except Exception as e:
            app.logger.error(f"Auto-initialization failed in status: {e}")
    
    if ml_engine and hasattr(ml_engine, 'is_loaded') and ml_engine.is_loaded:
        stats = {}
        if hasattr(ml_engine, 'get_attack_statistics'):
            stats = ml_engine.get_attack_statistics()
        return json.dumps({
            'status': 'active',
            'monitoring': ml_monitoring_active,
            'statistics': stats
        })
    else:
        return json.dumps({'status': 'inactive', 'monitoring': False})

@app.route('/ml/detections')
def ml_detections():
    """Get recent attack detections"""
    if not ML_ENGINE_AVAILABLE:
        return json.dumps({
            'error': 'ML engine not available',
            'status': 'error',
            'message': 'TensorFlow not installed'
        }), 503
    
    try:
        global ml_engine, ml_monitoring_active
        
        # Auto-initialize if not running
        if not ml_engine:
            try:
                ml_engine = initialize_ml_engine()
                if ml_engine and hasattr(ml_engine, 'is_loaded') and ml_engine.is_loaded:
                    ml_monitoring_active = True
                    if hasattr(ml_engine, 'start_monitoring'):
                        ml_engine.start_monitoring()
                    app.logger.info("ML engine auto-initialized from detections endpoint")
            except Exception as e:
                app.logger.error(f"Auto-initialization failed in detections: {e}")
                return json.dumps({
                    'error': 'ML engine initialization failed',
                    'status': 'error',
                    'message': str(e)
                }), 503

        if not ml_engine:
            return json.dumps({'error': 'ML engine not initialized', 'status': 'error'}), 503

        if not hasattr(ml_engine, 'is_loaded') or not ml_engine.is_loaded:
            return json.dumps({'error': 'ML model not loaded', 'status': 'error'}), 503

        if hasattr(ml_engine, 'attack_detections'):
            detections = list(ml_engine.attack_detections)[-20:]  # Get last 20 detections
        else:
            detections = []

        # Ensure all data is JSON serializable
        clean_detections = []
        for d in detections:
            clean_det = {
                'timestamp': d.get('timestamp'),
                'is_attack': bool(d.get('is_attack', False)),
                'attack_type': str(d.get('attack_type', 'Unknown')),
                'confidence': float(d.get('confidence', 0.0))
            }
            if 'device_id' in d:
                clean_det['device_id'] = str(d.get('device_id'))
            if 'details' in d:
                clean_det['details'] = str(d.get('details'))
            clean_detections.append(clean_det)

        return json.dumps({
            'status': 'success',
            'detections': clean_detections,
            'stats': ml_engine.get_attack_statistics()
        }), 200
    except Exception as e:
        app.logger.error(f"Error in /ml/detections: {str(e)}")
        return json.dumps({
            'error': 'Internal server error',
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/ml/analyze_packet', methods=['POST'])
def analyze_packet():
    """Analyze a specific packet for attacks"""
    if not ML_ENGINE_AVAILABLE:
        return json.dumps({'error': 'ML engine not available (TensorFlow not installed)'})
    
    global ml_engine
    if not ml_engine or not hasattr(ml_engine, 'is_loaded') or not ml_engine.is_loaded:
        return json.dumps({'error': 'ML engine not initialized'})
    
    try:
        packet_data = request.json
        if hasattr(ml_engine, 'predict_attack'):
            result = ml_engine.predict_attack(packet_data)
            return json.dumps(result)
        else:
            return json.dumps({'error': 'ML engine does not support packet analysis'})
    except Exception as e:
        return json.dumps({'error': f'Analysis failed: {str(e)}'})

@app.route('/ml/statistics')
def ml_statistics():
    """Get comprehensive ML statistics"""
    if not ML_ENGINE_AVAILABLE:
        return json.dumps({'error': 'ML engine not available (TensorFlow not installed)'})
    
    global ml_engine
    if ml_engine and hasattr(ml_engine, 'is_loaded') and ml_engine.is_loaded:
        if hasattr(ml_engine, 'get_attack_statistics'):
            stats = ml_engine.get_attack_statistics()
            return json.dumps(stats)
        else:
            return json.dumps({'error': 'ML engine statistics not available'})
    else:
        return json.dumps({'error': 'ML engine not available'})

def start_ml_engine():
    """Initialize and start the ML engine on app startup"""
    if not ML_ENGINE_AVAILABLE:
        print("⚠️  ML engine not available (TensorFlow not installed)")
        print("   System will run with heuristic-based detection only")
        return False
        
    global ml_engine, ml_monitoring_active
    try:
        print("🚀 Initializing ML Security Engine...")
        ml_engine = initialize_ml_engine()
        if ml_engine and hasattr(ml_engine, 'is_loaded') and ml_engine.is_loaded:
            ml_monitoring_active = True
            if hasattr(ml_engine, 'start_monitoring'):
                ml_engine.start_monitoring()
            print("✅ ML Security Engine initialized and monitoring started")
            return True
        else:
            print("⚠️  ML engine initialization skipped (using heuristic detection)")
            return False
    except Exception as e:
        print(f"⚠️  ML initialization failed: {str(e)}")
        print("   System will run with heuristic-based detection only")
        return False

if __name__ == '__main__':
    # Start ML engine before running the app (optional)
    start_ml_engine()
    
    # Run the Flask app
    print("🌐 Starting Flask Controller on http://0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000, use_reloader=False, debug=False)  # disable reloader to prevent duplicate ML engine initialization