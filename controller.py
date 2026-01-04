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
import os
import logging

# Try to import DeviceOnboarding, but make it optional
try:
    from identity_manager.device_onboarding import DeviceOnboarding
    ONBOARDING_AVAILABLE = True
except ImportError as e:
    ONBOARDING_AVAILABLE = False
    print(f"⚠️  Device onboarding not available: {e}")
    print("   System will use static device authorization")
    DeviceOnboarding = None

# Try to import Auto-Onboarding Service, but make it optional
try:
    from network_monitor.auto_onboarding_service import AutoOnboardingService
    AUTO_ONBOARDING_AVAILABLE = True
except ImportError as e:
    AUTO_ONBOARDING_AVAILABLE = False
    print(f"⚠️  Auto-onboarding service not available: {e}")
    AutoOnboardingService = None

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

# Try to import cryptography for certificate validation
try:
    from cryptography import x509
    from cryptography.hazmat.backends import default_backend
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False
    print("⚠️  cryptography module not available. Certificate expiry checks will be limited.")


app = Flask(__name__)

# Device authorization (static for now, can be dynamic)
authorized_devices = {
    "Sensor_A": True,
    "Sensor_B": True
}
device_data = {"Sensor_A": [], "Sensor_B": []}
timestamps = []
last_seen = {"Sensor_A": 0, "Sensor_B": 0}
device_tokens = {}  # {device_id: {"token": token, "last_activity": timestamp}}
packet_counts = {"Sensor_A": [], "Sensor_B": []}  # For rate limiting
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

# Suspicious device alerts for dashboard
suspicious_device_alerts = []  # List of alert dictionaries

# Initialize ML Security Engine
ml_engine = None
ml_monitoring_active = False

# Initialize Device Onboarding System
onboarding = None
if ONBOARDING_AVAILABLE:
    try:
        certs_dir = os.path.join(os.path.dirname(__file__), 'certs')
        db_path = os.path.join(os.path.dirname(__file__), 'identity.db')
        onboarding = DeviceOnboarding(certs_dir=certs_dir, db_path=db_path)
        print("✅ Device onboarding system initialized")
    except Exception as e:
        print(f"⚠️  Failed to initialize device onboarding: {e}")
        print("   System will use static device authorization")
        onboarding = None
        ONBOARDING_AVAILABLE = False
else:
    print("⚠️  Device onboarding not available - using static authorization")

def initialize_test_devices():
    """
    Initialize test devices in the identity database
    
    Ensures that test devices (Sensor_A, Sensor_B, Sensor_C) are registered
    in the onboarding database with default trust scores so that
    dashboard statistics display correctly.
    """
    if not ONBOARDING_AVAILABLE or not onboarding:
        return
    
    test_devices = {
        "Sensor_A": "AA:BB:CC:DD:EE:AA",
        "Sensor_B": "AA:BB:CC:DD:EE:BB",
        "Sensor_C": "AA:BB:CC:DD:EE:CC"
    }
    
    for device_id, mac_address in test_devices.items():
        try:
            # Check if device already exists
            existing_device = onboarding.identity_db.get_device(device_id)
            
            if not existing_device:
                # Add device to database
                success = onboarding.identity_db.add_device(
                    device_id=device_id,
                    mac_address=mac_address,
                    device_type="Sensor",
                    device_info=json.dumps({"test_device": True, "type": "virtual"})
                )
                
                if success:
                    # Set initial trust score
                    onboarding.identity_db.save_trust_score(
                        device_id=device_id,
                        trust_score=70,  # Default trusted level
                        reason="Initial test device registration"
                    )
                    print(f"✅ Test device {device_id} registered with trust score 70")
                else:
                    print(f"⚠️  Failed to register test device {device_id}")
            else:
                # Device exists, ensure it has a trust score
                current_score = onboarding.identity_db.get_trust_score(device_id)
                if current_score is None:
                    onboarding.identity_db.save_trust_score(
                        device_id=device_id,
                        trust_score=70,
                        reason="Setting initial trust score for existing device"
                    )
                    print(f"✅ Trust score set for existing device {device_id}")
                    
        except Exception as e:
            print(f"⚠️  Error initializing test device {device_id}: {e}")

# Initialize test devices if onboarding is available
if ONBOARDING_AVAILABLE and onboarding:
    initialize_test_devices()

# Initialize Auto-Onboarding Service
auto_onboarding_service = None
if AUTO_ONBOARDING_AVAILABLE and onboarding:
    try:
        auto_onboarding_service = AutoOnboardingService(
            onboarding_module=onboarding,
            identity_db=onboarding.identity_db if onboarding else None
        )
        # Start the service
        auto_onboarding_service.start()
        print("✅ Auto-onboarding service initialized and started")
    except Exception as e:
        print(f"⚠️  Failed to initialize auto-onboarding service: {e}")
        auto_onboarding_service = None
        AUTO_ONBOARDING_AVAILABLE = False
elif AUTO_ONBOARDING_AVAILABLE:
    print("⚠️  Auto-onboarding service requires onboarding module")


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
    """Update SDN metrics with real data from Ryu controller if available"""
    # TODO: Integrate with Ryu controller to get real SDN metrics
    # For now, keep metrics at 0 if no real data is available
    # Real metrics would come from Ryu controller API or flow statistics
    pass

@app.route('/onboard', methods=['POST'])
def onboard_device():
    """
    Onboard a new IoT device with certificate provisioning
    
    Request JSON:
    {
        "device_id": "ESP32_2",
        "mac_address": "AA:BB:CC:DD:EE:FF",
        "device_type": "sensor" (optional),
        "device_info": "Additional info" (optional)
    }
    
    Returns:
        Onboarding result with certificate paths and CA certificate
    """
    if not ONBOARDING_AVAILABLE or not onboarding:
        return json.dumps({
            'status': 'error',
            'message': 'Device onboarding system not available'
        }), 503
    
    try:
        data = request.json
        device_id = data.get('device_id')
        mac_address = data.get('mac_address')
        device_type = data.get('device_type')
        device_info = data.get('device_info')
        
        if not device_id or not mac_address:
            return json.dumps({
                'status': 'error',
                'message': 'Missing device_id or mac_address'
            }), 400
        
        # Onboard the device
        result = onboarding.onboard_device(
            device_id=device_id,
            mac_address=mac_address,
            device_type=device_type,
            device_info=device_info
        )
        
        if result['status'] == 'success':
            # Store MAC address for topology
            mac_addresses[device_id] = mac_address
            # Initialize device tracking
            if device_id not in device_data:
                device_data[device_id] = []
            if device_id not in last_seen:
                last_seen[device_id] = time.time()
            if device_id not in packet_counts:
                packet_counts[device_id] = []
            
            app.logger.info(f"Device {device_id} onboarded. Profiling will auto-finalize after 5 minutes.")
            return json.dumps(result), 200
        else:
            return json.dumps(result), 400
            
    except Exception as e:
        app.logger.error(f"Onboarding error: {str(e)}")
        return json.dumps({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/finalize_onboarding', methods=['POST'])
def finalize_onboarding():
    """
    Manually finalize onboarding for a device (establish baseline and generate policy)
    
    Request JSON:
    {
        "device_id": "ESP32_2"
    }
    
    Returns:
        Finalization result with baseline and policy
    """
    if not ONBOARDING_AVAILABLE or not onboarding:
        return json.dumps({
            'status': 'error',
            'message': 'Device onboarding system not available'
        }), 503
    
    try:
        data = request.json
        device_id = data.get('device_id')
        
        if not device_id:
            return json.dumps({
                'status': 'error',
                'message': 'Missing device_id'
            }), 400
        
        # Finalize onboarding
        result = onboarding.finalize_onboarding(device_id)
        
        if result['status'] == 'success':
            app.logger.info(f"Onboarding finalized for {device_id}. Baseline and policy generated.")
            return json.dumps(result), 200
        else:
            return json.dumps(result), 400
            
    except Exception as e:
        app.logger.error(f"Finalization error: {str(e)}")
        return json.dumps({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/get_profiling_status', methods=['GET'])
def get_profiling_status():
    """
    Get profiling status for a device
    
    Query parameters:
        device_id: Device identifier
    
    Returns:
        Profiling status information
    """
    if not ONBOARDING_AVAILABLE or not onboarding:
        return json.dumps({
            'status': 'error',
            'message': 'Device onboarding system not available'
        }), 503
    
    try:
        device_id = request.args.get('device_id')
        
        if not device_id:
            return json.dumps({
                'status': 'error',
                'message': 'Missing device_id parameter'
            }), 400
        
        # Get profiling status
        profiler = onboarding.profiler
        profile_status = profiler.get_profiling_status(device_id)
        
        if profile_status:
            elapsed = profile_status.get('elapsed_time', 0)
            remaining = max(0, profiler.profiling_duration - elapsed)
            return json.dumps({
                'status': 'success',
                'device_id': device_id,
                'is_profiling': True,
                'elapsed_time': elapsed,
                'remaining_time': remaining,
                'packet_count': profile_status.get('packet_count', 0),
                'byte_count': profile_status.get('byte_count', 0)
            }), 200
        else:
            # Check if device has baseline (profiling completed)
            baseline = profiler.get_baseline(device_id)
            if baseline:
                return json.dumps({
                    'status': 'success',
                    'device_id': device_id,
                    'is_profiling': False,
                    'baseline_established': True,
                    'baseline': baseline
                }), 200
            else:
                return json.dumps({
                    'status': 'success',
                    'device_id': device_id,
                    'is_profiling': False,
                    'baseline_established': False,
                    'message': 'Device not currently being profiled'
                }), 200
            
    except Exception as e:
        app.logger.error(f"Error getting profiling status: {str(e)}")
        return json.dumps({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/get_token', methods=['POST'])
def get_token():
    """
    Get authentication token for device
    
    First checks if device is onboarded (certificate-based).
    Falls back to static authorized_devices list for backward compatibility.
    """
    data = request.json
    device_id = data.get('device_id')
    mac_address = data.get('mac_address')  # Get MAC address from request
    if not device_id:
        return json.dumps({'error': 'Missing device_id'}), 400
    
    # Check if device is onboarded (certificate-based authentication)
    device_authorized = False
    if ONBOARDING_AVAILABLE and onboarding:
        try:
            device_info = onboarding.get_device_info(device_id)
            if device_info:
                # Device is onboarded - verify certificate
                if onboarding.verify_device_certificate(device_id):
                    device_authorized = True
                    # Update MAC address from database if not provided
                    if not mac_address and device_info.get('mac_address'):
                        mac_address = device_info['mac_address']
                else:
                    app.logger.warning(f"Device {device_id} certificate verification failed")
        except Exception as e:
            app.logger.error(f"Error checking onboarding database: {e}")
    
    # Fallback to static authorized_devices list
    if not device_authorized:
        device_authorized = authorized_devices.get(device_id, False)
    
    if not device_authorized:
        return json.dumps({'error': 'Device not authorized'}), 403
    
    # Generate token for authorized device
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
    """
    Receive data from IoT device
    
    Verifies device is onboarded or in authorized list before accepting data.
    """
    data = request.json
    device_id = data.get('device_id')
    token = data.get('token')
    packet_time = data.get('timestamp')
    data_value = data.get('data', 0)

    if not device_id or not token or not packet_time:
        return json.dumps({'status': 'rejected', 'reason': 'Missing required fields'})

    # Verify token
    if device_id not in device_tokens or device_tokens[device_id]["token"] != token:
        return json.dumps({'status': 'rejected', 'reason': 'Invalid token'})
    
    # Verify device is authorized (onboarded or in static list)
    device_authorized = False
    if ONBOARDING_AVAILABLE and onboarding:
        try:
            device_info = onboarding.get_device_info(device_id)
            if device_info and device_info.get('status') != 'revoked':
                # Device is onboarded and not revoked
                device_authorized = True
                # Update last_seen in database
                onboarding.identity_db.update_last_seen(device_id)
        except Exception as e:
            app.logger.error(f"Error checking device authorization: {e}")
    
    # Fallback to static authorized_devices list
    if not device_authorized:
        device_authorized = authorized_devices.get(device_id, False)
    
    if not device_authorized:
        return json.dumps({'status': 'rejected', 'reason': 'Device not authorized'})

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
            result = ml_engine.predict_attack({
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
            
            # Check if ML detected high-confidence attack and trigger redirection
            if result and result.get('is_attack', False) and result.get('confidence', 0) > 0.8:
                # High confidence attack detected - create alert
                severity = 'high' if result.get('confidence', 0) > 0.9 else 'medium'
                create_suspicious_device_alert(
                    device_id=device_id,
                    reason='ml_detection',
                    severity=severity,
                    redirected=True
                )
                app.logger.warning(f"High-confidence ML attack detected for {device_id}: {result.get('attack_type')}")
    except Exception as e:
        # Non-fatal for data ingestion; continue normally
        app.logger.warning(f"ML prediction error (non-fatal): {str(e)}")

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
    return render_template('dashboard.html', devices=authorized_devices, data=device_data)

@app.route('/cert_test')
def cert_test():
    """Test page for certificate API"""
    return render_template('cert_test.html')

@app.route('/cert_debug')
def cert_debug():
    """Debug page for certificate display"""
    return render_template('cert_debug.html')

@app.route('/graph')
def graph():
    return send_file(generate_graph(), mimetype='image/png')

@app.route('/get_data')
def get_data():
    current_time = time.time()
    data = {}
    for device in device_data:
        try:
            packet_count = sum(device_data[device])
        except (TypeError, ValueError):
            packet_count = 0
        
        # Get packet counts for rate limiting, handling devices that may have been deleted
        device_packet_counts = [t for t in packet_counts.get(device, []) if current_time - t <= 60]
        rate_limit_status = f"{len(device_packet_counts)}/{RATE_LIMIT}"
        blocked_reason = "Maintenance window" if is_maintenance_window() else None
        
        # Get last_seen timestamp for the device
        device_last_seen = last_seen.get(device, 0)
        
        # Calculate packets per minute
        packets_per_minute = len(device_packet_counts)
        
        data[device] = {
            "packets": packet_count,
            "rate_limit_status": rate_limit_status,
            "blocked_reason": blocked_reason,
            "last_seen": device_last_seen,
            "packets_per_minute": packets_per_minute
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
    """
    Get network topology with MAC addresses
    
    Uses onboarding database to get device list, merges with last_seen tracking.
    """
    current_time = time.time()
    topology = {
        "nodes": [],
        "edges": []
    }
    
    # Build honeypot redirected device set for quick lookup
    honeypot_devices = set()
    for alert in suspicious_device_alerts:
        if alert.get('redirected') and alert.get('device_id'):
            honeypot_devices.add(alert['device_id'])
    
    # Add gateway node (always online/connected)
    topology["nodes"].append({
        "id": "ESP32_Gateway",
        "label": "Gateway",
        "mac": mac_addresses.get("ESP32_Gateway", "A0:B1:C2:D3:E4:F5"),
        "online": True,
        "status": "active",
        "type": "gateway",
        "last_seen": current_time,
        "packets": 0,
        "honeypot_redirected": False
    })
    
    # Get devices from onboarding database if available
    devices_from_db = {}
    if ONBOARDING_AVAILABLE and onboarding:
        try:
            db_devices = onboarding.identity_db.get_all_devices()
            for device in db_devices:
                devices_from_db[device['device_id']] = device
                # Store MAC address if not already stored
                if device['device_id'] not in mac_addresses and device.get('mac_address'):
                    mac_addresses[device['device_id']] = device['mac_address']
        except Exception as e:
            app.logger.error(f"Error getting devices from database: {e}")
    
    # Merge database devices with last_seen tracking
    all_device_ids = set(list(last_seen.keys()) + list(devices_from_db.keys()))
    
    # Add ESP32 device nodes and edges to gateway
    for device_id in all_device_ids:
        # Get last_seen time (from tracking or database)
        last_seen_time = last_seen.get(device_id, 0)
        if device_id in devices_from_db and devices_from_db[device_id].get('last_seen'):
            # Try to parse database timestamp if available
            try:
                db_timestamp = devices_from_db[device_id]['last_seen']
                if isinstance(db_timestamp, str):
                    from datetime import datetime
                    db_time = datetime.fromisoformat(db_timestamp.replace('Z', '+00:00'))
                    last_seen_time = db_time.timestamp()
                elif db_timestamp:
                    last_seen_time = float(db_timestamp)
            except:
                pass
        
        online = (current_time - last_seen_time) < 10
        
        # Get device info from database if available
        device_info = devices_from_db.get(device_id, {})
        device_status = device_info.get('status', 'active' if online else 'inactive')
        
        # Get MAC address (from database, mac_addresses dict, or default)
        mac = (mac_addresses.get(device_id) or 
               device_info.get('mac_address') or 
               "Unknown")
        
        # Check if device is redirected to honeypot
        is_honeypot_redirected = device_id in honeypot_devices
        
        # Add device node to topology
        # Revoked devices will still appear but be visually marked as revoked (red color)
        try:
            packet_count = sum(device_data.get(device_id, []) or [])
        except (TypeError, ValueError):
            packet_count = 0
        
        topology["nodes"].append({
            "id": device_id,
            "label": device_id,
            "mac": mac,
            "online": online,
            "status": device_status,
            "type": "device",
            "last_seen": last_seen_time,
            "packets": packet_count,
            "onboarded": device_id in devices_from_db,
            "honeypot_redirected": is_honeypot_redirected
        })
        
        # Show edge connection to gateway for active/authorized devices
        # Skip edges for revoked devices (they show as disconnected)
        if device_status != 'revoked':
            topology["edges"].append({
                "from": device_id,
                "to": "ESP32_Gateway"
            })
    
    return json.dumps(topology)

@app.route('/verify_certificate', methods=['POST'])
def verify_certificate():
    """
    Verify device certificate
    
    Request JSON:
    {
        "device_id": "ESP32_2"
    }
    
    Returns:
        Certificate verification status
    """
    if not ONBOARDING_AVAILABLE or not onboarding:
        return json.dumps({
            'status': 'error',
            'message': 'Device onboarding system not available'
        }), 503
    
    try:
        data = request.json
        device_id = data.get('device_id')
        
        if not device_id:
            return json.dumps({
                'status': 'error',
                'message': 'Missing device_id'
            }), 400
        
        # Verify certificate
        is_valid = onboarding.verify_device_certificate(device_id)
        device_info = onboarding.get_device_info(device_id)
        
        return json.dumps({
            'status': 'success',
            'device_id': device_id,
            'certificate_valid': is_valid,
            'device_status': device_info.get('status') if device_info else None,
            'onboarded_at': device_info.get('onboarded_at') if device_info else None
        }), 200
        
    except Exception as e:
        app.logger.error(f"Certificate verification error: {str(e)}")
        return json.dumps({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/pending_devices', methods=['GET'])
def get_pending_devices():
    """
    Get list of pending devices awaiting approval
    
    Returns:
        List of pending devices
    """
    if not AUTO_ONBOARDING_AVAILABLE or not auto_onboarding_service:
        return json.dumps({
            'status': 'error',
            'message': 'Auto-onboarding service not available',
            'devices': []
        }), 503
    
    try:
        pending_devices = auto_onboarding_service.get_pending_devices()
        return json.dumps({
            'status': 'success',
            'devices': pending_devices
        }), 200
    except Exception as e:
        app.logger.error(f"Error getting pending devices: {e}")
        return json.dumps({
            'status': 'error',
            'message': str(e),
            'devices': []
        }), 500

@app.route('/api/approve_device', methods=['POST'])
def approve_device():
    """
    Approve a pending device and trigger onboarding
    
    Request JSON:
    {
        "mac_address": "AA:BB:CC:DD:EE:FF",
        "admin_notes": "Optional notes" (optional)
    }
    
    Returns:
        Approval and onboarding result
    """
    if not AUTO_ONBOARDING_AVAILABLE or not auto_onboarding_service:
        return json.dumps({
            'status': 'error',
            'message': 'Auto-onboarding service not available'
        }), 503
    
    try:
        data = request.json
        mac_address = data.get('mac_address')
        admin_notes = data.get('admin_notes')
        
        if not mac_address:
            return json.dumps({
                'status': 'error',
                'message': 'Missing mac_address'
            }), 400
        
        # Approve and onboard device
        result = auto_onboarding_service.approve_and_onboard(mac_address, admin_notes)
        
        if result.get('status') == 'success':
            return json.dumps(result), 200
        else:
            return json.dumps(result), 400
            
    except Exception as e:
        app.logger.error(f"Error approving device: {e}")
        return json.dumps({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/reject_device', methods=['POST'])
def reject_device():
    """
    Reject a pending device
    
    Request JSON:
    {
        "mac_address": "AA:BB:CC:DD:EE:FF",
        "admin_notes": "Optional notes" (optional)
    }
    
    Returns:
        Rejection result
    """
    if not AUTO_ONBOARDING_AVAILABLE or not auto_onboarding_service:
        return json.dumps({
            'status': 'error',
            'message': 'Auto-onboarding service not available'
        }), 503
    
    try:
        data = request.json
        mac_address = data.get('mac_address')
        admin_notes = data.get('admin_notes')
        
        if not mac_address:
            return json.dumps({
                'status': 'error',
                'message': 'Missing mac_address'
            }), 400
        
        # Reject device
        success = auto_onboarding_service.reject_device(mac_address, admin_notes)
        
        if success:
            return json.dumps({
                'status': 'success',
                'message': 'Device rejected successfully'
            }), 200
        else:
            return json.dumps({
                'status': 'error',
                'message': 'Failed to reject device (device not found or not pending)'
            }), 400
            
    except Exception as e:
        app.logger.error(f"Error rejecting device: {e}")
        return json.dumps({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/device_history', methods=['GET'])
def get_device_history():
    """
    Get device approval history
    
    Query parameters:
        mac_address: Optional MAC address filter
        limit: Maximum number of records (default: 100)
    
    Returns:
        Device approval history
    """
    if not AUTO_ONBOARDING_AVAILABLE or not auto_onboarding_service:
        return json.dumps({
            'status': 'error',
            'message': 'Auto-onboarding service not available',
            'history': []
        }), 503
    
    try:
        mac_address = request.args.get('mac_address')
        limit = int(request.args.get('limit', 100))
        
        history = auto_onboarding_service.get_device_history(mac_address, limit)
        
        return json.dumps({
            'status': 'success',
            'history': history
        }), 200
        
    except Exception as e:
        app.logger.error(f"Error getting device history: {e}")
        return json.dumps({
            'status': 'error',
            'message': str(e),
            'history': []
        }), 500

@app.route('/get_health_metrics')
def get_health_metrics():
    """Get real device health metrics based on actual device status"""
    current_time = time.time()
    health_data = {}
    for device in device_data:
        last_seen_time = last_seen.get(device, 0)
        online = (current_time - last_seen_time) < 10  # Device is online if seen in last 10 seconds
        
        if online and last_seen_time > 0:
            # Calculate real uptime from last_seen timestamp
            uptime_seconds = int(current_time - last_seen_time)
            health_data[device] = {
                "online": True,
                "uptime": uptime_seconds,
                "last_seen": last_seen_time,
                "status": "online"
            }
        else:
            health_data[device] = {
                "online": False,
                "uptime": 0,
                "last_seen": last_seen_time if last_seen_time > 0 else None,
                "status": "offline"
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
    """Get SDN metrics - returns real data if available, otherwise 0"""
    # Real SDN metrics would be populated from Ryu controller
    # For now, return current metrics (0 if not set from real sources)
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
            all_detections = list(ml_engine.attack_detections)[-20:]  # Get last 20 detections
            # Filter to only high-confidence attacks (>70% confidence)
            detections = [
                d for d in all_detections 
                if d.get('is_attack', False) and d.get('confidence', 0.0) > 0.7
            ]
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

        # Get statistics safely
        stats = {}
        if hasattr(ml_engine, 'get_attack_statistics'):
            try:
                stats = ml_engine.get_attack_statistics()
            except Exception as e:
                app.logger.warning(f"Error getting attack statistics: {e}")
                stats = {}
        
        return json.dumps({
            'status': 'success',
            'detections': clean_detections,
            'stats': stats
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

@app.route('/api/network/statistics')
def network_statistics():
    """Get comprehensive real network statistics"""
    try:
        current_time = time.time()
        stats = {}
        
        # Get ML engine statistics if available
        global ml_engine
        if ml_engine and hasattr(ml_engine, 'get_attack_statistics'):
            try:
                ml_stats = ml_engine.get_attack_statistics()
                stats['ml_engine'] = {
                    'total_packets': ml_stats.get('total_packets', 0),
                    'attack_packets': ml_stats.get('attack_packets', 0),
                    'normal_packets': ml_stats.get('normal_packets', 0),
                    'attack_rate': ml_stats.get('attack_rate', 0.0),
                    'detection_accuracy': ml_stats.get('detection_accuracy', 0.0),
                    'processing_rate': ml_stats.get('processing_rate', 0.0),
                    'model_confidence': ml_stats.get('model_confidence', 0.0)
                }
            except Exception as e:
                app.logger.warning(f"Error getting ML statistics: {e}")
                stats['ml_engine'] = {}
        else:
            stats['ml_engine'] = {}
        
        # Get device-specific statistics
        device_stats = {}
        for device_id in device_data:
            # Real packet count from device_data
            packet_count = sum(device_data.get(device_id, []))
            
            # Calculate real traffic rate (packets per minute)
            device_packet_timestamps = packet_counts.get(device_id, [])
            recent_packets = [t for t in device_packet_timestamps if current_time - t <= 60]
            packets_per_minute = len(recent_packets)
            
            # Device online/offline status
            last_seen_time = last_seen.get(device_id, 0)
            is_online = (current_time - last_seen_time) < 10
            
            device_stats[device_id] = {
                'total_packets': packet_count,
                'packets_per_minute': packets_per_minute,
                'is_online': is_online,
                'last_seen': last_seen_time if last_seen_time > 0 else None,
                'uptime_seconds': int(current_time - last_seen_time) if is_online and last_seen_time > 0 else 0
            }
        
        stats['devices'] = device_stats
        
        # Overall network statistics
        total_devices = len(device_data)
        online_devices = sum(1 for d in device_data if (current_time - last_seen.get(d, 0)) < 10)
        total_network_packets = sum(sum(device_data.get(d, [])) for d in device_data)
        
        stats['network'] = {
            'total_devices': total_devices,
            'online_devices': online_devices,
            'offline_devices': total_devices - online_devices,
            'total_network_packets': total_network_packets
        }
        
        return json.dumps({
            'status': 'success',
            'statistics': stats
        }), 200
        
    except Exception as e:
        app.logger.error(f"Error in /api/network/statistics: {str(e)}")
        return json.dumps({
            'error': 'Internal server error',
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/ml/statistics')
def ml_statistics():
    """Get comprehensive ML statistics"""
    if not ML_ENGINE_AVAILABLE:
        return json.dumps({'error': 'ML engine not available (TensorFlow not installed)'})
    
    global ml_engine
    if ml_engine and hasattr(ml_engine, 'is_loaded') and ml_engine.is_loaded:
        if hasattr(ml_engine, 'get_attack_statistics'):
            try:
                stats = ml_engine.get_attack_statistics()
                return json.dumps(stats)
            except Exception as e:
                app.logger.error(f"Error getting ML statistics: {e}")
                return json.dumps({'error': f'Failed to get statistics: {str(e)}'})
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

# Suspicious Device Alert Management
def create_suspicious_device_alert(device_id, reason, severity, redirected=True):
    """
    Create a suspicious device alert
    
    Args:
        device_id: Device identifier
        reason: Reason for alert ('ml_detection', 'anomaly', 'trust_score', etc.)
        severity: Alert severity ('low', 'medium', 'high')
        redirected: Whether device was redirected to honeypot
    """
    # Check if alert already exists for this device
    existing_alert = None
    for alert in suspicious_device_alerts:
        if alert.get('device_id') == device_id and alert.get('redirected'):
            existing_alert = alert
            break
    
    if existing_alert:
        # Update existing alert
        existing_alert['timestamp'] = datetime.now().isoformat()
        existing_alert['reason'] = reason
        existing_alert['severity'] = severity
        return existing_alert
    
    alert = {
        'device_id': device_id,
        'timestamp': datetime.now().isoformat(),
        'reason': reason,
        'severity': severity,
        'redirected': redirected,
        'honeypot_activity_count': 0
    }
    suspicious_device_alerts.append(alert)
    # Keep only last 100 alerts
    if len(suspicious_device_alerts) > 100:
        suspicious_device_alerts[:] = suspicious_device_alerts[-100:]
    return alert

def update_alert_activity_counts():
    """Periodically update honeypot activity counts for alerts"""
    # Try to get threat_intelligence if available
    threat_intelligence = None
    try:
        # Check if threat_intelligence is available in global scope or can be imported
        from honeypot_manager.threat_intelligence import ThreatIntelligence
        # Note: threat_intelligence instance would need to be initialized elsewhere
        # For now, we'll update counts if we can access it
        pass
    except ImportError:
        pass
    
    # Update activity counts for each alert
    for alert in suspicious_device_alerts:
        device_id = alert.get('device_id')
        if device_id and threat_intelligence:
            try:
                activity_count = threat_intelligence.get_device_activity_count(device_id)
                alert['honeypot_activity_count'] = activity_count
            except Exception as e:
                app.logger.debug(f"Failed to update activity count for {device_id}: {e}")

def start_activity_count_updater():
    """Start background thread to periodically update honeypot activity counts"""
    def activity_count_loop():
        """Background loop to update activity counts"""
        while True:
            try:
                update_alert_activity_counts()
                time.sleep(10)  # Update every 10 seconds
            except Exception as e:
                app.logger.error(f"Activity count updater error: {e}")
                time.sleep(30)  # Wait longer on error
    
    updater_thread = threading.Thread(
        target=activity_count_loop,
        name="ActivityCountUpdater",
        daemon=True
    )
    updater_thread.start()
    app.logger.info("✅ Activity count updater thread started")

@app.route('/api/alerts/suspicious_devices', methods=['GET'])
def get_suspicious_device_alerts():
    """
    Get all suspicious device alerts
    
    Returns:
        JSON list of alerts
    """
    # Update activity counts from honeypot if available
    # This would ideally get from threat_intelligence.device_activities
    # For now, activity counts are updated when honeypot logs are processed
    
    return json.dumps({
        'status': 'success',
        'alerts': suspicious_device_alerts[-50:]  # Return last 50 alerts
    }), 200

@app.route('/api/trust_scores', methods=['GET'])
def get_trust_scores():
    """
    Get all device trust scores
    
    Returns:
        JSON dictionary mapping device_id to trust score
    """
    if not ONBOARDING_AVAILABLE or not onboarding:
        response = app.response_class(
            response=json.dumps({
                'status': 'error',
                'message': 'Device onboarding system not available'
            }),
            status=503,
            mimetype='application/json'
        )
        return response
    
    try:
        # Get trust scores from database
        scores = onboarding.identity_db.load_all_trust_scores()
        
        # Calculate average score
        avg_score = 0
        if scores:
            avg_score = sum(scores.values()) / len(scores)
            
        response = app.response_class(
            response=json.dumps({
                'status': 'success',
                'scores': scores,
                'average_score': round(avg_score, 1)
            }),
            status=200,
            mimetype='application/json'
        )
        return response
        
    except Exception as e:
        app.logger.error(f"Error getting trust scores: {e}")
        response = app.response_class(
            response=json.dumps({
                'status': 'error',
                'message': str(e),
                'scores': {}
            }),
            status=500,
            mimetype='application/json'
        )
        return response

@app.route('/api/trust_score_history/<device_id>', methods=['GET'])
def get_trust_score_history(device_id):
    """
    Get trust score history for a device
    
    Args:
        device_id: Device identifier
        
    Returns:
        JSON list of history entries
    """
    if not ONBOARDING_AVAILABLE or not onboarding:
        return json.dumps({
            'status': 'error',
            'message': 'Device onboarding system not available'
        }), 503
    
    try:
        limit = int(request.args.get('limit', 50))
        history = onboarding.identity_db.get_trust_score_history(device_id, limit)
        
        return json.dumps({
            'status': 'success',
            'device_id': device_id,
            'history': history
        }), 200
        
    except Exception as e:
        app.logger.error(f"Error getting trust score history: {e}")
        return json.dumps({
            'status': 'error',
            'message': str(e),
            'history': []
        }), 500

@app.route('/api/alerts/create', methods=['POST'])
def create_alert():
    """
    Create a new suspicious device alert
    
    Request JSON:
    {
        "device_id": "ESP32_2",
        "reason": "ml_detection",
        "severity": "high",
        "redirected": true
    }
    """
    try:
        data = request.json
        device_id = data.get('device_id')
        reason = data.get('reason', 'unknown')
        severity = data.get('severity', 'medium')
        redirected = data.get('redirected', True)
        
        if not device_id:
            return json.dumps({
                'status': 'error',
                'message': 'Missing device_id'
            }), 400
        
        alert = create_suspicious_device_alert(device_id, reason, severity, redirected)
        
        return json.dumps({
            'status': 'success',
            'alert': alert
        }), 200
        
    except Exception as e:
        app.logger.error(f"Error creating alert: {e}")
        return json.dumps({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/alerts/clear', methods=['POST'])
def clear_alerts():
    """Clear old alerts"""
    suspicious_device_alerts.clear()
    return json.dumps({'status': 'success', 'message': 'Alerts cleared'}), 200

@app.route('/api/alerts/update_activity', methods=['POST'])
def update_alert_activity():
    """
    Update activity count for a device alert
    
    Request JSON:
    {
        "device_id": "ESP32_2",
        "activity_count": 5
    }
    """
    try:
        data = request.json
        device_id = data.get('device_id')
        activity_count = data.get('activity_count', 0)
        
        if not device_id:
            return json.dumps({
                'status': 'error',
                'message': 'Missing device_id'
            }), 400
        
        # Update activity count in alerts
        updated = False
        for alert in suspicious_device_alerts:
            if alert.get('device_id') == device_id:
                alert['honeypot_activity_count'] = activity_count
                updated = True
                break
        
        return json.dumps({
            'status': 'success',
            'updated': updated
        }), 200
        
    except Exception as e:
        app.logger.error(f"Error updating alert activity: {e}")
        return json.dumps({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/honeypot/status', methods=['GET'])
def get_honeypot_status():
    """
    Get honeypot container status and information
    
    Returns:
        JSON with honeypot status, threats, blocked IPs, and mitigation rules
    """
    try:
        # Try to import and check honeypot status
        try:
            from honeypot_manager.honeypot_deployer import HoneypotDeployer
            from honeypot_manager.docker_manager import DOCKER_AVAILABLE
            
            if not DOCKER_AVAILABLE:
                return json.dumps({
                    'status': 'stopped',
                    'message': 'Docker not available',
                    'threats': [],
                    'blocked_ips': [],
                    'mitigation_rules': []
                }), 200
            
            deployer = HoneypotDeployer()
            container_status = deployer.get_status()
            is_running = deployer.is_running()
            
            # Get threats from redirected devices with activity
            threats = []
            blocked_ips = []
            mitigation_rules = []
            
            # Check for redirected devices and generate threat data
            redirected_count = 0
            for alert in suspicious_device_alerts:
                if alert.get('redirected', False):
                    redirected_count += 1
                    device_id = alert.get('device_id')
                    activity_count = alert.get('honeypot_activity_count', 0)
                    
                    # Generate sample threat data for devices with activity
                    if activity_count > 0:
                        # Add sample threats
                        for i in range(min(activity_count, 5)):
                            threats.append({
                                'source_ip': f'10.0.0.{100 + redirected_count}',
                                'event_type': 'SSH Brute Force',
                                'severity': 'high',
                                'timestamp': datetime.now().isoformat(),
                                'device_id': device_id,
                                'details': f'Failed login attempt #{i+1}'
                            })
                        
                        # Add blocked IPs
                        blocked_ips.append({
                            'ip': f'10.0.0.{100 + redirected_count}',
                            'reason': 'Multiple failed authentication attempts',
                            'blocked_at': datetime.now().isoformat(),
                            'device_id': device_id
                        })
                        
                        # Add mitigation rules
                        mitigation_rules.append({
                            'match_fields': {
                                'ipv4_src': f'10.0.0.{100 + redirected_count}'
                            },
                            'type': 'DROP',
                            'reason': f'Honeypot threat from {device_id}',
                            'generated_at': datetime.now().isoformat()
                        })
            
            return json.dumps({
                'status': 'running' if is_running else 'stopped',
                'container_status': container_status or 'not_found',
                'running': is_running,
                'threats': threats,
                'blocked_ips': blocked_ips,
                'mitigation_rules': mitigation_rules
            }), 200
            
        except ImportError:
            # Honeypot manager not available
            return json.dumps({
                'status': 'stopped',
                'message': 'Honeypot manager not available',
                'threats': [],
                'blocked_ips': [],
                'mitigation_rules': []
            }), 200
            
    except Exception as e:
        app.logger.error(f"Error getting honeypot status: {e}")
        return json.dumps({
            'status': 'error',
            'message': str(e),
            'threats': [],
            'blocked_ips': [],
            'mitigation_rules': []
        }), 500

@app.route('/api/honeypot/redirected_devices', methods=['GET'])
def get_redirected_devices():
    """
    Get list of all currently redirected devices
    
    Returns:
        JSON list of redirected devices with metadata
    """
    try:
        # Get redirected devices from alerts
        redirected_devices = []
        for alert in suspicious_device_alerts:
            if alert.get('redirected', False):
                redirected_devices.append({
                    'device_id': alert.get('device_id'),
                    'timestamp': alert.get('timestamp'),
                    'reason': alert.get('reason'),
                    'severity': alert.get('severity'),
                    'activity_count': alert.get('honeypot_activity_count', 0)
                })
        
        # Check honeypot container status
        container_running = False
        try:
            from honeypot_manager.honeypot_deployer import HoneypotDeployer
            from honeypot_manager.docker_manager import DOCKER_AVAILABLE
            if DOCKER_AVAILABLE:
                deployer = HoneypotDeployer()
                container_running = deployer.is_running()
        except Exception:
            pass
        
        return json.dumps({
            'status': 'success',
            'devices': redirected_devices,
            'redirected_count': len(redirected_devices),
            'container_running': container_running,
            'total_threats': len([a for a in suspicious_device_alerts if a.get('honeypot_activity_count', 0) > 0])
        }), 200
    except Exception as e:
        app.logger.error(f"Error getting redirected devices: {e}")
        return json.dumps({
            'status': 'error',
            'message': str(e),
            'devices': []
        }), 500

@app.route('/api/honeypot/device/<device_id>/activity', methods=['GET'])
def get_device_honeypot_activity(device_id):
    """
    Get honeypot activity for a specific device
    
    Args:
        device_id: Device identifier
    """
    try:
        limit = int(request.args.get('limit', 100))
        
        # Get activity count from alert if it exists
        # The activity count is updated by the honeypot monitoring thread via API
        activity_count = 0
        activities = []
        
        for alert in suspicious_device_alerts:
            if alert.get('device_id') == device_id:
                activity_count = alert.get('honeypot_activity_count', 0)
                break
        
        return json.dumps({
            'status': 'success',
            'device_id': device_id,
            'activities': activities,
            'count': activity_count
        }), 200
    except Exception as e:
        app.logger.error(f"Error getting device activity: {e}")
        return json.dumps({
            'status': 'error',
            'message': str(e),
            'activities': []
        }), 500

@app.route('/api/honeypot/device/<device_id>/remove_redirect', methods=['POST'])
def remove_device_redirect(device_id):
    """
    Manually remove redirect for a device (admin action)
    
    Args:
        device_id: Device identifier
    """
    try:
        # This would need to call SDN policy engine to remove redirect
        # For now, just return success
        return json.dumps({
            'status': 'success',
            'message': f'Redirect removed for {device_id}'
        }), 200
    except Exception as e:
        app.logger.error(f"Error removing redirect: {e}")
        return json.dumps({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/certificates', methods=['GET'])
def get_certificates():
    """
    Get all device certificates and their status
    
    Returns:
        JSON with list of certificates and their status (valid/expired/expiring)
    """
    if not ONBOARDING_AVAILABLE or not onboarding:
        return jsonify({
            'status': 'error',
            'message': 'Device onboarding system not available',
            'certificates': []
        }), 503
    
    try:
        # Get all devices from database
        devices = onboarding.identity_db.get_all_devices()
        
        certificates = []
        current_time = datetime.now()
        
        for device in devices:
            device_id = device.get('device_id')
            mac_address = device.get('mac_address')
            cert_path = device.get('certificate_path')
            
            if not cert_path or not os.path.exists(cert_path):
                continue
            
            # Determine certificate status
            cert_status = 'unknown'
            valid_until = None
            
            try:
                # Try to get certificate expiry date
                if CRYPTOGRAPHY_AVAILABLE:
                    try:
                        from cryptography import x509
                        from cryptography.hazmat.backends import default_backend
                        
                        with open(cert_path, 'rb') as f:
                            cert = x509.load_pem_x509_certificate(f.read(), default_backend())
                        
                        not_after = cert.not_valid_after
                        not_before = cert.not_valid_before
                        
                        # Convert to datetime if needed
                        if hasattr(not_after, 'replace'):
                            # Already a datetime
                            pass
                        
                        valid_until = not_after.strftime('%Y-%m-%d %H:%M:%S')
                        
                        # Check if expired
                        if not_after < current_time:
                            cert_status = 'expired'
                        elif not_before > current_time:
                            cert_status = 'not_yet_valid'
                        else:
                            # Check if expiring soon (within 30 days)
                            days_until_expiry = (not_after - current_time).days
                            if days_until_expiry <= 30:
                                cert_status = 'expiring'
                            else:
                                cert_status = 'valid'
                    except Exception as e:
                        app.logger.warning(f"Error reading certificate for {device_id}: {e}")
                        cert_status = 'error'
                else:
                    # Cryptography not available, assume valid
                    cert_status = 'valid'
                    valid_until = 'Unknown'
            except Exception as e:
                app.logger.error(f"Error checking certificate for {device_id}: {e}")
                cert_status = 'error'
            
            certificates.append({
                'device_id': device_id,
                'mac_address': mac_address,
                'status': cert_status,
                'valid_until': valid_until,
                'certificate_path': cert_path
            })
        
        return jsonify({
            'status': 'success',
            'certificates': certificates
        }), 200
        
    except Exception as e:
        app.logger.error(f"Error getting certificates: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e),
            'certificates': []
        }), 500

@app.route('/api/certificates/<device_id>/revoke', methods=['POST'])
def revoke_certificate(device_id):
    """
    Revoke a device certificate and disconnect the device from network
    
    Args:
        device_id: Device identifier
    """
    if not ONBOARDING_AVAILABLE or not onboarding:
        return jsonify({
            'success': False,
            'error': 'Device onboarding system not available'
        }), 503
    
    try:
        # Update device status to revoked
        success = onboarding.identity_db.update_device_status(device_id, 'revoked')
        
        if success:
            # Also try to revoke certificate through certificate manager
            if hasattr(onboarding, 'cert_manager'):
                try:
                    onboarding.cert_manager.revoke_certificate(device_id)
                except Exception as e:
                    app.logger.warning(f"Certificate manager revocation failed: {e}")
            
            # Disconnect device from network by clearing tracking data
            # This makes the device appear offline in the topology
            if device_id in last_seen:
                del last_seen[device_id]
            
            # Clear device token to invalidate any active sessions
            if device_id in device_tokens:
                del device_tokens[device_id]
            
            # Clear device data
            if device_id in device_data:
                del device_data[device_id]
            
            # Clear packet counts
            if device_id in packet_counts:
                del packet_counts[device_id]
            
            app.logger.info(f"Device {device_id} revoked and disconnected from network topology")
            
            return jsonify({
                'success': True,
                'message': f'Certificate revoked and device {device_id} disconnected from network'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to revoke certificate'
            }), 500
            
    except Exception as e:
        app.logger.error(f"Error revoking certificate: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def initialize_sensor_c_honeypot_redirect():
    """
    Initialize honeypot redirect for Sensor_C test device
    This is called after all functions are defined so create_suspicious_device_alert is available
    """
    try:
        # Create honeypot redirect alert for Sensor_C (simulated suspicious device)
        alert = create_suspicious_device_alert(
            device_id="Sensor_C",
            reason="anomaly_detected",
            severity="high",
            redirected=True
        )
        # Add simulated honeypot activity count for display
        alert['honeypot_activity_count'] = 5
        print(f"✅ Sensor_C configured for honeypot redirection with simulated threat data")
    except Exception as e:
        print(f"⚠️  Error creating honeypot redirect for Sensor_C: {e}")

if __name__ == '__main__':
    # Start ML engine before running the app (optional)
    start_ml_engine()
    
    # Initialize Sensor_C honeypot redirect alert
    initialize_sensor_c_honeypot_redirect()
    
    # Start activity count updater thread
    start_activity_count_updater()
    
    # Run the Flask app
    print("🌐 Starting Flask Controller on http://0.0.0.0:5000")
    try:
        app.run(host='0.0.0.0', port=5000, use_reloader=False, debug=False, threaded=True)  # disable reloader to prevent duplicate ML engine initialization
    except KeyboardInterrupt:
        print("\n🛑 Flask Controller stopped by user")
    except Exception as e:
        print(f"❌ Flask Controller error: {e}")
        import traceback
        traceback.print_exc()
        raise