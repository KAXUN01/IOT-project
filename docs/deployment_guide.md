# Raspberry Pi 4 Deployment Guide

## Zero Trust SDN Framework for SOHO IoT Networks

This guide provides instructions for deploying the Zero Trust SDN Framework on a Raspberry Pi 4.

## Prerequisites

- Raspberry Pi 4 (4GB RAM recommended, 8GB preferred)
- MicroSD card (32GB minimum, Class 10 or better)
- Raspberry Pi OS (64-bit recommended)
- Internet connection
- SDN-compatible switch (optional, for physical deployment)

## System Requirements

- Python 3.8 or higher
- Docker (for honeypot deployment)
- OpenSSL
- SQLite3
- Git

## Installation Steps

### 1. Install Base System

```bash
# Update system
sudo apt update
sudo apt upgrade -y

# Install required packages
sudo apt install -y python3-pip python3-venv git openssl sqlite3 docker.io

# Start Docker service
sudo systemctl enable docker
sudo systemctl start docker

# Add user to docker group (optional, to run docker without sudo)
sudo usermod -aG docker $USER
```

### 2. Install Ryu SDN Controller

```bash
# Install Ryu
pip3 install ryu eventlet

# Verify installation
ryu-manager --version
```

### 3. Clone and Setup Project

```bash
# Clone repository
cd ~
git clone <repository-url> IOT-project
cd IOT-project

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 4. Configure System

```bash
# Create necessary directories
mkdir -p certs honeypot_data logs

# Set permissions
chmod 755 certs honeypot_data logs
```

### 5. Start Services

#### Option A: Using Systemd Services

Create service file `/etc/systemd/system/zero-trust-sdn.service`:

```ini
[Unit]
Description=Zero Trust SDN Framework
After=network.target docker.service

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/IOT-project
Environment="PATH=/home/pi/IOT-project/venv/bin"
ExecStart=/home/pi/IOT-project/venv/bin/python3 zero_trust_integration.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable zero-trust-sdn.service
sudo systemctl start zero-trust-sdn.service
```

#### Option B: Manual Start

```bash
cd ~/IOT-project
source venv/bin/activate
python3 zero_trust_integration.py
```

### 6. Start Ryu Controller

In a separate terminal:

```bash
cd ~/IOT-project
source venv/bin/activate
ryu-manager ryu_controller/sdn_policy_engine.py
```

## Configuration

### Network Configuration

1. Configure Raspberry Pi as SDN controller:
   - Set static IP address
   - Configure firewall rules
   - Enable SSH access

2. Connect SDN switch:
   - Connect switch to Raspberry Pi via Ethernet
   - Configure switch to connect to controller IP

### Performance Optimization

For Raspberry Pi 4, consider:

1. **Overclocking** (optional):
   ```bash
   # Edit /boot/config.txt
   sudo nano /boot/config.txt
   # Add: over_voltage=2, arm_freq=2000
   ```

2. **Swap space**:
   ```bash
   sudo dphys-swapfile swapoff
   sudo nano /etc/dphys-swapfile
   # Set CONF_SWAPSIZE=2048
   sudo dphys-swapfile setup
   sudo dphys-swapfile swapon
   ```

3. **Disable unnecessary services**:
   ```bash
   sudo systemctl disable bluetooth
   sudo systemctl disable avahi-daemon
   ```

## Monitoring

### Check System Status

```bash
# Check service status
sudo systemctl status zero-trust-sdn.service

# Check Docker containers
docker ps

# Check logs
tail -f logs/zero_trust.log
```

### Access Dashboard

The web dashboard should be accessible at:
```
http://<raspberry-pi-ip>:5000
```

## Troubleshooting

### Common Issues

1. **Docker not starting**:
   ```bash
   sudo systemctl restart docker
   ```

2. **Ryu controller not connecting**:
   - Check firewall rules
   - Verify switch configuration
   - Check controller IP address

3. **High CPU usage**:
   - Reduce honeypot logging verbosity
   - Adjust polling intervals
   - Disable unnecessary features

4. **Certificate errors**:
   ```bash
   # Regenerate CA
   rm -rf certs/*
   python3 -c "from identity_manager.certificate_manager import CertificateManager; cm = CertificateManager(); print('CA created')"
   ```

## Maintenance

### Regular Tasks

1. **Update system**:
   ```bash
   sudo apt update && sudo apt upgrade
   ```

2. **Backup database**:
   ```bash
   cp identity.db backups/identity_$(date +%Y%m%d).db
   ```

3. **Clean logs**:
   ```bash
   find logs/ -name "*.log" -mtime +30 -delete
   ```

## Performance Benchmarks

Expected performance on Raspberry Pi 4:

- Flow processing: ~1000 flows/second
- Device onboarding: < 5 seconds
- Trust score calculation: < 100ms
- Policy adaptation: < 500ms
- Honeypot log parsing: ~100 entries/second

## Security Considerations

1. **Change default passwords**
2. **Enable firewall**:
   ```bash
   sudo ufw enable
   sudo ufw allow 5000/tcp  # Dashboard
   sudo ufw allow 6653/tcp   # OpenFlow
   ```

3. **Use SSH keys** instead of passwords
4. **Regular security updates**
5. **Monitor system logs**

## Support

For issues or questions:
- Check logs in `logs/` directory
- Review documentation in `docs/`
- Run integration tests: `python3 -m pytest integration_test/`

