# 🚨 DDoS Attack Simulator for ML Testing

## Overview

This script simulates various types of DDoS attacks to test the ML-based attack detection system. It sends malicious traffic patterns that should trigger the ML engine's detection algorithms.

## Attack Types

### 1. **Volume Attack** (`--attack volume`)
- Sends large packets (1000-1500 bytes)
- Simulates bandwidth exhaustion
- **Usage**: `python3 ddos_attack_simulator.py --attack volume --intensity high`

### 2. **Rate Attack** (`--attack rate`)
- Sends packets at high frequency
- Simulates packet flooding
- **Usage**: `python3 ddos_attack_simulator.py --attack rate --intensity medium`

### 3. **Protocol Attack** (`--attack protocol`)
- Sends packets with unusual protocol characteristics
- Simulates SYN flood attacks
- **Usage**: `python3 ddos_attack_simulator.py --attack protocol --intensity low`

### 4. **Amplification Attack** (`--attack amplification`)
- Sends packets with spoofed sources
- Simulates DNS/NTP amplification attacks
- **Usage**: `python3 ddos_attack_simulator.py --attack amplification --intensity high`

### 5. **Mixed Attack** (`--attack mixed`)
- Combines multiple attack techniques
- Alternates between different attack types
- **Usage**: `python3 ddos_attack_simulator.py --attack mixed --duration 60`

### 6. **Stealth Attack** (`--attack stealth`)
- Gradually increases attack intensity
- Simulates slow-start attacks
- **Usage**: `python3 ddos_attack_simulator.py --attack stealth --duration 120`

## Usage Examples

### Basic Volume Attack
```bash
python3 ddos_attack_simulator.py --attack volume --duration 30 --intensity medium
```

### High-Intensity Rate Attack
```bash
python3 ddos_attack_simulator.py --attack rate --duration 45 --intensity high
```

### Stealth Attack (Hard to Detect)
```bash
python3 ddos_attack_simulator.py --attack stealth --duration 120 --intensity low
```

### Mixed Attack (Multiple Techniques)
```bash
python3 ddos_attack_simulator.py --attack mixed --duration 60
```

### Custom Target
```bash
python3 ddos_attack_simulator.py --target http://192.168.1.100:5000 --attack volume
```

## Parameters

- `--target`: Target URL (default: http://localhost:5000)
- `--device`: Device ID (default: ESP32_ATTACKER)
- `--attack`: Attack type (volume, rate, protocol, amplification, mixed, stealth)
- `--duration`: Attack duration in seconds (default: 30)
- `--intensity`: Attack intensity (low, medium, high)

## What the Script Does

1. **Authentication**: Authenticates as a malicious device
2. **Normal Traffic**: Sends normal traffic for 5 seconds
3. **Attack Phase**: Executes the specified attack type
4. **ML Monitoring**: Checks ML engine detections before and after
5. **Results**: Shows attack summary and detection results

## Expected ML Detection

The ML engine should detect:
- ✅ **Volume Attacks**: Large packet sizes
- ✅ **Rate Attacks**: High packet frequency
- ✅ **Protocol Attacks**: Unusual protocol patterns
- ✅ **Amplification Attacks**: Spoofed sources
- ✅ **Mixed Attacks**: Combination of patterns
- ⚠️ **Stealth Attacks**: May be harder to detect initially

## Testing Scenarios

### Scenario 1: Quick Detection Test
```bash
python3 ddos_attack_simulator.py --attack volume --duration 15 --intensity high
```

### Scenario 2: Gradual Attack Test
```bash
python3 ddos_attack_simulator.py --attack stealth --duration 60 --intensity low
```

### Scenario 3: Complex Attack Test
```bash
python3 ddos_attack_simulator.py --attack mixed --duration 90
```

## Monitoring Results

After running the attack, check:

1. **Dashboard**: Open http://localhost:5000 → ML Engine tab
2. **API**: `curl http://localhost:5000/ml/detections`
3. **Logs**: Check terminal output for detection messages

## Safety Notes

- This script is for **testing purposes only**
- Only use against your own test environment
- The attacks are simulated and won't cause real damage
- Stop the attack with `Ctrl+C` if needed

## Troubleshooting

### If ML Engine Doesn't Detect Attacks:

1. **Check ML Model**: Ensure model is loaded properly
2. **Increase Intensity**: Try `--intensity high`
3. **Longer Duration**: Try `--duration 60`
4. **Check Logs**: Look for ML engine error messages
5. **Verify API**: Test `/ml/status` endpoint

### If Authentication Fails:

1. **Check Controller**: Ensure Flask controller is running
2. **Check Port**: Verify port 5000 is accessible
3. **Check Network**: Ensure localhost connectivity

## Integration with Dashboard

The attack simulator integrates with the dashboard to show:
- Real-time attack detection
- Attack statistics and metrics
- Detailed attacker information
- ML model confidence levels
- Attack type classification
