# 🎉 IoT Security Framework - Complete Single Script Solution

## ✅ What's Been Created

I've created a comprehensive single-script solution to run your entire IoT Security Framework project:

### 📁 New Files Created:

1. **`run_iot_framework.py`** - Main Python launcher script
2. **`start.sh`** - Simple bash wrapper script  
3. **`LAUNCHER_README.md`** - Comprehensive documentation

## 🚀 How to Use

### Single Command to Run Everything:
```bash
python3 run_iot_framework.py
```

**OR**

```bash
./start.sh
```

## 🔧 What the Launcher Does Automatically:

1. **System Checks**
   - ✅ Verifies Python 3.8+ is installed
   - ✅ Checks for required project files
   - ✅ Validates ML model files exist

2. **Environment Setup**
   - ✅ Creates virtual environment (if needed)
   - ✅ Installs all dependencies from `requirements.txt`
   - ✅ Sets up proper Python paths

3. **Component Startup**
   - ✅ Starts Flask SDN Controller with ML engine
   - ✅ Launches virtual ESP32 devices simulation
   - ✅ Initializes network topology
   - ✅ Waits for all components to be ready

4. **Monitoring & Status**
   - ✅ Checks system health every 30 seconds
   - ✅ Displays real-time statistics
   - ✅ Shows connected devices and packet counts
   - ✅ Monitors ML engine status

5. **User Interface**
   - ✅ Provides dashboard access URL
   - ✅ Shows API endpoints documentation
   - ✅ Displays usage instructions
   - ✅ Handles graceful shutdown (Ctrl+C)

## 🌐 Access Your Dashboard

Once the launcher starts everything, open your browser to:
```
http://localhost:5000
```

## 📊 Dashboard Features Available:

- **Overview Tab**: Real-time network status and topology
- **Devices Tab**: Connected ESP32 devices and controls  
- **Security Tab**: SDN policies and security alerts
- **ML Engine Tab**: Attack detection and ML statistics (NEWLY REDESIGNED)
- **Analytics Tab**: Network performance metrics

## 🛑 Stopping the Framework

Simply press `Ctrl+C` and the launcher will:
- ✅ Stop virtual devices gracefully
- ✅ Shutdown the controller properly
- ✅ Clean up all processes
- ✅ Display confirmation message

## 🔍 Current System Status

Based on the terminal logs, your system is already running perfectly:
- ✅ **Flask Controller**: Active on port 5000
- ✅ **ML Engine**: Processing packets continuously
- ✅ **API Endpoints**: All responding (200 status codes)
- ✅ **Real-time Updates**: Every 5 seconds
- ✅ **Virtual Devices**: Connected and sending data

## 🎯 Benefits of the Single Script:

1. **One Command**: Start everything with a single command
2. **Automatic Setup**: No manual dependency installation
3. **Health Monitoring**: Continuous system status checks
4. **Graceful Shutdown**: Clean process termination
5. **Error Handling**: Comprehensive error checking and reporting
6. **User Friendly**: Clear status messages and instructions
7. **Cross Platform**: Works on Linux, macOS, and Windows

## 📋 Quick Start Summary:

```bash
# Navigate to project directory
cd /home/cdrditgis/Documents/IOT-project

# Run the complete framework
python3 run_iot_framework.py

# Open browser to dashboard
# http://localhost:5000

# Stop with Ctrl+C when done
```

## 🎉 Your IoT Security Framework is Ready!

The single script launcher makes it incredibly easy to run your entire IoT Security Framework. Everything is automated - from dependency installation to component startup to health monitoring. Just run one command and you'll have a fully functional IoT security system with ML-based attack detection running!
