# SecureIoT-SDN - Features Guide

## Table of Contents

1. [Token-Based Authentication](#token-based-authentication)
2. [ML-Based DDoS Detection](#ml-based-ddos-detection)
3. [SDN Policy Enforcement](#sdn-policy-enforcement)
4. [Zero Trust Architecture](#zero-trust-architecture)
5. [Honeypot Integration](#honeypot-integration)
6. [Rate Limiting](#rate-limiting)
7. [Real-Time Dashboard](#real-time-dashboard)
8. [Network Topology Visualization](#network-topology-visualization)
9. [Device Onboarding](#device-onboarding)
10. [Trust Scoring System](#trust-scoring-system)
11. [Heuristic Analysis](#heuristic-analysis)
12. [Threat Intelligence](#threat-intelligence)

---

## Token-Based Authentication

### Overview

Token-based authentication provides secure device authentication using dynamically generated, time-limited tokens. Each device must obtain a token before transmitting data.

### How It Works

1. **Token Request**: Device requests token with device_id and MAC address
2. **Authorization Check**: Controller verifies device is authorized
3. **Token Generation**: UUID v4 token generated and stored
4. **Token Validation**: Each data packet validated against stored token
5. **Session Timeout**: Tokens expire after 5 minutes of inactivity

### Usage

#### Device Side (ESP32)

```cpp
// Request token
HTTPClient http;
http.begin("http://192.168.4.1:5000/get_token");
http.addHeader("Content-Type", "application/json");

String payload = "{\"device_id\":\"ESP32_2\",\"mac_address\":\"" + 
                 WiFi.macAddress() + "\"}";
int code = http.POST(payload);

if (code == 200) {
    String response = http.getString();
    // Parse token from JSON response
    token = parseToken(response);
}
http.end();
```

#### Controller Side

**Endpoint**: `POST /get_token`

**Request**:
```json
{
    "device_id": "ESP32_2",
    "mac_address": "AA:BB:CC:DD:EE:FF"
}
```

**Response** (200 OK):
```json
{
    "token": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Response** (403 Forbidden):
```json
{
    "error": "Device not authorized"
}
```

### Configuration

**Session Timeout**: Edit `controller.py`:
```python
SESSION_TIMEOUT = 300  # 5 minutes (in seconds)
```

**Token Format**: UUID v4 (automatically generated)

### Best Practices

1. **Store tokens securely**: Don't log tokens in plain text
2. **Handle token expiration**: Re-request token when expired
3. **Use HTTPS**: In production, use TLS for token transmission
4. **Rotate tokens**: Tokens automatically rotate on timeout

### Troubleshooting

**Problem**: Token request fails
- **Solution**: Verify device is in `authorized_devices` dictionary
- **Solution**: Check MAC address format (AA:BB:CC:DD:EE:FF)

**Problem**: Token expires too quickly
- **Solution**: Increase `SESSION_TIMEOUT` value
- **Solution**: Ensure device sends data regularly to refresh token

---

## ML-Based DDoS Detection

### Overview

Machine learning-based attack detection uses pre-trained TensorFlow models to analyze network traffic and detect DDoS attacks in real-time.

### How It Works

1. **Model Loading**: TensorFlow model loaded from `models/` directory
2. **Feature Extraction**: Packet features extracted (size, protocol, ports, rates)
3. **Prediction**: Model classifies packet as Normal or Attack
4. **Classification**: Attack type determined (DDoS, Botnet, Flood)
5. **Statistics**: Detection statistics tracked and displayed

### Usage

#### Initialize ML Engine

**Endpoint**: `POST /ml/initialize`

**Response**:
```json
{
    "status": "success",
    "message": "ML engine initialized and monitoring started"
}
```

#### Check ML Status

**Endpoint**: `GET /ml/status`

**Response**:
```json
{
    "status": "active",
    "monitoring": true,
    "statistics": {
        "total_packets": 10000,
        "attack_packets": 150,
        "normal_packets": 9850,
        "attack_rate": 1.5,
        "detection_rate": 98.5,
        "model_status": "loaded"
    }
}
```

#### Get Recent Detections

**Endpoint**: `GET /ml/detections`

**Response**:
```json
{
    "status": "success",
    "detections": [
        {
            "timestamp": "2024-01-15T14:30:00",
            "is_attack": true,
            "attack_type": "DDoS Attack",
            "confidence": 0.95,
            "device_id": "ESP32_2",
            "details": "High packet rate detected"
        }
    ],
    "stats": {
        "total_packets": 10000,
        "attack_packets": 150
    }
}
```

#### Analyze Specific Packet

**Endpoint**: `POST /ml/analyze_packet`

**Request**:
```json
{
    "device_id": "ESP32_2",
    "size": 1500,
    "protocol": 6,
    "src_port": 12345,
    "dst_port": 80,
    "rate": 1000.0,
    "duration": 10.0,
    "bps": 1000000.0,
    "pps": 100.0,
    "tcp_flags": 2,
    "window_size": 65535,
    "ttl": 64
}
```

**Response**:
```json
{
    "is_attack": true,
    "attack_type": "DDoS Attack",
    "confidence": 0.92
}
```

### Model Files

**Location**: `models/` directory

**Files**:
- `ddos_model_retrained.keras`: Main DDoS detection model (recommended)
- `ddos_model.keras`: Alternative model
- `robust_cic_ddos2019_model_*.h5`: H5 format models

**Model Training**:
- Dataset: CIC-DDoS2019
- Features: 78 network features
- Architecture: Deep neural network

### Configuration

**Model Path**: Edit `ml_security_engine.py`:
```python
model_path = "models/ddos_model_retrained.keras"
```

**Detection Threshold**: Adjust confidence threshold:
```python
confidence_threshold = 0.8  # 80% confidence required
```

### Features Analyzed

- Packet size (bytes)
- Protocol type (TCP=6, UDP=17, ICMP=1)
- Source and destination ports
- Packet rates (bps, pps)
- TCP flags
- Window size
- TTL value
- Fragment offset
- IP and TCP lengths

### Attack Types Detected

1. **Normal Traffic**: Legitimate network traffic
2. **DDoS Attack**: Distributed denial of service
3. **Botnet Attack**: Botnet command and control
4. **Flood Attack**: Traffic flooding

### Best Practices

1. **Keep models updated**: Retrain with new attack patterns
2. **Monitor false positives**: Adjust thresholds as needed
3. **Combine with heuristics**: Use both ML and rule-based detection
4. **Regular health checks**: Monitor ML engine status

### Troubleshooting

**Problem**: ML engine not loading
- **Solution**: Install TensorFlow: `pip install tensorflow`
- **Solution**: Verify model files exist in `models/` directory
- **Solution**: Check model file format (Keras or H5)

**Problem**: High false positive rate
- **Solution**: Adjust confidence threshold
- **Solution**: Retrain model with more data
- **Solution**: Use heuristic analysis as secondary check

**Problem**: Slow detection
- **Solution**: Use GPU acceleration (if available)
- **Solution**: Reduce feature extraction overhead
- **Solution**: Batch process packets

---

## SDN Policy Enforcement

### Overview

Software-Defined Networking (SDN) policy enforcement provides dynamic network control through OpenFlow rules. Policies can be enabled/disabled in real-time to control traffic flow.

### Available Policies

#### 1. Packet Inspection

**Purpose**: Deep packet inspection and filtering

**How It Works**:
- Inspects packet contents
- Applies filtering rules
- Blocks suspicious packets
- Logs policy violations

**Usage**:
```bash
# Enable packet inspection
curl -X POST http://localhost:5000/toggle_policy/packet_inspection

# Response
{"enabled": true}
```

#### 2. Traffic Shaping

**Purpose**: Bandwidth limiting and Quality of Service (QoS)

**How It Works**:
- Limits bandwidth per device
- Applies QoS rules
- Delays packets when needed
- Prioritizes critical traffic

**Usage**:
```bash
# Enable traffic shaping
curl -X POST http://localhost:5000/toggle_policy/traffic_shaping

# Response
{"enabled": true}
```

#### 3. Dynamic Routing

**Purpose**: Intelligent packet routing

**How It Works**:
- Analyzes network topology
- Selects optimal paths
- Reroutes traffic dynamically
- Load balances across paths

**Usage**:
```bash
# Enable dynamic routing
curl -X POST http://localhost:5000/toggle_policy/dynamic_routing

# Response
{"enabled": true}
```

### Policy Management

#### Get Current Policies

**Endpoint**: `GET /get_policies`

**Response**:
```json
{
    "packet_inspection": false,
    "traffic_shaping": true,
    "dynamic_routing": false
}
```

#### Get Policy Logs

**Endpoint**: `GET /get_policy_logs`

**Response**:
```json
[
    "[14:30:15] Packet Inspection policy enabled",
    "[14:30:20] Blocked packet from ESP32_2 due to packet inspection policy",
    "[14:30:25] Delayed packet from ESP32_3 due to traffic shaping policy",
    "[14:30:30] Rerouted packet from ESP32_4 via dynamic routing policy"
]
```

#### Clear Policy Logs

**Endpoint**: `POST /clear_policy_logs`

**Response**:
```json
{
    "status": "ok"
}
```

### SDN Controller Integration

**Ryu SDN Controller**: OpenFlow 1.3 protocol

**Policy Actions**:
- **ALLOW**: Normal forwarding
- **DENY**: Block traffic
- **REDIRECT**: Send to honeypot
- **QUARANTINE**: Isolate device

**Flow Rule Example**:
```python
# Block device traffic
rule = {
    "match": {
        "eth_src": "AA:BB:CC:DD:EE:FF"
    },
    "action": "DENY",
    "priority": 100
}
```

### SDN Metrics

**Endpoint**: `GET /get_sdn_metrics`

**Response**:
```json
{
    "control_plane_latency": 25,
    "data_plane_throughput": 500,
    "policy_enforcement_rate": 95
}
```

### Best Practices

1. **Start with monitoring**: Enable policies gradually
2. **Test policies**: Verify policies don't break legitimate traffic
3. **Monitor logs**: Review policy logs regularly
4. **Adjust priorities**: Set rule priorities appropriately

### Troubleshooting

**Problem**: Policies not applying
- **Solution**: Verify Ryu controller is running
- **Solution**: Check OpenFlow switch connection
- **Solution**: Review policy logs for errors

**Problem**: Legitimate traffic blocked
- **Solution**: Adjust policy rules
- **Solution**: Whitelist trusted devices
- **Solution**: Lower policy sensitivity

---

## Zero Trust Architecture

### Overview

Zero Trust architecture implements continuous verification and least-privilege access control. No device is trusted by default, and access is granted based on trust scores and policies.

### Components

#### 1. PKI-Based Identity

**Certificate Authority (CA)**:
- Self-signed CA certificate
- Device certificate generation
- Certificate validation
- Certificate revocation

**Usage**:
```python
from identity_manager.certificate_manager import CertificateManager

cm = CertificateManager(certs_dir="certs")
cert_path, key_path = cm.generate_device_certificate(
    device_id="ESP32_2",
    mac_address="AA:BB:CC:DD:EE:FF"
)
```

#### 2. Continuous Attestation

**Purpose**: Periodic device verification

**How It Works**:
- Verifies device certificates every 5 minutes
- Checks certificate validity
- Validates device integrity
- Updates trust scores based on results

**Usage**:
```python
from trust_evaluator.device_attestation import DeviceAttestation

attestation = DeviceAttestation(attestation_interval=300)
result = attestation.perform_attestation(
    device_id="ESP32_2",
    cert_path="certs/ESP32_2.crt",
    cert_manager=cm
)
```

#### 3. Trust Scoring

**Purpose**: Dynamic trust evaluation (0-100 scale)

**Trust Score Factors**:
- Behavioral anomalies: -10 to -30
- Attestation failures: -20
- Security alerts: -5 to -15 (severity-based)
- Time-based decay: -1 per day

**Usage**:
```python
from trust_evaluator.trust_scorer import TrustScorer

scorer = TrustScorer(initial_score=70)
score = scorer.get_trust_score("ESP32_2")
scorer.adjust_trust_score("ESP32_2", -10, "Behavioral anomaly detected")
```

#### 4. Policy Adaptation

**Purpose**: Access control based on trust scores

**Trust Levels**:
- **High (80-100)**: Full access, normal policies
- **Medium (50-79)**: Restricted access, enhanced monitoring
- **Low (20-49)**: Limited access, strict policies
- **Critical (0-19)**: Quarantined, no access

**Usage**:
```python
from trust_evaluator.policy_adapter import PolicyAdapter

adapter = PolicyAdapter(trust_scorer=scorer)
adapter.adapt_policy_for_device("ESP32_2")
```

### Zero Trust Workflow

```
Device Onboarding
    ↓
Certificate Generation
    ↓
Initial Trust Score (70)
    ↓
Behavioral Baseline
    ↓
Continuous Monitoring
    ↓
Trust Score Updates
    ↓
Policy Adaptation
    ↓
Access Control
```

### Best Practices

1. **Start with high trust**: New devices get initial score of 70
2. **Monitor continuously**: Regular attestation and behavioral analysis
3. **Adapt quickly**: Lower trust scores trigger immediate policy changes
4. **Document changes**: Log all trust score adjustments

### Troubleshooting

**Problem**: Trust scores too low
- **Solution**: Check for false positives in detection
- **Solution**: Adjust trust score factors
- **Solution**: Manually increase trust score for trusted devices

**Problem**: Certificates expiring
- **Solution**: Implement certificate renewal
- **Solution**: Extend certificate validity period
- **Solution**: Monitor certificate expiration dates

---

## Honeypot Integration

### Overview

Honeypot integration provides active threat detection by redirecting suspicious traffic to a honeypot (Cowrie) that captures attacker activities.

### How It Works

1. **Deployment**: Cowrie honeypot deployed in Docker container
2. **Redirection**: Suspicious traffic redirected to honeypot
3. **Capture**: Honeypot logs attacker activities
4. **Analysis**: Logs parsed for threat intelligence
5. **Mitigation**: Automatic blocking rules generated

### Deployment

**Usage**:
```python
from honeypot_manager.honeypot_deployer import HoneypotDeployer

deployer = HoneypotDeployer(honeypot_type="cowrie")
success = deployer.deploy()

if success:
    print("Honeypot deployed successfully")
    status = deployer.get_status()
    print(f"Honeypot status: {status}")
```

### Honeypot Configuration

**Ports**:
- SSH: 2222
- HTTP: 8080

**Data Storage**: `honeypot_data/cowrie/`

**Container Name**: `iot_honeypot_cowrie`

### Threat Intelligence

**Usage**:
```python
from honeypot_manager.threat_intelligence import ThreatIntelligence

ti = ThreatIntelligence()
threats = ti.get_blocked_ips()
statistics = ti.get_statistics()
```

### Log Parsing

**Usage**:
```python
from honeypot_manager.log_parser import LogParser

parser = LogParser()
logs = parser.parse_cowrie_logs("honeypot_data/cowrie/log.json")
threats = parser.extract_threats(logs)
```

### Mitigation Generation

**Usage**:
```python
from honeypot_manager.mitigation_generator import MitigationGenerator

generator = MitigationGenerator()
rules = generator.generate_rules_from_threats(threats)
generator.apply_rules(rules)
```

### Best Practices

1. **Isolate honeypot**: Use separate network segment
2. **Monitor logs**: Regularly review honeypot logs
3. **Update signatures**: Keep threat intelligence current
4. **Test regularly**: Verify honeypot is capturing attacks

### Troubleshooting

**Problem**: Honeypot not starting
- **Solution**: Verify Docker is installed and running
- **Solution**: Check port availability (2222, 8080)
- **Solution**: Review Docker logs: `docker logs iot_honeypot_cowrie`

**Problem**: No traffic reaching honeypot
- **Solution**: Verify SDN redirection rules
- **Solution**: Check network connectivity
- **Solution**: Review policy enforcement logs

---

## Rate Limiting

### Overview

Rate limiting prevents DoS attacks by controlling the number of packets each device can send per minute.

### Configuration

**Default Limit**: 60 packets per minute per device

**Window**: 60-second sliding window

**Edit** `controller.py`:
```python
RATE_LIMIT = 60  # packets per minute
```

### How It Works

1. **Packet Counting**: Each packet timestamped and stored
2. **Window Calculation**: Count packets in last 60 seconds
3. **Limit Check**: Compare count to rate limit
4. **Blocking**: Reject packets when limit exceeded

### Usage

**Check Rate Limit Status**:
```bash
GET /get_data
```

**Response**:
```json
{
    "ESP32_2": {
        "packets": 150,
        "rate_limit_status": "45/60",
        "blocked_reason": null
    },
    "ESP32_3": {
        "packets": 200,
        "rate_limit_status": "60/60",
        "blocked_reason": "Rate limit exceeded"
    }
}
```

### Best Practices

1. **Set appropriate limits**: Balance security and functionality
2. **Monitor usage**: Track rate limit status
3. **Adjust per device**: Different limits for different device types
4. **Handle gracefully**: Return clear error messages

### Troubleshooting

**Problem**: Legitimate traffic blocked
- **Solution**: Increase rate limit
- **Solution**: Adjust window size
- **Solution**: Whitelist trusted devices

**Problem**: Attacks not blocked
- **Solution**: Lower rate limit
- **Solution**: Implement burst detection
- **Solution**: Add per-IP limits

---

## Real-Time Dashboard

### Overview

Web-based dashboard provides real-time monitoring and control of the IoT security framework.

### Access

**URL**: `http://localhost:5000`

**Or from network**: `http://<controller-ip>:5000`

### Dashboard Tabs

#### 1. Overview Tab

**Features**:
- Network status summary
- Connected device count
- Total packets processed
- System health metrics
- Network topology visualization

#### 2. Devices Tab

**Features**:
- Device list with status
- Authorization controls (Authorize/Revoke)
- Packet counts per device
- Rate limit status
- Last seen timestamps

#### 3. Security Tab

**Features**:
- SDN policy controls
- Policy status (enabled/disabled)
- Security alerts
- Policy enforcement logs
- Threat intelligence

#### 4. ML Engine Tab

**Features**:
- ML engine status
- Attack detections
- Detection statistics
- Model information
- Confidence scores

#### 5. Analytics Tab

**Features**:
- Network performance metrics
- Device health metrics
- Traffic statistics
- Control plane metrics
- Data plane throughput

### Real-Time Updates

**Update Interval**: 5 seconds (automatic refresh)

**AJAX Endpoints**:
- `/get_data`: Device data
- `/get_topology_with_mac`: Network topology
- `/get_health_metrics`: Health metrics
- `/get_policy_logs`: Policy logs
- `/ml/detections`: ML detections

### Best Practices

1. **Monitor regularly**: Check dashboard for anomalies
2. **Review alerts**: Address security alerts promptly
3. **Track metrics**: Monitor performance over time
4. **Use filters**: Filter devices and alerts as needed

---

## Network Topology Visualization

### Overview

Interactive network topology graph shows device connections and network structure in real-time.

### Features

- **Interactive Graph**: Click and drag nodes
- **Real-Time Updates**: Automatic refresh every 5 seconds
- **MAC Address Display**: Shows device MAC addresses
- **Connection Status**: Visual indication of online/offline
- **Packet Counts**: Display packets per device
- **Gateway-Centric**: Gateway as central node

### Usage

**Endpoint**: `GET /get_topology_with_mac`

**Response**:
```json
{
    "nodes": [
        {
            "id": "ESP32_Gateway",
            "label": "Gateway",
            "mac": "A0:B1:C2:D3:E4:F5",
            "online": true,
            "last_seen": 1234567890.0,
            "packets": 0
        },
        {
            "id": "ESP32_2",
            "label": "ESP32_2",
            "mac": "AA:BB:CC:DD:EE:22",
            "online": true,
            "last_seen": 1234567890.0,
            "packets": 150
        }
    ],
    "edges": [
        {
            "from": "ESP32_2",
            "to": "ESP32_Gateway"
        }
    ]
}
```

### Visualization Library

**Library**: vis-network.js

**Features**:
- Force-directed layout
- Node styling
- Edge styling
- Interactive controls

---

## Device Onboarding

### Overview

Secure device onboarding process with certificate provisioning and behavioral baseline establishment.

### Onboarding Workflow

1. **Device Registration**: Device ID and MAC address
2. **Certificate Generation**: X.509 certificate created
3. **Database Entry**: Device added to identity database
4. **Behavioral Profiling**: Baseline established (5 minutes)
5. **Policy Generation**: Least-privilege policy created
6. **Trust Initialization**: Initial trust score (70)

### Usage

```python
from identity_manager.device_onboarding import DeviceOnboarding

onboarding = DeviceOnboarding(
    certs_dir="certs",
    db_path="identity.db"
)

result = onboarding.onboard_device(
    device_id="ESP32_2",
    mac_address="AA:BB:CC:DD:EE:FF",
    device_type="sensor",
    device_info="Temperature sensor"
)

if result['status'] == 'success':
    print(f"Device onboarded: {result['device_id']}")
    print(f"Certificate: {result['certificate_path']}")
```

### Behavioral Profiling

**Duration**: 5 minutes (configurable)

**Metrics Collected**:
- Average packet size
- Average packet rate
- Common destination ports
- Traffic patterns
- Protocol distribution

**Usage**:
```python
from identity_manager.behavioral_profiler import BehavioralProfiler

profiler = BehavioralProfiler(profiling_duration=300)
baseline = profiler.establish_baseline("ESP32_2")
```

### Policy Generation

**Usage**:
```python
from identity_manager.policy_generator import PolicyGenerator

generator = PolicyGenerator()
policy = generator.generate_policy(
    device_id="ESP32_2",
    baseline=baseline
)
```

---

## Trust Scoring System

### Overview

Dynamic trust scoring system evaluates device trustworthiness based on multiple factors and adjusts access control accordingly.

### Trust Score Calculation

**Initial Score**: 70 (for new devices)

**Adjustments**:
- Behavioral Anomaly: -10 to -30 points
- Attestation Failure: -20 points
- Security Alert (Low): -5 points
- Security Alert (Medium): -10 points
- Security Alert (High): -15 points
- Time Decay: -1 point per day of inactivity

**Final Score**: Clamped to 0-100 range

### Usage

```python
from trust_evaluator.trust_scorer import TrustScorer

scorer = TrustScorer(initial_score=70)

# Initialize device
scorer.initialize_device("ESP32_2")

# Get current score
score = scorer.get_trust_score("ESP32_2")

# Adjust score
scorer.adjust_trust_score("ESP32_2", -10, "Behavioral anomaly")

# Record security alert
scorer.record_security_alert("ESP32_2", "DoS", "high")

# Get all scores
all_scores = scorer.get_all_scores()
```

### Trust Levels

- **High (80-100)**: Full access, normal policies
- **Medium (50-79)**: Restricted access, enhanced monitoring
- **Low (20-49)**: Limited access, strict policies
- **Critical (0-19)**: Quarantined, no access

---

## Heuristic Analysis

### Overview

Heuristic-based anomaly detection uses rule-based analysis to identify suspicious network behavior.

### Detection Rules

#### 1. DoS Detection

**Rule**: Packet rate > 1000 packets per second

**Severity**: High

**Usage**:
```python
from heuristic_analyst.anomaly_detector import AnomalyDetector

detector = AnomalyDetector()
alert = detector.detect_dos(packet_rate=1500)
```

#### 2. Port Scanning Detection

**Rule**: > 50 unique destination ports in 1 minute

**Severity**: Medium

**Usage**:
```python
alert = detector.detect_scanning(unique_ports=75)
```

#### 3. Volume Attack Detection

**Rule**: > 10 MB data transfer in 1 minute

**Severity**: High

**Usage**:
```python
alert = detector.detect_volume_attack(data_transfer=15*1024*1024)
```

### Flow Analysis

**Usage**:
```python
from heuristic_analyst.flow_analyzer import FlowAnalyzer

analyzer = FlowAnalyzer(ryu_controller_url="http://localhost:8080")
flows = analyzer.get_flow_statistics()
device_stats = analyzer.aggregate_by_device(flows)
```

### Baseline Comparison

**Usage**:
```python
from heuristic_analyst.baseline_manager import BaselineManager

manager = BaselineManager()
baseline = manager.get_baseline("ESP32_2")
anomaly = manager.compare_to_baseline("ESP32_2", current_stats)
```

---

## Threat Intelligence

### Overview

Threat intelligence extraction from honeypot logs and automatic mitigation rule generation.

### Threat Extraction

**Usage**:
```python
from honeypot_manager.threat_intelligence import ThreatIntelligence

ti = ThreatIntelligence()
threats = ti.process_logs(honeypot_logs)
blocked_ips = ti.get_blocked_ips()
statistics = ti.get_statistics()
```

### Mitigation Rules

**Usage**:
```python
from honeypot_manager.mitigation_generator import MitigationGenerator

generator = MitigationGenerator()
rules = generator.generate_rules_from_threats(threats)
generator.apply_rules(rules)
```

### Best Practices

1. **Regular updates**: Update threat intelligence regularly
2. **Verify threats**: Confirm threats before blocking
3. **Whitelist trusted**: Don't block legitimate IPs
4. **Monitor effectiveness**: Track mitigation success

---

**Last Updated**: 2024-01-15
**Version**: 1.0.0

