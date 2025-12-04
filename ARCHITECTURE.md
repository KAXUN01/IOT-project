# SecureIoT-SDN - Architecture Documentation

## Table of Contents

1. [System Architecture Overview](#system-architecture-overview)
2. [Layered Architecture](#layered-architecture)
3. [Component Architecture](#component-architecture)
4. [Data Flow Architecture](#data-flow-architecture)
5. [Security Architecture](#security-architecture)
6. [Network Architecture](#network-architecture)
7. [Deployment Architecture](#deployment-architecture)

---

## System Architecture Overview

### Architecture Principles

The SecureIoT-SDN framework is built on the following architectural principles:

1. **Zero Trust Security**: Never trust, always verify
2. **Software-Defined Networking**: Centralized network control
3. **Microservices Design**: Modular, independent components
4. **Event-Driven Architecture**: Asynchronous processing
5. **Defense in Depth**: Multiple security layers

### High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Management Layer                        │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Web Dashboard (Flask)                      │  │
│  │  • Real-time monitoring                                  │  │
│  │  • Device management                                      │  │
│  │  • Policy configuration                                  │  │
│  │  • Security alerts                                       │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              ↕ HTTP/REST
┌─────────────────────────────────────────────────────────────────┐
│                      Control Plane Layer                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   Flask      │  │   Ryu SDN    │  │   ML Security │         │
│  │  Controller  │  │  Controller  │  │    Engine    │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│         ↕                ↕                    ↕                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   Identity   │  │    Trust     │  │   Heuristic  │         │
│  │   Manager    │  │  Evaluator   │  │   Analyst    │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│         ↕                ↕                    ↕                 │
│  ┌──────────────┐  ┌──────────────┐                            │
│  │   Honeypot   │  │    Policy    │                            │
│  │   Manager    │  │   Adapter    │                            │
│  └──────────────┘  └──────────────┘                            │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │         Zero Trust Integration Framework                 │  │
│  │         (Orchestrates all components)                   │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              ↕ OpenFlow/HTTP
┌─────────────────────────────────────────────────────────────────┐
│                        Data Plane Layer                         │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              SDN Switch (OpenFlow)                       │  │
│  │  • Flow table management                                 │  │
│  │  • Packet forwarding                                     │  │
│  │  • Policy enforcement                                    │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              ↕ WiFi/Ethernet
┌─────────────────────────────────────────────────────────────────┐
│                        Gateway Layer                            │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │         ESP32 Gateway (Dual Mode: AP + STA)              │  │
│  │  • WiFi Access Point for nodes                           │  │
│  │  • Station mode to controller                            │  │
│  │  • Data forwarding                                       │  │
│  │  • Protocol translation                                  │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              ↕ WiFi
┌─────────────────────────────────────────────────────────────────┐
│                       IoT Device Layer                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │ ESP32    │  │ ESP32    │  │ ESP32    │  │ ESP32    │      │
│  │ Node 1   │  │ Node 2   │  │ Node 3   │  │ Node N   │      │
│  │          │  │          │  │          │  │          │      │
│  │ Sensors: │  │ Sensors: │  │ Sensors: │  │ Sensors: │      │
│  │ • Temp   │  │ • Motion │  │ • Light │  │ • Custom │      │
│  │ • Humid  │  │ • PIR    │  │ • DHT22 │  │          │      │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Layered Architecture

### Layer 1: IoT Device Layer

**Purpose**: Physical IoT devices that collect and transmit data

**Components**:
- ESP32 microcontrollers
- Various sensors (temperature, motion, light, etc.)
- Firmware: `esp32/node.ino`

**Responsibilities**:
- Sensor data collection
- WiFi connectivity
- Token-based authentication
- Periodic data transmission (every 5 seconds)
- MAC address identification

**Protocols**:
- WiFi 802.11 (b/g/n)
- HTTP/JSON for data transmission
- TCP/IP stack

**Characteristics**:
- Low power consumption
- Limited processing capability
- Battery or USB powered
- Range: ~100 meters (indoor)

### Layer 2: Gateway Layer

**Purpose**: Bridge between IoT devices and controller

**Components**:
- ESP32 Gateway device
- Firmware: `esp32/gateway.ino`

**Responsibilities**:
- WiFi Access Point (AP) for nodes
- Station (STA) mode to connect to controller network
- Data forwarding between nodes and controller
- Protocol translation
- Network isolation

**Network Configuration**:
- AP Mode:
  - SSID: "ESP32-AP"
  - IP: 192.168.4.1 (fixed)
  - Subnet: 192.168.4.0/24
- STA Mode:
  - Connects to existing WiFi
  - Gets IP via DHCP
  - Forwards to controller

**Dual Mode Operation**:
```cpp
WiFi.mode(WIFI_AP_STA);  // Both modes simultaneously
WiFi.softAP(ap_ssid, ap_password);  // Start AP
WiFi.begin(sta_ssid, sta_password);  // Connect to WiFi
```

### Layer 3: Data Plane Layer (SDN Switch)

**Purpose**: Software-defined network switching and forwarding

**Components**:
- OpenFlow-compatible switch
- Flow tables
- Packet forwarding engine

**Responsibilities**:
- Packet forwarding based on flow rules
- Policy enforcement (allow/deny/redirect/quarantine)
- Traffic redirection to honeypot
- Flow statistics collection

**OpenFlow Protocol**:
- Version: 1.3
- Controller connection: TCP port 6653
- Flow table operations:
  - Install rules
  - Delete rules
  - Modify rules
  - Query statistics

**Flow Rule Structure**:
```
Match Fields:
  - Source MAC
  - Destination MAC
  - Source IP
  - Destination IP
  - Source Port
  - Destination Port
  - Protocol

Actions:
  - OUTPUT: Forward to port
  - DROP: Discard packet
  - REDIRECT: Send to honeypot
  - QUARANTINE: Isolate device
```

### Layer 4: Control Plane Layer

**Purpose**: Centralized network control and security management

#### 4.1 Flask Controller

**File**: `controller.py`

**Responsibilities**:
- Web server (Flask)
- REST API endpoints
- Token generation and validation
- Device authorization management
- Rate limiting enforcement
- Session timeout management
- Dashboard serving

**Key Modules**:
- Token management
- Device authorization
- Rate limiting
- SDN policy coordination
- ML engine integration

#### 4.2 Ryu SDN Controller

**File**: `ryu_controller/sdn_policy_engine.py`

**Responsibilities**:
- OpenFlow protocol handling
- Switch connection management
- Flow rule generation and installation
- Policy enforcement
- Traffic redirection

**Key Components**:
- `SDNPolicyEngine`: Main Ryu application
- `OpenFlowRuleGenerator`: Rule generation
- `TrafficRedirector`: Honeypot redirection

**Policy Types**:
- **ALLOW**: Normal forwarding
- **DENY**: Block traffic
- **REDIRECT**: Send to honeypot
- **QUARANTINE**: Isolate device

#### 4.3 ML Security Engine

**File**: `ml_security_engine.py`

**Responsibilities**:
- Load TensorFlow models
- Real-time packet analysis
- Attack detection and classification
- Statistics tracking
- Health monitoring

**Models**:
- DDoS detection model
- Attack classification
- Confidence scoring

**Features Analyzed**:
- Packet size
- Protocol type
- Port numbers
- Packet rates (bps, pps)
- TCP flags
- Window size
- TTL values

#### 4.4 Identity Manager

**Directory**: `identity_manager/`

**Components**:
- `certificate_manager.py`: PKI operations
- `identity_database.py`: Device database
- `device_onboarding.py`: Onboarding workflow
- `behavioral_profiler.py`: Traffic profiling
- `policy_generator.py`: Policy generation

**Responsibilities**:
- Certificate Authority (CA) management
- Device certificate generation (X.509)
- Identity database (SQLite)
- Behavioral baseline establishment
- Least-privilege policy generation

**Database Schema**:
```sql
CREATE TABLE devices (
    device_id TEXT PRIMARY KEY,
    mac_address TEXT UNIQUE,
    certificate_path TEXT,
    key_path TEXT,
    device_type TEXT,
    device_info TEXT,
    onboarded_at TIMESTAMP,
    last_seen TIMESTAMP
);

CREATE TABLE behavioral_baselines (
    device_id TEXT PRIMARY KEY,
    avg_packet_size REAL,
    avg_packet_rate REAL,
    common_ports TEXT,
    traffic_pattern TEXT,
    established_at TIMESTAMP
);
```

#### 4.5 Trust Evaluator

**Directory**: `trust_evaluator/`

**Components**:
- `trust_scorer.py`: Trust calculation
- `device_attestation.py`: Certificate attestation
- `policy_adapter.py`: Policy adaptation

**Responsibilities**:
- Dynamic trust score calculation (0-100)
- Device attestation verification
- Trust-based policy adaptation
- Score history tracking

**Trust Score Factors**:
```
Initial Score: 70

Adjustments:
- Behavioral Anomaly: -10 to -30
- Attestation Failure: -20
- Security Alert (Low): -5
- Security Alert (Medium): -10
- Security Alert (High): -15
- Time Decay: -1 per day of inactivity

Final Score: Clamped to 0-100
```

**Trust Levels**:
- **High (80-100)**: Full access, normal policies
- **Medium (50-79)**: Restricted access, enhanced monitoring
- **Low (20-49)**: Limited access, strict policies
- **Critical (0-19)**: Quarantined, no access

#### 4.6 Heuristic Analyst

**Directory**: `heuristic_analyst/`

**Components**:
- `flow_analyzer.py`: Flow statistics analysis
- `anomaly_detector.py`: Heuristic detection
- `baseline_manager.py`: Baseline management

**Responsibilities**:
- Poll Ryu flow statistics
- Compare against baselines
- Detect anomalies using heuristics
- Generate security alerts

**Detection Rules**:
```python
# DoS Detection
if packet_rate > 1000 pps:
    alert = "DoS Attack Detected"
    severity = "high"

# Scanning Detection
if unique_dest_ports > 50 in 1 minute:
    alert = "Port Scanning Detected"
    severity = "medium"

# Volume Attack
if data_transfer > 10 MB in 1 minute:
    alert = "Volume Attack Detected"
    severity = "high"
```

#### 4.7 Honeypot Manager

**Directory**: `honeypot_manager/`

**Components**:
- `docker_manager.py`: Container management
- `honeypot_deployer.py`: Honeypot deployment
- `log_parser.py`: Log parsing
- `threat_intelligence.py`: Threat extraction
- `mitigation_generator.py`: Rule generation

**Responsibilities**:
- Deploy Cowrie honeypot (Docker)
- Parse honeypot logs
- Extract threat intelligence (IPs, commands)
- Generate mitigation rules
- Integrate with SDN controller

**Honeypot Configuration**:
- Type: Cowrie (SSH/Telnet honeypot)
- Ports: 2222 (SSH), 8080 (HTTP)
- Data Storage: `honeypot_data/cowrie/`
- Log Format: JSON

#### 4.8 Zero Trust Integration

**File**: `zero_trust_integration.py`

**Purpose**: Orchestrates all components

**Responsibilities**:
- Initialize all modules
- Coordinate component interactions
- Background monitoring threads
- Event handling
- Status reporting

**Background Threads**:
1. **Honeypot Monitor**: Monitors honeypot logs every 10 seconds
2. **Attestation Thread**: Performs device attestation every 5 minutes
3. **Policy Adapter**: Adapts policies every 1 minute

### Layer 5: Management Layer

**Purpose**: User interface and system management

**Components**:
- Web Dashboard (`templates/dashboard.html`)
- REST API endpoints
- Real-time updates (AJAX)

**Features**:
- Device overview and management
- Network topology visualization
- Security alerts display
- ML engine statistics
- SDN policy controls
- Trust score visualization
- Certificate management

**Technologies**:
- HTML5/CSS3
- JavaScript (vanilla)
- vis-network.js (topology)
- AJAX for real-time updates

---

## Component Architecture

### Component Interaction Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Zero Trust Framework                      │
│                    (Orchestrator)                            │
└─────────────────────────────────────────────────────────────┘
         │              │              │              │
         ↓              ↓              ↓              ↓
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│   Identity   │ │    Trust     │ │   Heuristic  │ │   Honeypot   │
│   Manager    │ │  Evaluator   │ │   Analyst    │ │   Manager    │
└──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
         │              │              │              │
         ↓              ↓              ↓              ↓
┌─────────────────────────────────────────────────────────────┐
│                    Flask Controller                          │
│  • Token Management                                          │
│  • Device Authorization                                      │
│  • Rate Limiting                                             │
│  • API Endpoints                                             │
└─────────────────────────────────────────────────────────────┘
         │              │              │
         ↓              ↓              ↓
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│   Ryu SDN    │ │   ML Security │ │   Dashboard  │
│  Controller  │ │    Engine     │ │              │
└──────────────┘ └──────────────┘ └──────────────┘
```

### Component Communication Patterns

#### 1. Synchronous Communication (HTTP/REST)
- Device → Controller: Token requests, data submission
- Dashboard → Controller: API calls for status
- Controller → ML Engine: Packet analysis

#### 2. Asynchronous Communication (Events)
- Heuristic Analyst → Trust Scorer: Anomaly alerts
- Trust Scorer → Policy Adapter: Trust score changes
- Honeypot Manager → Mitigation Generator: Threat intelligence

#### 3. Database Communication (SQLite)
- Identity Manager ↔ Identity Database
- Trust Scorer ↔ Score History
- Behavioral Profiler ↔ Baselines

#### 4. OpenFlow Protocol
- Ryu Controller ↔ SDN Switch
- Flow rule installation
- Statistics polling

---

## Data Flow Architecture

### 1. Device Onboarding Flow

```
┌──────────┐
│ ESP32    │
│ Device   │
└────┬─────┘
     │ 1. Connect to Gateway AP
     ↓
┌──────────┐
│ Gateway  │
└────┬─────┘
     │ 2. Forward onboarding request
     ↓
┌──────────┐
│ Flask    │
│Controller│
└────┬─────┘
     │ 3. Validate device authorization
     ↓
┌──────────┐
│Identity  │
│Manager   │
└────┬─────┘
     │ 4. Generate certificate
     │ 5. Create identity record
     │ 6. Establish baseline
     ↓
┌──────────┐
│Trust     │
│Scorer    │
└────┬─────┘
     │ 7. Initialize trust score (70)
     ↓
┌──────────┐
│Controller│
└────┬─────┘
     │ 8. Issue token
     ↓
┌──────────┐
│ Device   │
│ Ready    │
└──────────┘
```

### 2. Data Transmission Flow

```
┌──────────┐
│ ESP32    │
│ Node     │
└────┬─────┘
     │ 1. Collect sensor data
     │ 2. Create packet with token
     ↓
┌──────────┐
│ Gateway  │
└────┬─────┘
     │ 3. Forward to controller
     ↓
┌──────────┐
│ Flask    │
│Controller│
└────┬─────┘
     │ 4. Validate token
     │ 5. Check session timeout
     │ 6. Check rate limit
     │ 7. Check authorization
     ↓
┌──────────┐
│   ML     │
│  Engine  │
└────┬─────┘
     │ 8. Analyze packet
     │ 9. Detect attacks
     ↓
┌──────────┐
│   SDN    │
│  Policy  │
│  Engine  │
└────┬─────┘
     │ 10. Enforce policies
     │ 11. Apply flow rules
     ↓
┌──────────┐
│  Trust   │
│  Scorer  │
└────┬─────┘
     │ 12. Update trust score
     ↓
┌──────────┐
│Response  │
│Accept/   │
│Reject    │
└──────────┘
```

### 3. Threat Detection and Mitigation Flow

```
┌──────────┐
│Suspicious│
│ Traffic  │
└────┬─────┘
     │
     ↓
┌──────────┐      ┌──────────┐
│Heuristic │      │   ML     │
│ Analyst  │ ←──→ │  Engine  │
└────┬─────┘      └──────────┘
     │
     │ 1. Detect anomaly
     ↓
┌──────────┐
│  Trust   │
│  Scorer  │
└────┬─────┘
     │ 2. Reduce trust score
     ↓
┌──────────┐
│   SDN    │
│  Policy  │
│  Engine  │
└────┬─────┘
     │ 3. Redirect to honeypot
     ↓
┌──────────┐
│ Honeypot │
│ (Cowrie) │
└────┬─────┘
     │ 4. Capture attack
     ↓
┌──────────┐
│ Threat   │
│Intel     │
└────┬─────┘
     │ 5. Extract IOCs
     ↓
┌──────────┐
│Mitigation│
│Generator │
└────┬─────┘
     │ 6. Generate blocking rules
     ↓
┌──────────┐
│   SDN    │
│  Policy  │
│  Engine  │
└────┬─────┘
     │ 7. Install rules
     ↓
┌──────────┐
│  Policy  │
│ Adapter  │
└────┬─────┘
     │ 8. Update device policies
     ↓
┌──────────┐
│ Threat   │
│ Blocked  │
└──────────┘
```

---

## Security Architecture

### Security Layers

#### Layer 1: Device Authentication
- **Token-based**: UUID tokens, 5-minute expiry
- **PKI-based**: X.509 certificates (optional)
- **MAC address**: Device identification

#### Layer 2: Authorization
- **Device whitelist**: Pre-authorized devices
- **Dynamic revocation**: Real-time access control
- **Trust-based access**: Trust score determines access level

#### Layer 3: Rate Limiting
- **Per-device limits**: 60 packets/minute
- **Sliding window**: 60-second window
- **Automatic blocking**: When limit exceeded

#### Layer 4: Session Management
- **Timeout**: 5-minute sessions
- **Token invalidation**: Automatic on timeout
- **Activity tracking**: Last activity timestamp

#### Layer 5: Network Security
- **SDN policies**: Packet inspection, traffic shaping
- **Traffic redirection**: Suspicious traffic to honeypot
- **Quarantine**: Isolate compromised devices

#### Layer 6: Attack Detection
- **ML-based**: TensorFlow models for DDoS detection
- **Heuristic-based**: Rule-based anomaly detection
- **Behavioral analysis**: Baseline comparison

#### Layer 7: Threat Intelligence
- **Honeypot**: Active threat capture
- **Log analysis**: Threat extraction
- **Automatic mitigation**: Rule generation

### Zero Trust Principles Implementation

1. **Never Trust, Always Verify**
   - Every packet validated
   - Continuous authentication
   - Token validation on each request

2. **Least Privilege Access**
   - Trust-based access levels
   - Policy adaptation based on trust
   - Device-specific policies

3. **Assume Breach**
   - Honeypot for threat detection
   - Continuous monitoring
   - Automatic isolation

4. **Continuous Verification**
   - Periodic attestation (every 5 minutes)
   - Trust score updates
   - Behavioral monitoring

5. **Micro-segmentation**
   - Device isolation
   - Traffic redirection
   - Quarantine zones

---

## Network Architecture

### Network Topology

```
                    Internet
                       │
                       ↓
              ┌────────────────┐
              │   Router/AP     │
              │  (192.168.1.1)  │
              └────────┬────────┘
                       │ WiFi/Ethernet
                       ↓
        ┌──────────────┴──────────────┐
        │                              │
        ↓                              ↓
┌───────────────┐            ┌───────────────┐
│ Controller    │            │ ESP32 Gateway │
│ Server        │            │               │
│(192.168.1.100)│            │ AP: 192.168.4.1│
│               │            │ STA: DHCP     │
└───────────────┘            └───────┬───────┘
                                     │ WiFi AP
                                     │ "ESP32-AP"
                                     ↓
                        ┌────────────┴────────────┐
                        │                         │
                        ↓                         ↓
                ┌──────────────┐         ┌──────────────┐
                │ ESP32 Node 1 │         │ ESP32 Node 2 │
                │ (192.168.4.X)│         │ (192.168.4.Y)│
                └──────────────┘         └──────────────┘
```

### IP Address Allocation

**Controller Network** (192.168.1.0/24):
- Router: 192.168.1.1
- Controller: 192.168.1.100 (static recommended)
- Gateway (STA): DHCP from router

**Gateway AP Network** (192.168.4.0/24):
- Gateway (AP): 192.168.4.1 (fixed)
- Nodes: 192.168.4.2-254 (DHCP from gateway)

### Protocol Stack

```
Application Layer
    │
    ├── HTTP/JSON (Device ↔ Controller)
    ├── OpenFlow 1.3 (Controller ↔ Switch)
    └── REST API (Dashboard ↔ Controller)
    │
Transport Layer
    │
    ├── TCP (HTTP, OpenFlow)
    └── UDP (Optional for stats)
    │
Network Layer
    │
    └── IP (IPv4)
    │
Data Link Layer
    │
    ├── WiFi 802.11 (Device ↔ Gateway)
    └── Ethernet (Gateway ↔ Controller)
    │
Physical Layer
    │
    ├── 2.4 GHz WiFi
    └── Ethernet cable
```

---

## Deployment Architecture

### Development Deployment

```
Developer Machine
    │
    ├── Python 3.8+
    ├── Flask Controller
    ├── ML Engine
    ├── Virtual ESP32 devices (Mininet)
    └── Web Dashboard
```

### Production Deployment (Raspberry Pi)

```
Raspberry Pi 4
    │
    ├── Systemd Services
    │   ├── Flask Controller (port 5000)
    │   ├── Ryu SDN Controller (port 6653)
    │   └── Zero Trust Framework
    │
    ├── Docker
    │   └── Cowrie Honeypot
    │
    ├── SQLite Database
    │   └── identity.db
    │
    └── File System
        ├── certs/ (Certificates)
        ├── models/ (ML models)
        ├── logs/ (Log files)
        └── honeypot_data/ (Honeypot logs)
```

### Cloud Deployment

```
Cloud Provider (AWS/Azure/GCP)
    │
    ├── Compute Instance
    │   ├── Flask Controller
    │   ├── ML Engine
    │   └── Zero Trust Framework
    │
    ├── Container Service
    │   └── Honeypot containers
    │
    ├── Database Service
    │   └── Device identity database
    │
    └── Load Balancer
        └── Distribute traffic
```

### Hybrid Deployment

```
On-Premise Gateway
    │
    └── ESP32 Gateway
        └── Local IoT devices

Cloud Controller
    │
    └── Centralized control
        └── Multiple gateways
```

---

## Scalability Architecture

### Horizontal Scaling

- **Multiple Controllers**: Load balance across instances
- **Database Replication**: SQLite → PostgreSQL
- **Redis Cache**: Token caching
- **Message Queue**: Async processing (RabbitMQ/Kafka)

### Vertical Scaling

- **Raspberry Pi 4**: 4GB → 8GB RAM
- **Server Upgrade**: More CPU/RAM
- **SSD Storage**: Faster I/O
- **GPU**: ML model acceleration

---

## Performance Architecture

### Optimization Strategies

1. **Caching**: Token cache, trust score cache
2. **Async Processing**: Background threads for heavy operations
3. **Database Indexing**: Fast device lookups
4. **Connection Pooling**: Reuse database connections
5. **Batch Processing**: Group similar operations

### Performance Metrics

- **Token Generation**: < 10ms
- **Packet Analysis**: < 50ms (ML)
- **Policy Enforcement**: < 5ms
- **Trust Score Update**: < 20ms
- **Dashboard Load**: < 500ms

---

**Last Updated**: 2024-01-15
**Version**: 1.0.0

