# Device Onboarding Guide

> **Complete reference for automatic and manual device onboarding workflows**

## Table of Contents

1. [Overview](#overview)
2. [Automatic WiFi Onboarding](#automatic-wifi-onboarding)
3. [Secure PKI Onboarding](#secure-pki-onboarding)
4. [Database Schema](#database-schema)
5. [API Reference](#api-reference)
6. [Configuration](#configuration)
7. [Troubleshooting](#troubleshooting)
8. [Changelog](#changelog)

---

## Overview

The SecureIoT-SDN framework supports two onboarding methods:

1. **Automatic WiFi Onboarding**: Devices automatically detected when connecting to Raspberry Pi WiFi, pending admin approval
2. **Secure PKI Onboarding**: Manual onboarding with certificate generation, physical identity linking, and behavioral profiling

Both methods integrate seamlessly and provide strong security guarantees.

---

## Automatic WiFi Onboarding

### System Architecture

The automatic onboarding system enables zero-touch device detection and approval workflow.

```
Device Connects to WiFi
    ↓
WiFi Detector (monitors hostapd/ARP)
    ↓
Device ID Generator (MAC prefix + random key)
    ↓
Pending Device Entry Created
    ↓
Admin Reviews in Dashboard
    ↓
Approve → Triggers Full PKI Onboarding
    or
Reject → Device Marked as Rejected
```

### Components

#### 1. WiFi Detector (`network_monitor/wifi_detector.py`)
- Monitors hostapd log files for WiFi association events
- Falls back to ARP table monitoring if logs unavailable
- Detects new MAC addresses on network
- Tracks known devices to avoid duplicates

**Log Monitoring**:
```bash
# Monitors /var/log/hostapd.log for:
wlan0: STA AA:BB:CC:DD:EE:FF IEEE 802.11: authenticated
```

#### 2. Device ID Generator (`network_monitor/device_id_generator.py`)
Generates unique, secure device IDs from MAC addresses.

**Format**: `DEV_<MAC_PREFIX>_<RANDOM_KEY>`

**Example**:
- MAC: `AA:BB:CC:DD:EE:FF`
- Prefix: `AA_BB_CC`
- Random Key: `A3F2K9` (6 alphanumeric chars)
- Device ID: `DEV_AA_BB_CC_A3F2K9`

**Benefits**:
- Prevents MAC address enumeration
- Ensures uniqueness
- User-friendly format

#### 3. Pending Devices Manager (`network_monitor/pending_devices.py`)
Manages device approval workflow with SQLite persistence.

**Status Flow**: `pending` → `approved` → `onboarded`  
or `pending` → `rejected`

#### 4. Auto-Onboarding Service (`network_monitor/auto_onboarding_service.py`)
- Background monitoring thread (2-second intervals)
- Integrates with DeviceOnboarding for certificate provisioning
- Handles approval/rejection actions

### Configuration

Edit `network_monitor/config.py`:
```python
# WiFi interface
WIFI_INTERFACE = 'wlan0'

# hostapd log paths (searched in order)
HOSTAPD_LOG_PATHS = [
    '/var/log/hostapd.log',
    '/var/log/hostapd/hostapd.log',
    '/tmp/hostapd.log'
]

# Monitoring interval
MONITORING_INTERVAL = 2  # seconds

# Device ID configuration
DEVICE_ID_PREFIX = 'DEV'
DEVICE_ID_RANDOM_LENGTH = 6
```

### Workflow

#### 1. Device Detection
1. New IoT device connects to Raspberry Pi WiFi (SSID: configured in hostapd)
2. WiFi Detector captures MAC address from hostapd logs or ARP table
3. Checks if device already known (in identity database or pending list)
4. If new, proceeds to ID generation

#### 2. ID Generation
1. Extract MAC prefix (first 3 octets): `AA:BB:CC`
2. Generate random 6-character key: `A3F2K9`
3. Combine: `DEV_AA_BB_CC_A3F2K9`
4. Verify uniqueness against existing device IDs

#### 3. Pending Entry Creation
1. Device added to `pending_devices` table
2. Status: `pending`
3. Timestamp: Current time
4. Available for admin review

#### 4. Admin Review
1. Admin opens "Device Approval" tab in dashboard
2. Reviews pending device:
   - Device ID (generated)
   - MAC address
   - Detection timestamp
3. Makes decision: Approve or Reject

#### 5. On Approval
1. Admin clicks "Approve" button
2. System calls `/api/approve_device`
3. Triggers full PKI onboarding automatically:
   - Certificate generation
   - Physical identity linking
   - Behavioral profiling starts
   - Trust score initialized (70)
4. Device status updated: `approved` → `onboarded`
5. Device appears in main dashboard topology

#### 6. On Rejection
1. Admin clicks "Reject" button
2. System calls `/api/reject_device`
3. Device status updated: `rejected`
4. Device removed from pending list
5. Action logged in history

### API Endpoints

#### GET /api/pending_devices
Returns devices awaiting approval.

**Response**:
```json
{
    "status": "success",
    "devices": [
        {
            "id": 1,
            "mac_address": "AA:BB:CC:DD:EE:01",
            "device_id": "DEV_AA_BB_CC_A3F2K9",
            "detected_at": "2024-01-15 10:30:00",
            "status": "pending"
        }
    ]
}
```

---

#### POST /api/approve_device
Approves pending device and triggers onboarding.

**Request**:
```json
{
    "mac_address": "AA:BB:CC:DD:EE:01",
    "admin_notes": "Approved for testing"
}
```

**Response**:
```json
{
    "status": "success",
    "message": "Device approved and onboarded successfully",
    "device_id": "DEV_AA_BB_CC_A3F2K9",
    "onboarding_result": {
        "status": "success",
        "certificate_path": "certs/DEV_AA_BB_CC_A3F2K9_cert.pem",
        "key_path": "certs/DEV_AA_BB_CC_A3F2K9_key.pem"
    }
}
```

---

#### POST /api/reject_device
Rejects pending device.

**Request**:
```json
{
    "mac_address": "AA:BB:CC:DD:EE:01",
    "admin_notes": "Unknown device, rejected"
}
```

**Response**:
```json
{
    "status": "success",
    "message": "Device rejected successfully"
}
```

---

#### GET /api/device_history
Returns device approval history.

**Query Parameters**:
- `mac_address` (optional): Filter by MAC
- `limit` (optional): Max records (default: 100)

**Response**:
```json
{
    "status": "success",
    "history": [
        {
            "id": 1,
            "mac_address": "AA:BB:CC:DD:EE:01",
            "device_id": "DEV_AA_BB_CC_A3F2K9",
            "action": "approved",
            "timestamp": "2024-01-15 10:35:00",
            "admin_notes": "Approved for testing"
        }
    ]
}
```

---

## Secure PKI Onboarding

### Overview

Secure onboarding provides certificate-based authentication with physical identity binding and automatic behavioral profiling.

### Features

- ✅ X.509 certificate generation
- ✅ Physical identity linking (MAC + fingerprint)
- ✅ Behavioral profiling (5-minute observation)
- ✅ Traffic recording and analysis
- ✅ Automatic baseline establishment
- ✅ Least-privilege policy generation
- ✅ Zero-touch finalization

### Complete Workflow

```
1. Onboarding Request
   ↓
2. Physical Identity Creation
   - MAC address
   - Device type
   - Fingerprint (SHA-256)
   ↓
3. Certificate Generation (X.509)
   - Device certificate
   - Private key
   - CA certificate
   ↓
4. Database Entry
   - Identity record
   - Physical identity metadata
   ↓
5. Trust Score Initialization (70)
   ↓
6. Behavioral Profiling Starts (5 minutes)
   - Traffic recording activated
   - SDN captures all packets
   ↓
7. Traffic Observation
   - IPs accessed
   - Ports used
   - Protocols
   - Packet sizes
   ↓
8. Automatic Finalization (after 5 min)
   - Behavioral baseline established
   - Least-privilege policy generated
   - Policy applied to SDN controller
   ↓
9. Continuous Monitoring
   - Attestation (every 5 min)
   - Anomaly detection
   - Trust score updates
```

### Physical Identity Linking

**Purpose**: Strong binding between physical device and network credential

**Physical Identity Components**:
```json
{
    "mac_address": "AA:BB:CC:DD:EE:FF",
    "device_type": "sensor",
    "first_seen": "2024-01-15T10:30:00Z",
    "onboarding_timestamp": "2024-01-15T10:30:00Z"
}
```

**Device Fingerprint**:
```
SHA256(MAC_ADDRESS:DEVICE_TYPE:FIRST_SEEN_TIMESTAMP)[:16]
Example: a3f2k9b8c7d6e5f4
```

**Benefits**:
- Prevents device spoofing
- Audit trail of physical characteristics
- Foundation for Zero Trust architecture

### Behavioral Profiling Period

**Duration**: 5 minutes (configurable)

**What's Captured**:
1. **Destination IPs**: All IPs the device communicates with
2. **Destination Ports**: TCP/UDP ports accessed
3. **Protocols**: IP protocol types (TCP=6, UDP=17, ICMP=1)
4. **Packet Sizes**: Average and distribution
5. **Traffic Rates**: Packets per second, bytes per second

**Traffic Recording** (`ryu_controller/sdn_policy_engine.py`):
```python
# SDN Policy Engine records traffic during profiling
if device_id and self.onboarding_module:
    packet_info = {
        'size': len(msg.data),
        'dst_ip': ip_pkt.dst,
        'dst_port': tcp_pkt.dst_port,
        'protocol': ip_pkt.proto
    }
    self.onboarding_module.record_traffic(device_id, packet_info)
```

### Baseline Establishment

**Metrics Recorded**:
- Average packets per second
- Average bytes per second
- Common destinations (top 10 IPs)
- Common ports (top 10)
- Traffic pattern fingerprint

**Baseline Format**:
```json
{
    "avg_packet_size": 1024,
    "avg_packet_rate": 0.15,
    "common_destinations": ["192.168.1.100", "192.168.1.101"],
    "common_ports": [80, 443, 8080],
    "protocols": [6, 17],
    "established_at": "2024-01-15T10:35:00Z"
}
```

### Automatic Policy Generation

**Least-Privilege Approach**:
The system generates policies that ONLY allow observed traffic patterns.

**Generated Policy Example**:
```python
policy = {
    'device_id': 'ESP32_2',
    'action': 'allow',
    'rules': [
        # Allow observed IPs
        {'type': 'allow', 'match': {'ipv4_dst': '192.168.1.100'}, 'priority': 100},
        # Allow observed ports
        {'type': 'allow', 'match': {'tcp_dst': 80}, 'priority': 100},
        {'type': 'allow', 'match': {'tcp_dst': 443}, 'priority': 100},
        # Default deny (everything else)
        {'type': 'deny', 'match': {}, 'priority': 0}
    ],
    'rate_limit': {'packets_per_second': 10.0}
}
```

### Automatic Finalization

**Background Monitoring** (`device_onboarding.py`):
- Monitoring thread runs every 30 seconds
- Checks all devices in active profiling
- When profiling period expires (5 minutes):
  1. Calls `finalize_onboarding(device_id)`
  2. Establishes baseline from recorded traffic
  3. Generates least-privilege policy
  4. Applies policy to SDN controller
  5. Status updated to `finalized`

**Edge Cases**:
- **Insufficient Traffic** (\u003c5 packets): Finalizes with available data, logs warning
- **Device Disconnected**: Profiling continues, finalizes on schedule
- **Manual Override**: Admin can manually finalize via `/finalize_onboarding`

### API Endpoints

#### POST /onboard
Manually onboard a device.

**Request**:
```json
{
    "device_id": "ESP32_2",
    "mac_address": "AA:BB:CC:DD:EE:FF",
    "device_type": "sensor",
    "device_info": "Temperature sensor"
}
```

**Response**:
```json
{
    "status": "success",
    "device_id": "ESP32_2",
    "certificate_path": "certs/ESP32_2_cert.pem",
    "key_path": "certs/ESP32_2_key.pem",
    "ca_certificate": "-----BEGIN CERTIFICATE-----\n...",
    "profiling": true,
    "device_fingerprint": "a3f2k9b8c7d6e5f4",
    "physical_identity_linked": true,
    "message": "Device onboarded successfully. Behavioral profiling started."
}
```

---

#### GET /get_profiling_status
Check profiling status for a device.

**Query Parameters**: `device_id` (required)

**Response (Active Profiling)**:
```json
{
    "status": "success",
    "device_id": "ESP32_2",
    "is_profiling": true,
    "elapsed_time": 120.5,
    "remaining_time": 179.5,
    "packet_count": 45,
    "byte_count": 10240
}
```

**Response (Completed)**:
```json
{
    "status": "success",
    "device_id": "ESP32_2",
    "is_profiling": false,
    "baseline_established": true,
    "baseline": {
        "avg_packet_rate": 0.15,
        "common_destinations": ["192.168.1.100"]
    }
}
```

---

#### POST /finalize_onboarding
Manually finalize onboarding (optional - auto-finalizes after 5 min).

**Request**:
```json
{
    "device_id": "ESP32_2"
}
```

**Response**:
```json
{
    "status": "success",
    "device_id": "ESP32_2",
    "baseline": {...},
    "policy": {...},
    "message": "Onboarding finalized. Baseline and policy generated."
}
```

---

## Database Schema

### devices Table
```sql
CREATE TABLE devices (
    device_id TEXT PRIMARY KEY,
    mac_address TEXT UNIQUE NOT NULL,
    certificate_path TEXT,
    key_path TEXT,
    onboarded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP,
    status TEXT DEFAULT 'active',
    device_type TEXT,
    device_info TEXT,
    physical_identity TEXT,        -- JSON metadata
    first_seen TIMESTAMP,           -- First detection time
    device_fingerprint TEXT         -- SHA-256 fingerprint
)
```

### pending_devices Table
```sql
CREATE TABLE pending_devices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mac_address TEXT UNIQUE NOT NULL,
    device_id TEXT NOT NULL,
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'pending',
    approved_at TIMESTAMP,
    rejected_at TIMESTAMP,
    onboarded_at TIMESTAMP,
    device_type TEXT,
    device_info TEXT,
    admin_notes TEXT
)
```

### device_history Table
```sql
CREATE TABLE device_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mac_address TEXT NOT NULL,
    device_id TEXT,
    action TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    admin_notes TEXT
)
```

### behavioral_baselines Table
```sql
CREATE TABLE behavioral_baselines (
    device_id TEXT PRIMARY KEY,
    baseline_data TEXT,
    established_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    FOREIGN KEY (device_id) REFERENCES devices(device_id)
)
```

### device_policies Table
```sql
CREATE TABLE device_policies (
    device_id TEXT PRIMARY KEY,
    policy_data TEXT,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    FOREIGN KEY (device_id) REFERENCES devices(device_id)
)
```

---

## Configuration

### Profiling Configuration

Edit `identity_manager/device_onboarding.py`:
```python
self.profiler = BehavioralProfiler(profiling_duration=300)  # 5 minutes
self.monitoring_interval = 30  # Check every 30 seconds
self.min_traffic_packets = 5   # Minimum packets for baseline
```

### WiFi Detection Configuration

Edit `network_monitor/config.py`:
```python
WIFI_INTERFACE = 'wlan0'
MONITORING_INTERVAL = 2
DEVICE_ID_PREFIX = 'DEV'
DEVICE_ID_RANDOM_LENGTH = 6
```

---

## Troubleshooting

### Automatic WiFi Onboarding Issues

**Problem**: Devices not detected

**Solutions**:
1. Check hostapd log file exists:
   ```bash
   ls -l /var/log/hostapd.log
   sudo chmod 644 /var/log/hostapd.log
   ```
2. Verify WiFi interface name:
   ```bash
   ip link show
   # Update WIFI_INTERFACE in config if needed
   ```
3. Check ARP table access:
   ```bash
   arp -n -i wlan0
   ```
4. Review service logs in controller output

---

**Problem**: Approval not triggering onboarding

**Solutions**:
1. Check browser console for JavaScript errors
2. Verify API endpoint accessible:
   ```bash
   curl http://localhost:5000/api/pending_devices
   ```
3. Check controller logs for errors
4. Verify onboarding module initialized

---

### PKI Onboarding Issues

**Problem**: Certificate generation fails

**Solutions**:
1. Check `certs/` directory permissions:
   ```bash
   ls -ld certs/
   chmod 755 certs/
   ```
2. Verify cryptography package installed:
   ```bash
   pip install cryptography
   ```
3. Check CA certificate exists:
   ```bash
   ls -l certs/ca_cert.pem
   ```

---

**Problem**: Profiling not finalizing

**Solutions**:
1. Check monitoring thread is running
2. Check logs for errors
3. Manually finalize:
   ```bash
   curl -X POST http://localhost:5000/finalize_onboarding \
     -H "Content-Type: application/json" \
     -d '{"device_id": "ESP32_2"}'
   ```

---

**Problem**: Traffic not being recorded

**Solutions**:
1. Verify SDN Policy Engine connected
2. Check `set_onboarding_module()` was called
3. Verify device is in active profiling:
   ```bash
   curl "http://localhost:5000/get_profiling_status?device_id=ESP32_2"
   ```
4. Check SDN controller processing packets

---

## Changelog

### Version 2.0 (2024)
**Automatic WiFi Onboarding**:
- ✅ Automatic device detection via hostapd/ARP
- ✅ Secure device ID generation (MAC + random key)
- ✅ Pending approval workflow
- ✅ Admin dashboard integration
- ✅ Approval history tracking

**Secure PKI Onboarding**:
- ✅ Physical identity linking
- ✅ Device fingerprinting (SHA-256)
- ✅ Automatic behavioral profiling (5 minutes)
- ✅ Traffic recording integration with SDN
- ✅ Automatic baseline establishment
- ✅ Least-privilege policy generation
- ✅ Zero-touch finalization

**Database Enhancements**:
- ✅ Extended schema with physical identity fields
- ✅ Automatic database migration
- ✅ Pending devices management
- ✅ Approval history tracking

**API Additions**:
- ✅ `/api/pending_devices` - Get pending devices
- ✅ `/api/approve_device` - Approve device
- ✅ `/api/reject_device` - Reject device
- ✅ `/api/device_history` - Get approval history
- ✅ `/get_profiling_status` - Check profiling status
- ✅ `/finalize_onboarding` - Manual finalization

---

**Last Updated**: 2026-01-02  
**Version**: 2.0
