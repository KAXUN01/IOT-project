#!/bin/bash

# IoT Security Framework - Quick Start Script
# Simple bash script to run the complete IoT Security Framework

echo "🔐 Starting IoT Security Framework..."
echo "======================================"

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed"
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "controller.py" ]; then
    echo "❌ Error: controller.py not found. Please run this script from the project directory"
    exit 1
fi

# Run the Python launcher
echo "🚀 Launching IoT Security Framework..."
python3 run_iot_framework.py

echo "✅ IoT Security Framework stopped"
