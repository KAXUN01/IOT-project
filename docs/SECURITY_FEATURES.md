# Security Features Guide

> **Comprehensive reference for all security mechanisms: Zero Trust, dynamic trust scoring, heuristic-deception loop, and threat detection**

## Table of Contents

1. [Zero Trust Architecture](#zero-trust-architecture)
2. [Dynamic Trust Scoring](#dynamic-trust-scoring)
3. [Threat Detection Systems](#threat-detection-systems)
4. [Heuristic-Deception Feedback Loop](#heuristic-deception-feedback-loop)
5. [Honeypot Integration](#honeypot-integration)
6. [Traffic Orchestration](#traffic-orchestration)
7. [Configuration](#configuration)

---

## Zero Trust Architecture

### Principles

The framework implements **Zero Trust Architecture** based on NIST SP 800-207:

1. **Never Trust, Always Verify**: No device is trusted by default
2. **Least Privilege**: Minimal access required for operation
3. **Continuous Verification**: Ongoing assessment of device trustworthiness
4. **Assume Breach**: Design assumes network is already compromised

### Implementation

**PKI-Based Identity**:
- Self-signed Certificate Authority (CA)
- X.509 device certificates with 365-day validity
- Public/private key pairs (RSA 2048-bit)
- Physical identity binding (MAC address + fingerprint)

**Continuous Attestation**:
- Periodic device integrity checks (every 5 minutes)
- Certificate validity verification
- Heartbeat monitoring (device liveness)
- Automatic trust score adjustments on failures

**Policy Adaptation**:
- Trust-based access control
- Dynamic policy enforcement via SDN
- Threshold-triggered actions
- Automatic quarantine of compromised devices

---

## Dynamic Trust Scoring

### Overview

Every device in the network is assigned a **dynamic trust score** (0-100) that continuously adjusts based on behavior, integrity checks, and security events.

### Trust Score Calculation

**Initial Score**: 70 (Monitored/Trusted state)

**Scoring Factors**:

| Event Category | Specific Event | Score Adjustment | Trigger |
|---------------|----------------|------------------|---------|
| **Integrity** | Attestation Failure | **-20** | Certificate invalid or heartbeat missing |
| **Security** | High Severity Alert | **-40** | Critical threat detected (e.g., malware) |
| **Security** | Medium Severity Alert | **-20** | Suspicious activity (e.g., port scanning) |
| **Security** | Low Severity Alert | **-10** | Minor anomaly |
| **Behavior** | Anomaly (High) | **-30** | Major deviation from ML baseline |
| **Behavior** | Anomaly (Medium) | **-15** | Moderate deviation |
| **Behavior** | Anomaly (Low) | **-5** | Slight deviation |
| **Positive** | Good Behavior | **+2** | Gradual recovery over time |

### Trust Levels & Thresholds

| Score Range | Level | Policy Action | Description |
|-------------|-------|---------------|-------------|
| **70-100** | **Trusted** | ALLOW | Full network access permitted |
| **50-69** | **Monitored** | REDIRECT | Traffic redirected to inspection/honeypot |
| **30-49** | **Suspicious** | DENY | Access to sensitive resources blocked |
| **0-29** | **Untrusted** | QUARANTINE | Device isolated from network |

### Continuous Attestation

**Purpose**: Verify device integrity and liveness

**Workflow**:
```
Every 5 minutes:
  1. Check certificate validity
  2. Verify device heartbeat (sent within last 10 min)
  3. Validate against CA
  ↓
If ANY check fails:
  ├─ Record attestation failure
  ├─ Lower trust score by 20 points
  ├─ Trigger policy re-evaluation
  └─ Log event for audit
```

**Implementation** (`trust_evaluator/device_attestation.py`):
```python
def perform_attestation(device_id, cert_path, cert_manager):
    """
    Performs comprehensive device attestation
    Returns: {'passed': bool, 'checks': {...}}
    """
    checks = {
        'certificate_valid': verify_certificate(cert_path),
        'heartbeat_present': check_heartbeat(device_id),
        'ca_validation': validate_against_ca(cert_path)
    }
    
    passed = all(checks.values())
    
    if not passed:
        trust_scorer.record_attestation_failure(device_id)
    
    return {'passed': passed, 'checks': checks}
```

### Policy Adaptation

**Automatic Adaptation**:
Trust score changes trigger immediate policy updates via callback mechanism.

**Callback Flow**:
```
Trust Score Changes
    ↓
Callbacks Fired
    ↓
Policy Adapter Notified
    ↓
Trust Threshold Evaluated
    ↓
New Policy Determined (ALLOW/REDIRECT/DENY/QUARANTINE)
    ↓
SDN Policy Engine Updated
    ↓
OpenFlow Rules Installed
    ↓
Network Access Controlled
```

**Implementation** (`trust_evaluator/policy_adapter.py`):
```python
def adapt_policy_for_device(device_id):
    score = trust_scorer.get_trust_score(device_id)
    
    if score >= 70:
        action = 'allow'
    elif score >= 50:
        action = 'redirect'  # Monitor via honeypot
    elif score >= 30:
        action = 'deny'
    else:
        action = 'quarantine'
    
    sdn_policy_engine.apply_policy(device_id, action)
```

### Trust Score Persistence

**Storage**: SQLite database (`identity.db`)

**Schema**:
```sql
-- Current trust scores
ALTER TABLE devices ADD COLUMN trust_score INTEGER DEFAULT 70;

-- Trust score history
CREATE TABLE trust_score_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT NOT NULL,
    trust_score INTEGER NOT NULL,
    reason TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Benefits**:
- Trust scores survive system restarts
- Complete audit trail
- Historical analysis capabilities
- Persistence across reboots

### End-to-End Example

**Scenario**: IoT sensor (Score: 75) gets infected and starts port scanning

```
1. Heuristic Analyst detects abnormal traffic (port scanning)
   ↓
2. Triggers alert: record_security_alert(device_id, 'Port Scan', 'high')
   ↓
3. Trust Scorer receives alert
   ↓
4. Score Calculation: 75 - 40 = 35
   ↓
5. Score updated in database
   ↓
6. Callbacks fired
   ↓
7. Policy Adapter sees score < 50
   ↓
8. Determines action: DENY
   ↓
9. SDN Policy Engine applies DENY policy
   ↓
10. OpenFlow drop rules installed for device MAC
    ↓
11. Device cut off from network instantly
```

---

## Threat Detection Systems

### 1. ML-Based DDoS Detection

**Purpose**: Real-time attack detection using machine learning

**Models**:
- Location: `models/ddos_model_retrained.keras`
- Framework: TensorFlow 2.14+
- Training Dataset: CIC-DDoS2019
- Architecture: Deep neural network (78 features)

**Features Analyzed**:
- Packet size, protocol type
- Source/destination ports
- Packet rates (bps, pps)
- TCP flags, window size, TTL
- Fragment offset, IP headers

**Attack Types Detected**:
1. **Normal Traffic**: Legitimate network traffic
2. **DDoS Attack**: Distributed denial of service
3. **Botnet Attack**: Botnet command and control
4. **Flood Attack**: Traffic flooding

**Confidence Scoring**:
- Threshold: 0.8 (80% confidence required)
- Real-time classification
- Statistics tracking

**API**:
```python
result = ml_engine.predict_attack(packet_features)
# Returns: {'is_attack': True, 'attack_type': 'DDoS', 'confidence': 0.95}
```

---

### 2. Heuristic Anomaly Detection

**Purpose**: Lightweight real-time detection using baseline comparison

**Detection Rules**:

**DoS Attack**:
```python
if current_pps > baseline_pps * 10:
    severity = 'high'
    anomaly_type = 'dos'
elif current_pps > baseline_pps * 5:
    severity = 'high'
    anomaly_type = 'dos'
elif current_pps > baseline_pps * 2:
    severity = 'medium'
    anomaly_type = 'dos'
```

**Volume Attack**:
```python
if current_bps > baseline_bps * 10:
    severity = 'high'
    anomaly_type = 'volume_attack'
```

**Network Scanning**:
```python
if unique_destinations > baseline_destinations * 5 and unique_destinations > 20:
    severity = 'medium'
    anomaly_type = 'scanning'
```

**Port Scanning**:
```python
if unique_ports > baseline_ports * 3 and unique_ports > 10:
    severity = 'medium'
    anomaly_type = 'port_scanning'
```

**Severity Scoring**:
- **High (70+)**: Immediate action required
- **Medium (40-69)**: Monitor and redirect
- **Low (20-39)**: Log and observe
- **None (<20)**: Normal traffic

---

### 3. Baseline Management

**Purpose**: Establish normal behavior patterns for anomaly detection

**Baseline Metrics**:
- Average packets per second
- Average bytes per second
- Common destinations (top 10 IPs)
- Common ports (top 10)
- Traffic patterns and fingerprints

**Baseline Establishment**:
1. Created during device onboarding (5-minute profiling)
2. Updated adaptively using exponential moving average
3. Stored in `behavioral_baselines` table

**Adaptive Updates**:
```python
# Exponential Moving Average (EMA)
alpha = 0.1  # Weight for new observations
new_baseline = alpha * current_value + (1 - alpha) * old_baseline
```

---

## Heuristic-Deception Feedback Loop

### Key Innovation

**Tight integration** of lightweight anomaly detection with active deception environment. The heuristic analysis acts as a tripwire that triggers the honeypot to capture high-fidelity threat intelligence, which generates confirmed mitigation rules.

### Complete System Flow

```
1. Flow Statistics Polling (every 10 seconds)
   - FlowAnalyzerManager polls all SDN switches
   - Collects packet counts, byte counts, destinations, ports
   - Aggregates statistics across switches per device
   ↓
2. Baseline Comparison (real-time)
   - Gets behavioral baseline for each device
   - Compares current stats against baseline
   - Calculates deviation ratios
   ↓
3. Anomaly Detection (real-time)
   - Detects DoS, scanning, volume attacks
   - Assigns severity levels (high/medium/low)
   - Generates anomaly alerts
   ↓
4. Alert Handling (immediate)
   - Alert sent to Policy Engine via handle_analyst_alert()
   - Trust score reduced based on severity
   - Policy orchestration triggered
   ↓
5. Traffic Redirection (immediate)
   - OpenFlow rules installed dynamically
   - Traffic from suspicious device redirected to honeypot
   - Device unaware of redirection (transparent)
   ↓
6. Honeypot Capture (ongoing)
   - Attacker interacts with honeypot (Cowrie)
   - All interactions logged in JSON format
   - High-fidelity intelligence captured
   ↓
7. Log Parsing (every 10 seconds)
   - Honeypot logs monitored continuously
   - Threat intelligence extracted
   - IPs, commands, patterns identified
   ↓
8. Threat Analysis (real-time)
   - Severity assessment
   - Malicious behavior detection
   - Threat classification
   ↓
9. Mitigation Rule Generation (real-time)
   - DENY rules for high severity (block attacker IP)
   - REDIRECT rules for medium severity (continue monitoring)
   - MONITOR rules for low severity (log only)
   ↓
10. Rule Application (immediate)
    - Rules applied to SDN Policy Engine
    - OpenFlow rules installed on switches
    - Permanent mitigation active
    ↓
11. Threat Blocked (ongoing)
    - Future traffic from attacker blocked
    - System protected from confirmed threats
    - Adaptive defense improved
```

### Flow Statistics Polling

**Implementation**: `FlowAnalyzerManager` in `zero_trust_integration.py`

**Features**:
- Polls every 10 seconds (configurable)
- Multi-switch support via FlowAnalyzer instances
- Automatic switch detection
- Device ID mapping via Identity module
- Aggregation across switches

**Statistics Collected**:
```python
{
    'device_id': 'ESP32_2',
    'packet_count': 1500,
    'byte_count': 153600,
    'packets_per_second': 25.0,
    'bytes_per_second': 2560.0,
    'unique_destinations': 3,
    'unique_ports': [80, 443],
    'duration': 60.0
}
```

---

### Traffic Redirection

**Implementation**: `SDNPolicyEngine.handle_analyst_alert()`

**OpenFlow Rule Installation**:
```python
# Redirect suspicious device to honeypot
match = {
    'eth_src': device_mac_address  # Suspicious device
}
action = OUTPUT(port=3)  # Honeypot port (configurable)
priority = 150  # Higher than normal rules
```

**Characteristics**:
- Transparent to device
- High-priority rules (150)
- Immediate enforcement
- Automatic removal on threat clearance

---

## Honeypot Integration

### Deployment

**Honeypot Type**: Cowrie (SSH/Telnet honeypot)

**Container**: Docker-based lightweight deployment

**Configuration**:
```python
honeypot_config = {
    'type': 'cowrie',
    'ssh_port': 2222,
    'http_port': 8080,
    'data_dir': 'honeypot_data/cowrie',
    'log_format': 'json'
}
```

**Deployment** (`honeypot_manager/honeypot_deployer.py`):
```python
deployer = HoneypotDeployer(honeypot_type='cowrie')
deployer.deploy()  # Creates and starts Docker container
status = deployer.get_status()  # Check running status
```

---

### Threat Intelligence Extraction

**Log Parsing** (`honeypot_manager/log_parser.py`):
```python
parser = HoneypotLogParser(honeypot_type='cowrie')
threats = parser.parse_logs(log_content)

# Extract specific intelligence
ips = parser.extract_ips()
commands = parser.extract_commands()
patterns = parser.extract_attack_patterns()
```

**Intelligence Extracted**:
1. **Attacker IPs**: Source IP addresses
2. **Commands Used**: Commands executed by attackers
3. **Event Types**: Login attempts, file downloads, command execution
4. **Timestamps**: When attacks occurred
5. **Credentials**: Usernames/passwords attempted

**Threat Severity Assessment**:
```python
# High Severity
if event_type in ['login_success', 'file_download', 'malware_execution']:
    severity = 'high'

# Medium Severity
if event_type in ['command_execution', 'multiple_login_attempts']:
    severity = 'medium'

# Low Severity
if event_type in ['login_attempt', 'port_probe']:
    severity = 'low'
```

---

### Mitigation Rule Generation

**Implementation**: `MitigationGenerator` in `honeypot_manager/`

**Rule Types**:

**DENY Rule** (High Severity):
```python
rule = {
    'type': 'deny',
    'match_fields': {'ipv4_src': attacker_ip},
    'priority': 200,  # Highest priority
    'reason': 'High severity threats detected',
    'permanent': True
}
```

**REDIRECT Rule** (Medium Severity):
```python
rule = {
    'type': 'redirect',
    'match_fields': {'ipv4_src': attacker_ip},
    'priority': 150,
    'reason': 'Multiple threats detected, continue monitoring'
}
```

**MONITOR Rule** (Low Severity):
```python
rule = {
    'type': 'monitor',
    'match_fields': {'ipv4_src': attacker_ip},
    'priority': 100,
    'reason': 'Threats detected, log all activity'
}
```

**Automatic Application**:
- Rules applied to SDN Policy Engine automatically
- OpenFlow rules installed on all switches
- Permanent until manually removed
- Logged for audit trail

---

## Traffic Orchestration

### Purpose

**Single intelligent orchestration engine** that makes policy decisions based on multiple real-time factors simultaneously.

### Decision Factors

1. **Device Identity**:
   - Authentication status
   - Certificate validity
   - Onboarding status

2. **Trust Scores**:
   - Current score (0-100)
   - Score history and trends
   - Recent score changes

3. **Threat Intelligence**:
   - Active threats from Analyst module
   - Honeypot-captured threats
   - Recent security alerts

4. **Threat Level**:
   - None, Low, Medium, High, Critical
   - Based on alert severity and frequency

### Decision Logic

**Implementation** (`ryu_controller/traffic_orchestrator.py`):
```python
def orchestrate_policy(device_id, threat_intelligence):
    # Gather all factors
    device_info = identity_module.get_device_info(device_id)
    trust_score = trust_evaluator.get_trust_score(device_id)
    recent_alerts = analyst.get_recent_alerts(device_id)
    threat_level = assess_threat_level(threat_intelligence, recent_alerts)
    
    # Make intelligent decision
    if threat_level == 'critical':
        return 'QUARANTINE'
    elif threat_level == 'high' or trust_score < 30:
        return 'QUARANTINE'
    elif threat_level == 'medium' or trust_score < 50:
        return 'DENY'
    elif trust_score < 70:
        return 'REDIRECT'
    else:
        return 'ALLOW'
```

### Policy Actions

| Action | Condition | Effect |
|--------|-----------|--------|
| **ALLOW** | Trust ≥ 70, no threats | Normal forwarding |
| **REDIRECT** | Trust 50-69 or low threats | Send to honeypot |
| **DENY** | Trust 30-49 or medium threats | Block traffic |
| **QUARANTINE** | Trust < 30 or critical threats | Isolate device |

### Audit Trail

Every policy decision is logged:
```python
decision_log = {
    'timestamp': datetime.now(),
    'device_id': device_id,
    'trust_score': trust_score,
    'threat_level': threat_level,
    'decision': decision,
    'reason': reason
}
```

---

## Configuration

### Trust Scoring Configuration

Edit `zero_trust_integration.py`:
```python
config = {
    'initial_trust_score': 70,      # Starting score for new devices
    'attestation_interval': 300      # Seconds between integrity checks
}
```

### Flow Polling Configuration

Edit `zero_trust_integration.py`:
```python
config = {
    'flow_polling_interval': 10,    # Seconds between flow stat polls
    'anomaly_window': 60             # Time window for anomaly detection
}
```

### Anomaly Detection Thresholds

Edit `heuristic_analyst/anomaly_detector.py`:
```python
# DoS Detection
DOS_THRESHOLD_HIGH = 10.0      # 10x baseline = high severity
DOS_THRESHOLD_MEDIUM = 5.0     # 5x baseline = medium severity
DOS_THRESHOLD_LOW = 2.0        # 2x baseline = low severity

# Scanning Detection
SCAN_DEST_THRESHOLD = 5.0      # 5x baseline destinations
SCAN_PORT_THRESHOLD = 3.0      # 3x baseline ports
SCAN_MIN_DEST = 20             # Minimum unique destinations
SCAN_MIN_PORT = 10             # Minimum unique ports
```

### Honeypot Configuration

Edit `honeypot_manager/honeypot_deployer.py`:
```python
honeypot_config = {
    'type': 'cowrie',
    'ssh_port': 2222,
    'http_port': 8080,
    'data_dir': 'honeypot_data/cowrie'
}
```

---

## Best Practices

1. **Trust Score Monitoring**: Review trust score trends regularly
2. **Baseline Tuning**: Adjust thresholds based on network characteristics
3. **Honeypot Isolation**: Deploy honeypots on isolated network segments
4. **Log Rotation**: Rotate honeypot logs to prevent storage issues
5. **False Positive Review**: Monitor and adjust detection rules to minimize false positives
6. **Attestation Interval**: Balance security (shorter) vs. overhead (longer)
7. **Threat Intelligence Sharing**: Consider sharing IOCs with external systems

---

**Last Updated**: 2026-01-02  
**Version**: 2.0
