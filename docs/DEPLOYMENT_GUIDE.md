# Deployment Guide

> **Complete deployment reference for Raspberry Pi, cloud, and ESP32 hardware setup**

## Table of Contents

1. [Hardware Requirements](#hardware-requirements)
2. [Controller Deployment](#controller-deployment)
3. [ESP32 Hardware Setup](#esp32-hardware-setup)
4. [Physical Sensor Integration](#physical-sensor-integration)
5. [Network Configuration](#network-configuration)
6. [Testing & Verification](#testing--verification)
7. [Production Deployment](#production-deployment)

---

## Hardware Requirements

### Controller Server Options

**Option 1: Raspberry Pi 4** (Recommended for SOHO)
- Model: Raspberry Pi 4 Model B
- RAM: 4GB minimum, 8GB recommended
- Storage: 32GB+ microSD (Class 10+)
- OS: Raspberry Pi OS 64-bit
- Network: Ethernet or WiFi

**Option 2: Linux Server/VM**
- CPU: 2+ cores
- RAM: 4GB minimum
- Storage: 20GB+ free space
- OS: Ubuntu 20.04+ or Debian 11+

**Option 3: Cloud Instance**
- Provider: AWS EC2, Azure VM, GCP Compute Engine
- Instance: t3.medium or equivalent
- OS: Ubuntu 20.04 LTS

### ESP32 Development Boards

**Gateway Requirements**:
- ESP32-WROOM-32 or ESP32-DevKitC
- Power: 5V USB or external adapter (2A)
- Antenna: Built-in PCB (external optional)

**Node Requirements**:
- ESP32-WROOM-32 or ESP32-DevKit C
- Power: 5V USB or battery pack
- Sensors: Based on use case
- Breadboard and jumper wires

### Common Sensors

- **Temperature**: DS18B20, DHT22, LM35
- **Humidity**: DHT22, DHT11
- **Motion**: PIR (HC-SR501)
- **Light**: LDR, BH1750
- **Gas**: MQ-2, MQ-7

---

## Controller Deployment

### Raspberry Pi 4 Deployment

#### 1. Install Raspberry Pi OS

1. Download Raspberry Pi Imager from raspberrypi.org
2. Flash OS to microSD card
3. Enable SSH: Create empty `ssh` file in boot partition
4. Configure WiFi: Create `wpa_supplicant.conf` in boot partition:
   ```
   country=US
   ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
   update_config=1

   network={
     ssid="YourWiFiSSID"
     psk="YourWiFiPassword"
   }
   ```
5. Boot Raspberry Pi

#### 2. Initial Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3-pip python3-venv git openssl sqlite3 docker.io

# Start Docker
sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker $USER
```

#### 3. Clone and Setup Project

```bash
cd ~
git clone <repository-url> IOT-project
cd IOT-project

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

#### 4. Automated Setup Script

For complete automated deployment on Raspberry Pi:

```bash
cd ~/IOT-project
sudo bash scripts/raspberry_pi_setup.sh
```

The script will:
- Install all dependencies (Python, Docker, Ryu)
- Configure systemd services
- Set up firewall rules
- Create necessary directories

**Services Created**:
- `ryu-sdn-controller.service` - SDN controller (port 6653)
- `zero-trust-sdn.service` - Zero Trust framework
- `flask-controller.service` - Web dashboard (port 5000)

#### 5. Start Services

```bash
sudo systemctl start ryu-sdn-controller
sudo systemctl start zero-trust-sdn
sudo systemctl start flask-controller

# Enable auto-start on boot
sudo systemctl enable ryu-sdn-controller
sudo systemctl enable zero-trust-sdn
sudo systemctl enable flask-controller

# Check status
sudo systemctl status flask-controller
```

---

### Linux Server Deployment

#### 1. Install Dependencies

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git openssl sqlite3 docker.io
```

#### 2. Setup Project

```bash
cd /opt  # or your preferred directory
git clone <repository-url> IOT-project
cd IOT-project
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### 3. Configure Controller

Edit `controller.py`:
```python
# Add authorized devices
authorized_devices = {
    "ESP32_2": True,
    "ESP32_3": True,
    "ESP32_4": True
}
```

#### 4. Run Controller

```bash
# Manual start
python controller.py

# Or use screen for background
screen -S secureiot
python controller.py
# Press Ctrl+A then D to detach
```

---

### Cloud Deployment (AWS EC2)

#### 1. Launch Instance

- AMI: Ubuntu 20.04 LTS
- Instance Type: t3.medium
- Security Group:
  - Port 22 (SSH)
  - Port 5000 (HTTP - Dashboard)
  - Port 6653 (OpenFlow) if needed

#### 2. Connect and Setup

```bash
# SSH to instance
ssh -i your-key.pem ubuntu@<instance-ip>

# Install dependencies
sudo apt update
sudo apt install -y python3-pip python3-venv git docker.io

# Clone and setup project
git clone <repository-url> IOT-project
cd IOT-project
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run controller
python controller.py
```

#### 3. Access Dashboard

Open browser: `http://<instance-public-ip>:5000`

---

## ESP32 Hardware Setup

### Software Prerequisites

#### Install Arduino IDE

**Linux**:
```bash
sudo apt install arduino
```

**Windows/macOS**: Download from https://www.arduino.cc/en/software

#### Install ESP32 Board Support

1. Open Arduino IDE
2. Go to **File → Preferences**
3. Add to "Additional Board Manager URLs":
   ```
   https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
   ```
4. Go to **Tools → Board → Boards Manager**
5. Search for "ESP32" and install "esp32" by Espressif Systems

#### Install Required Libraries

Via **Tools → Manage Libraries**:
- ArduinoJson (v6.x)
- OneWire (for DS18B20)
- DallasTemperature (for DS18B20)
- DHT sensor library (for DHT22/DHT11)
- Adafruit Unified Sensor

---

### ESP32 Gateway Setup

#### 1. Hardware Connection
- Connect ESP32 to computer via USB
- Install drivers if needed (CP2102/CH340)

#### 2. Configure Firmware

Open `esp32/gateway.ino` and configure:

```cpp
// Access Point Configuration
const char *ap_ssid = "ESP32-AP";
const char *ap_password = "12345678";  // Min 8 chars

// Station Mode Configuration
const char *sta_ssid = "YourWiFi";
const char *sta_password = "YourPassword";

// Controller IP
const char *controller_ip = "192.168.1.100";
```

#### 3. Upload Firmware

1. Select **Board**: Tools → Board → ESP32 Dev Module
2. Select **Port**: Tools → Port → (your ESP32 port)
3. Click **Upload**
4. Wait for "Done uploading"

#### 4. Verify Operation

1. Open **Serial Monitor** (115200 baud)
2. Check output:
   ```
   Gateway AP Started
   Connected to WiFi
   ```
3. Verify "ESP32-AP" appears in WiFi networks

---

### ESP32 Node Setup

#### 1. Configure Firmware

Open `esp32/node.ino`:

```cpp
// Gateway AP Configuration
const char *ssid = "ESP32-AP";
const char *password = "12345678";

// Gateway IP
const char *controller_ip = "192.168.4.1";

// Device ID (UNIQUE for each node!)
String device_id = "ESP32_2";  // Change for each: ESP32_2, ESP32_3, etc.
```

**Critical**: Change `device_id` for each node!

#### 2. Update Controller Authorization

Edit `controller.py`:
```python
authorized_devices = {
    "ESP32_2": True,
    "ESP32_3": True,
    "ESP32_4": True
}
```

#### 3. Upload to Each Node

For each ESP32 node:
1. Update `device_id` in code
2. Select Board and Port
3. Upload firmware
4. Repeat for additional nodes

---

## Physical Sensor Integration

### Temperature Sensor (DS18B20)

**Wiring**:
```
DS18B20:
  Red (VDD)    → 3.3V
  Black (GND)  → GND
  Yellow (DATA) → GPIO 4 (with 4.7kΩ pull-up to 3.3V)
```

**Code** (`esp32/node.ino`):
```cpp
#include <OneWire.h>
#include <DallasTemperature.h>

#define ONE_WIRE_BUS 4
OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature sensors(&oneWire);

void setup() {
    sensors.begin();
    // ... WiFi setup ...
}

void loop() {
    sensors.requestTemperatures();
    float temp = sensors.getTempCByIndex(0);
    
    // Send to controller
    StaticJsonDocument<200> doc;
    doc["device_id"] = device_id;
    doc["token"] = token;
    doc["temperature"] = temp;
    
    // ... HTTP POST ...
    delay(5000);
}
```

---

### Humidity Sensor (DHT22)

**Wiring**:
```
DHT22:
  VCC  → 3.3V
  GND  → GND
  DATA → GPIO 2 (with 10kΩ pull-up to 3.3V)
```

**Code**:
```cpp
#include <DHT.h>

#define DHTPIN 2
#define DHTTYPE DHT22
DHT dht(DHTPIN, DHTTYPE);

void setup() {
    dht.begin();
}

void loop() {
    float humidity = dht.readHumidity();
    float temperature = dht.readTemperature();
    
    // Send to controller
    // ...
}
```

---

### Motion Sensor (PIR)

**Wiring**:
```
PIR (HC-SR501):
  VCC → 5V (or 3.3V)
  GND → GND
  OUT → GPIO 2
```

**Code**:
```cpp
#define PIR_PIN 2

void setup() {
    pinMode(PIR_PIN, INPUT);
}

void loop() {
    int motion = digitalRead(PIR_PIN);
    String status = motion ? "MOTION_DETECTED" : "NO_MOTION";
    
    // Send to controller
    // ...
    delay(1000);
}
```

---

## Network Configuration

### Network Topology

```
Internet
  ↓
Router (192.168.1.1)
  ├─→ Controller (192.168.1.100)
  └─→ Gateway (192.168.1.50 - DHCP)
         ↓ WiFi AP "ESP32-AP"
         ├─→ Node 1 (192.168.4.2)
         ├─→ Node 2 (192.168.4.3)
         └─→ Node N (192.168.4.X)
```

### IP Address Configuration

**Controller Network** (192.168.1.0/24):
- Router: 192.168.1.1
- Controller: 192.168.1.100 (static recommended)
- Gateway (STA): DHCP from router

**Gateway AP Network** (192.168.4.0/24):
- Gateway (AP): 192.168.4.1 (fixed)
- Nodes: 192.168.4.2-254 (DHCP)

### Set Static IP for Controller

**Raspberry Pi**:
```bash
sudo nano /etc/dhcpcd.conf

# Add:
interface eth0
static ip_address=192.168.1.100/24
static routers=192.168.1.1
static domain_name_servers=8.8.8.8 8.8.4.4

sudo systemctl restart dhcpcd
```

### Firewall Configuration

```bash
# UFW (Ubuntu)
sudo ufw allow 5000/tcp  # Flask controller
sudo ufw allow 6653/tcp  # OpenFlow
sudo ufw enable
```

---

## Testing & Verification

### 1. Controller Verification

```bash
# Check controller running
curl http://localhost:5000

# Should see dashboard HTML
```

### 2. Gateway Verification

1. Check "ESP32-AP" in WiFi networks
2. Serial Monitor shows:
   - "Gateway AP Started"
   - "Connected to WiFi"
3. Can ping controller from gateway network

### 3. Node Verification

1. Serial Monitor shows:
   - "Connected to Gateway"
   - "Received token: ..."
   - "Sent: ... | Response: 200"
2. Dashboard shows device in topology
3. Data packets appearing in dashboard

### 4. End-to-End Test

1. Power on gateway and nodes
2. Nodes request tokens
3. Nodes send sensor data
4. Dashboard displays:
   - Network topology with all nodes
- Device packet counts
   - Trust scores
5. Try revoking authorization:
   - Device stops receiving data acceptance

---

## Production Deployment

### Security Hardening

1. **Change Default Passwords**:
   - WiFi AP password
   - Dashboard admin password (if implemented)

2. **Enable HTTPS**:
   ```bash
   # Generate SSL certificate
   openssl req -x509 -newkey rsa:4096 -nodes \
     -keyout key.pem -out cert.pem -days 365
   ```

3. **Firewall Rules**:
   - Allow only necessary ports
   - Restrict SSH to specific IPs

4. **Update Regularly**:
   ```bash
   cd ~/IOT-project
   git pull
   pip install -r requirements.txt --upgrade
   ```

### Monitoring

**Check Logs**:
```bash
# Controller logs
journalctl -u flask-controller -f

# System logs
tail -f logs/controller.log
tail -f logs/zero_trust.log
```

**Monitor Services**:
```bash
sudo systemctl status flask-controller
sudo systemctl status ryu-sdn-controller
sudo systemctl status zero-trust-sdn
```

### Backup

```bash
# Backup database
cp identity.db identity.db.backup
cp pending_devices.db pending_devices.db.backup

# Backup certificates
tar -czf certs-backup.tar.gz certs/
```

### Troubleshooting

**Controller Not Starting**:
- Check Python version: `python3 --version` (need 3.8+)
- Verify dependencies: `pip install -r requirements.txt`
- Check port 5000 not in use: `sudo lsof -i :5000`

**Gateway Not Connecting**:
- Verify WiFi credentials in code
- Check Serial Monitor for errors
- Ping controller: `ping 192.168.1.100`

**Nodes Not Receiving Tokens**:
- Verify device ID authorized in `controller.py`
- Check gateway forwarding data
- Review controller logs

**Dashboard Not Loading**:
- Clear browser cache
- Check JavaScript console for errors
- Verify API endpoints responding

---

## Quick Start Commands

### Start System (Manual)

```bash
# Activate venv
cd ~/IOT-project
source venv/bin/activate

# Start controller
python controller.py
```

### Start System (Systemd)

```bash
sudo systemctl start flask-controller
sudo systemctl start ryu-sdn-controller
sudo systemctl start zero-trust-sdn
```

### Access Dashboard

```
http://192.168.1.100:5000
```

---

**Last Updated**: 2026-01-02  
**Version**: 2.0
