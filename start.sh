#!/bin/bash

# Zero Trust SDN Framework - Complete System Startup Script
# Automatically starts all components of the Zero Trust SDN Framework
# Works on fresh Ubuntu installations - installs all dependencies automatically

# Parse command line arguments
NO_ML=false
NO_MININET=false
WITH_MININET=false

for arg in "$@"; do
    case $arg in
        --no-ml)
            NO_ML=true
            shift
            ;;
        --no-mininet)
            NO_MININET=true
            shift
            ;;
        --with-mininet)
            WITH_MININET=true
            shift
            ;;
        --help|-h)
            echo "Usage: ./start.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --no-ml        Skip TensorFlow/ML installation (faster startup)"
            echo "  --no-mininet   Skip virtual IoT devices (Mininet)"
            echo "  --with-mininet Start virtual IoT devices automatically"
            echo "  --help, -h     Show this help message"
            exit 0
            ;;
    esac
done

# Don't exit on error for process checks
set +e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Process IDs
CONTROLLER_PID=""
RYU_PID=""
ZERO_TRUST_PID=""
MININET_PID=""
HONEYPOT_CONTAINER=""

# Status flags to prevent repeated warnings
CONTROLLER_STOPPED_REPORTED="false"
RYU_STOPPED_REPORTED="false"
ZERO_TRUST_STOPPED_REPORTED="false"
MININET_STOPPED_REPORTED="false"

# Cleanup function
cleanup() {
    echo ""
    echo -e "${YELLOW}Shutting down Zero Trust SDN Framework...${NC}"
    
    # Kill all processes
    if [ ! -z "$CONTROLLER_PID" ]; then
        echo "   Stopping Flask controller (PID: $CONTROLLER_PID)..."
        kill $CONTROLLER_PID 2>/dev/null || true
    fi
    
    if [ ! -z "$RYU_PID" ]; then
        echo "   Stopping Ryu SDN controller (PID: $RYU_PID)..."
        kill $RYU_PID 2>/dev/null || true
    fi
    
    if [ ! -z "$ZERO_TRUST_PID" ]; then
        echo "   Stopping Zero Trust framework (PID: $ZERO_TRUST_PID)..."
        kill $ZERO_TRUST_PID 2>/dev/null || true
    fi
    
    if [ ! -z "$MININET_PID" ] && kill -0 $MININET_PID 2>/dev/null; then
        echo "   Stopping Mininet topology (PID: $MININET_PID)..."
        kill $MININET_PID 2>/dev/null || true
        sudo mn -c 2>/dev/null || true
    fi
    
    # Stop honeypot container if it was started by this script
    if [ ! -z "$HONEYPOT_CONTAINER" ] && command -v docker &> /dev/null; then
        echo "   Stopping honeypot container..."
        docker stop "$HONEYPOT_CONTAINER" 2>/dev/null || true
    fi
    
    # Wait for processes to terminate
    sleep 2
    
    # Force kill if still running
    pkill -f "controller.py" 2>/dev/null || true
    pkill -f "ryu-manager" 2>/dev/null || true
    pkill -f "zero_trust_integration.py" 2>/dev/null || true
    pkill -f "mininet_topology.py" 2>/dev/null || true
    pkill -f "mininet" 2>/dev/null || true
    sudo mn -c 2>/dev/null || true
    
    echo -e "${GREEN}All components stopped${NC}"
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Banner
echo ""
echo -e "${BLUE}======================================================================${NC}"
echo -e "${BLUE}       Zero Trust SDN Framework - Complete System Startup            ${NC}"
echo -e "${BLUE}======================================================================${NC}"
echo -e "${BLUE}  * Flask Controller (Web Dashboard & API)                           ${NC}"
echo -e "${BLUE}  * Ryu SDN Controller (OpenFlow Policy Enforcement)                 ${NC}"
echo -e "${BLUE}  * Zero Trust Integration Framework                                 ${NC}"
echo -e "${BLUE}  * ML-Based DDoS Detection (TensorFlow/Keras)                       ${NC}"
echo -e "${BLUE}  * Honeypot Management (Suspicious Device Redirection)              ${NC}"
echo -e "${BLUE}  * Dashboard Alerts & Threat Intelligence                           ${NC}"
echo -e "${BLUE}======================================================================${NC}"
echo ""

# Check if we're in the right directory
if [ ! -f "controller.py" ]; then
    echo -e "${RED}Error: controller.py not found. Please run this script from the project directory${NC}"
    exit 1
fi

# Get the project directory
PROJECT_DIR=$(pwd)

# ============================================================================
# SYSTEM DEPENDENCIES INSTALLATION
# ============================================================================
install_system_deps() {
    echo -e "${BLUE}Checking system dependencies...${NC}"
    
    # Check if apt-get is available (Ubuntu/Debian)
    if ! command -v apt-get &> /dev/null; then
        echo -e "${YELLOW}Warning: apt-get not found. Assuming dependencies are installed.${NC}"
        return 0
    fi
    
    PACKAGES_TO_INSTALL=""
    NEED_UPDATE=false
    
    # Check for Python3
    if ! command -v python3 &> /dev/null; then
        PACKAGES_TO_INSTALL="$PACKAGES_TO_INSTALL python3"
        NEED_UPDATE=true
    fi
    
    # Check for pip
    if ! command -v pip3 &> /dev/null && ! python3 -m pip --version &> /dev/null 2>&1; then
        PACKAGES_TO_INSTALL="$PACKAGES_TO_INSTALL python3-pip"
        NEED_UPDATE=true
    fi
    
    # Check for python3-venv
    if ! python3 -m venv --help &> /dev/null 2>&1; then
        PACKAGES_TO_INSTALL="$PACKAGES_TO_INSTALL python3-venv"
        NEED_UPDATE=true
    fi
    
    # Development dependencies for building Python packages
    if ! dpkg -s python3-dev &> /dev/null 2>&1; then
        PACKAGES_TO_INSTALL="$PACKAGES_TO_INSTALL python3-dev"
        NEED_UPDATE=true
    fi
    
    if ! dpkg -s build-essential &> /dev/null 2>&1; then
        PACKAGES_TO_INSTALL="$PACKAGES_TO_INSTALL build-essential"
        NEED_UPDATE=true
    fi
    
    if ! dpkg -s libffi-dev &> /dev/null 2>&1; then
        PACKAGES_TO_INSTALL="$PACKAGES_TO_INSTALL libffi-dev"
        NEED_UPDATE=true
    fi
    
    if ! dpkg -s libssl-dev &> /dev/null 2>&1; then
        PACKAGES_TO_INSTALL="$PACKAGES_TO_INSTALL libssl-dev"
        NEED_UPDATE=true
    fi
    
    # Network tools
    if ! command -v netstat &> /dev/null && ! command -v ss &> /dev/null; then
        PACKAGES_TO_INSTALL="$PACKAGES_TO_INSTALL net-tools"
        NEED_UPDATE=true
    fi
    
    if ! command -v curl &> /dev/null; then
        PACKAGES_TO_INSTALL="$PACKAGES_TO_INSTALL curl"
        NEED_UPDATE=true
    fi
    
    if [ "$NEED_UPDATE" = true ]; then
        echo -e "${YELLOW}Installing system packages:${NC} $PACKAGES_TO_INSTALL"
        sudo apt-get update -qq
        sudo apt-get install -y $PACKAGES_TO_INSTALL
        echo -e "${GREEN}System packages installed${NC}"
    else
        echo -e "${GREEN}All system dependencies already installed${NC}"
    fi
}

# Run system dependencies installation
install_system_deps

# ============================================================================
# PYTHON ENVIRONMENT SETUP
# ============================================================================

# Determine pip command
get_pip_cmd() {
    if [ -d "venv" ] && [ -f "./venv/bin/pip" ]; then
        echo "./venv/bin/pip"
    elif [ -d "venv" ] && [ -f "./venv/bin/pip3" ]; then
        echo "./venv/bin/pip3"
    elif command -v pip3 &> /dev/null; then
        echo "pip3"
    elif command -v pip &> /dev/null; then
        echo "pip"
    elif python3 -m pip --version &> /dev/null 2>&1; then
        echo "python3 -m pip"
    else
        echo ""
    fi
}

# Check/create virtual environment
setup_venv() {
    echo -e "${BLUE}Setting up Python environment...${NC}"
    
    if [ -d "venv" ]; then
        echo -e "${GREEN}Virtual environment found${NC}"
        PYTHON_CMD="./venv/bin/python3"
        if [ ! -f "$PYTHON_CMD" ]; then
            PYTHON_CMD="python3"
        fi
    else
        echo -e "${YELLOW}Creating virtual environment...${NC}"
        python3 -m venv venv
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}Virtual environment created${NC}"
            PYTHON_CMD="./venv/bin/python3"
        else
            echo -e "${YELLOW}Could not create venv, using system Python${NC}"
            PYTHON_CMD="python3"
        fi
    fi
    
    # Upgrade pip in venv
    if [ -d "venv" ]; then
        ./venv/bin/pip install --upgrade pip --quiet 2>/dev/null || true
    fi
}

setup_venv

# Python version check
PYTHON_VERSION=$($PYTHON_CMD -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo -e "${GREEN}Python version: $PYTHON_VERSION${NC}"

# ============================================================================
# PYTHON DEPENDENCIES INSTALLATION
# ============================================================================

install_python_deps() {
    echo -e "${BLUE}Installing Python dependencies...${NC}"
    
    pip_cmd=$(get_pip_cmd)
    
    if [ -z "$pip_cmd" ]; then
        echo -e "${RED}Error: pip not found. Cannot install dependencies.${NC}"
        exit 1
    fi
    
    # Determine if we should use --user flag (only if not in venv)
    user_flag=""
    if [ ! -d "venv" ]; then
        user_flag="--user"
    fi
    
    # First, fix any broken PIL/Pillow installation
    if ! $PYTHON_CMD -c "from PIL import Image" 2>/dev/null; then
        echo -e "${YELLOW}   Fixing PIL/Pillow installation...${NC}"
        $pip_cmd uninstall -y pillow PIL 2>/dev/null || true
        $pip_cmd install $user_flag --upgrade pillow --quiet 2>/dev/null || true
    fi
    
    # Install core dependencies first (fast, required)
    echo -e "${YELLOW}   Installing core dependencies...${NC}"
    $pip_cmd install $user_flag --upgrade Flask requests cryptography pyOpenSSL --quiet 2>/dev/null
    
    # Install Ryu and eventlet with compatible version (critical)
    echo -e "${YELLOW}   Installing Ryu SDN Controller...${NC}"
    $pip_cmd install $user_flag ryu eventlet==0.30.2 --quiet 2>/dev/null
    
    # Install other dependencies
    echo -e "${YELLOW}   Installing remaining dependencies...${NC}"
    $pip_cmd install $user_flag matplotlib numpy pandas scikit-learn dnspython --quiet 2>/dev/null
    
    # Install TensorFlow (optional, large package)
    if [ "$NO_ML" = false ]; then
        echo -e "${YELLOW}   Installing TensorFlow (this may take a while)...${NC}"
        $pip_cmd install $user_flag tensorflow --quiet 2>/dev/null
        if $PYTHON_CMD -c "import tensorflow" 2>/dev/null; then
            echo -e "${GREEN}   TensorFlow installed${NC}"
        else
            echo -e "${YELLOW}   TensorFlow installation failed (ML will use fallback heuristics)${NC}"
        fi
    else
        echo -e "${YELLOW}   Skipping TensorFlow (--no-ml flag)${NC}"
    fi
    
    # Install Docker SDK (optional)
    echo -e "${YELLOW}   Installing Docker SDK...${NC}"
    $pip_cmd install $user_flag docker --quiet 2>/dev/null || true
    
    # Install test dependencies
    $pip_cmd install $user_flag pytest pytest-cov --quiet 2>/dev/null || true
    
    echo -e "${GREEN}Python dependencies installed${NC}"
}

install_python_deps

# ============================================================================
# DEPENDENCY VERIFICATION
# ============================================================================

echo ""
echo -e "${BLUE}Verifying dependencies...${NC}"

# Check Flask (required)
if $PYTHON_CMD -c "import flask" 2>/dev/null; then
    echo -e "${GREEN}  Flask${NC}"
else
    echo -e "${RED}  Flask NOT FOUND (required)${NC}"
    exit 1
fi

# Check TensorFlow/Keras (optional)
TENSORFLOW_AVAILABLE=false
if $PYTHON_CMD -c "import tensorflow" 2>/dev/null; then
    TENSORFLOW_AVAILABLE=true
    echo -e "${GREEN}  TensorFlow/Keras (ML model support)${NC}"
else
    echo -e "${YELLOW}  TensorFlow/Keras not available (using fallback heuristics)${NC}"
fi

# Check cryptography (required for Zero Trust)
CRYPTOGRAPHY_AVAILABLE=false
if $PYTHON_CMD -c "import cryptography" 2>/dev/null; then
    CRYPTOGRAPHY_AVAILABLE=true
    echo -e "${GREEN}  cryptography${NC}"
else
    echo -e "${YELLOW}  cryptography not available${NC}"
fi

# Check Ryu (required)
RYU_AVAILABLE=false
if $PYTHON_CMD -c "import ryu" 2>/dev/null; then
    RYU_AVAILABLE=true
    echo -e "${GREEN}  Ryu SDN Controller${NC}"
else
    echo -e "${RED}  Ryu SDN Controller NOT FOUND (required)${NC}"
    echo -e "${RED}  Please install manually: pip3 install ryu eventlet==0.30.2${NC}"
    exit 1
fi

# Check Docker (optional)
DOCKER_AVAILABLE=false
DOCKER_RUNNING=false
if command -v docker &> /dev/null; then
    if docker info > /dev/null 2>&1; then
        DOCKER_RUNNING=true
        if $PYTHON_CMD -c "import docker" 2>/dev/null; then
            DOCKER_AVAILABLE=true
            echo -e "${GREEN}  Docker (honeypot support enabled)${NC}"
        else
            echo -e "${YELLOW}  Docker command found but Python module missing${NC}"
        fi
    else
        echo -e "${YELLOW}  Docker installed but daemon not running${NC}"
    fi
else
    echo -e "${YELLOW}  Docker not found (honeypot features unavailable)${NC}"
fi

# ============================================================================
# DIRECTORY SETUP
# ============================================================================

echo ""
echo -e "${BLUE}Setting up directories...${NC}"
mkdir -p certs honeypot_data logs data/models

# Fix permissions if running as root
if [ "$EUID" -eq 0 ] && [ ! -z "$SUDO_USER" ]; then
    chown -R $SUDO_USER:$SUDO_USER certs honeypot_data logs data 2>/dev/null || true
fi

echo -e "${GREEN}Directories ready${NC}"

# Check for ML model
if [ -d "data/models/ddos_model_retrained" ] || [ -f "data/models/ddos_model_retrained.keras" ]; then
    echo -e "${GREEN}ML model found${NC}"
else
    echo -e "${YELLOW}ML model not found (using fallback heuristic detection)${NC}"
fi

# ============================================================================
# START FLASK CONTROLLER
# ============================================================================

echo ""
echo -e "${BLUE}Starting Flask Controller...${NC}"

# Check if port 5000 is already in use
if command -v lsof &> /dev/null; then
    EXISTING_PID=$(lsof -ti:5000 2>/dev/null)
    if [ ! -z "$EXISTING_PID" ]; then
        echo -e "${YELLOW}Port 5000 in use (PID: $EXISTING_PID), stopping...${NC}"
        kill $EXISTING_PID 2>/dev/null || true
        sleep 2
    fi
fi

# Kill any existing controller.py processes
pkill -f "controller.py" 2>/dev/null || true
sleep 1

nohup $PYTHON_CMD controller.py > logs/controller.log 2>&1 &
CONTROLLER_PID=$!
echo -e "${GREEN}Flask Controller started (PID: $CONTROLLER_PID)${NC}"

# Wait for controller to be ready
echo -e "${YELLOW}Waiting for controller to initialize...${NC}"
CONTROLLER_READY=false

for i in {1..40}; do
    # Check if process is still running
    if ! kill -0 $CONTROLLER_PID 2>/dev/null; then
        echo ""
        echo -e "${RED}Controller process died!${NC}"
        echo -e "${YELLOW}Check logs/controller.log for errors:${NC}"
        tail -30 logs/controller.log 2>/dev/null || echo "   (log file not found)"
        cleanup
        exit 1
    fi
    
    # Check if controller is responding
    if command -v curl &> /dev/null; then
        HTTP_CODE=$(curl -s -o /dev/null -w '%{http_code}' --connect-timeout 2 --max-time 3 http://localhost:5000 2>/dev/null)
        if [ "$HTTP_CODE" = "200" ]; then
            echo ""
            echo -e "${GREEN}Controller is ready!${NC}"
            CONTROLLER_READY=true
            break
        fi
    fi
    
    sleep 1
    if [ $((i % 5)) -eq 0 ]; then
        echo -n " [${i}s]"
    else
        echo -n "."
    fi
done

if [ "$CONTROLLER_READY" = false ]; then
    echo ""
    echo -e "${YELLOW}Controller not responding after 40 seconds, continuing anyway...${NC}"
fi

# ============================================================================
# START RYU SDN CONTROLLER
# ============================================================================

if [ "$RYU_AVAILABLE" = true ]; then
    echo ""
    echo -e "${BLUE}Starting Ryu SDN Controller...${NC}"
    
    # Check if Ryu module file exists
    if [ ! -f "ryu_controller/sdn_policy_engine.py" ]; then
        echo -e "${RED}Ryu controller file not found: ryu_controller/sdn_policy_engine.py${NC}"
        exit 1
    fi
    
    # Set PYTHONPATH to include project root for imports
    export PYTHONPATH="${PYTHONPATH}:$(pwd)"
    
    if command -v ryu-manager &> /dev/null; then
        ryu-manager --ofp-tcp-listen-port 6653 --verbose ryu_controller.sdn_policy_engine > logs/ryu.log 2>&1 &
        RYU_PID=$!
    else
        $PYTHON_CMD -m ryu.app.simple_switch_13 ryu_controller.sdn_policy_engine > logs/ryu.log 2>&1 &
        RYU_PID=$!
    fi
    
    # Wait for Ryu to start
    echo -e "${YELLOW}Waiting for Ryu to initialize...${NC}"
    RYU_READY=false
    for i in {1..20}; do
        if kill -0 $RYU_PID 2>/dev/null; then
            if command -v netstat &> /dev/null; then
                if netstat -tuln 2>/dev/null | grep -q ":6653 "; then
                    RYU_READY=true
                    break
                fi
            elif command -v ss &> /dev/null; then
                if ss -tuln 2>/dev/null | grep -q ":6653 "; then
                    RYU_READY=true
                    break
                fi
            else
                sleep 2
                if kill -0 $RYU_PID 2>/dev/null; then
                    RYU_READY=true
                    break
                fi
            fi
        else
            echo -e "${RED}Ryu SDN Controller process died${NC}"
            echo -e "${YELLOW}Check logs/ryu.log for errors:${NC}"
            tail -20 logs/ryu.log 2>/dev/null || echo "   (log file not found)"
            exit 1
        fi
        sleep 1
        echo -n "."
    done
    
    if [ "$RYU_READY" = true ]; then
        echo ""
        echo -e "${GREEN}Ryu SDN Controller started (PID: $RYU_PID)${NC}"
    else
        echo ""
        echo -e "${RED}Ryu SDN Controller failed to start${NC}"
        exit 1
    fi
else
    echo -e "${RED}Ryu SDN Controller is required but not available${NC}"
    exit 1
fi

# ============================================================================
# START ZERO TRUST FRAMEWORK
# ============================================================================

echo ""
echo -e "${BLUE}Starting Zero Trust Integration Framework...${NC}"
if [ -f "zero_trust_integration.py" ]; then
    if [ "$CRYPTOGRAPHY_AVAILABLE" = true ]; then
        sleep 2
        $PYTHON_CMD zero_trust_integration.py > logs/zero_trust.log 2>&1 &
        ZERO_TRUST_PID=$!
        sleep 3
        if kill -0 $ZERO_TRUST_PID 2>/dev/null; then
            echo -e "${GREEN}Zero Trust Framework started (PID: $ZERO_TRUST_PID)${NC}"
        else
            echo -e "${YELLOW}Zero Trust Framework failed to start${NC}"
            echo -e "${YELLOW}Check logs/zero_trust.log for errors${NC}"
            ZERO_TRUST_PID=""
        fi
    else
        echo -e "${YELLOW}Skipping Zero Trust Framework (cryptography not installed)${NC}"
    fi
else
    echo -e "${YELLOW}Zero Trust integration file not found, skipping${NC}"
fi

# ============================================================================
# CHECK HONEYPOT STATUS
# ============================================================================

if [ "$DOCKER_AVAILABLE" = true ] && [ "$DOCKER_RUNNING" = true ]; then
    echo ""
    echo -e "${BLUE}Checking Honeypot Status...${NC}"
    sleep 2
    
    if docker ps --format "{{.Names}}" 2>/dev/null | grep -q "iot_honeypot"; then
        HONEYPOT_CONTAINER=$(docker ps --format "{{.Names}}" 2>/dev/null | grep "iot_honeypot" | head -1)
        echo -e "${GREEN}Honeypot container running: $HONEYPOT_CONTAINER${NC}"
    else
        echo -e "${YELLOW}Honeypot will be deployed on demand${NC}"
    fi
fi

# ============================================================================
# START MININET (OPTIONAL)
# ============================================================================

if [ -f "mininet_topology.py" ]; then
    if [ "$WITH_MININET" = true ]; then
        echo ""
        echo -e "${BLUE}Starting Virtual IoT Devices...${NC}"
        $PYTHON_CMD mininet_topology.py > logs/mininet.log 2>&1 &
        MININET_PID=$!
        echo -e "${GREEN}Virtual devices started (PID: $MININET_PID)${NC}"
    elif [ "$NO_MININET" = false ]; then
        echo ""
        echo -e "${YELLOW}Virtual IoT devices available. Use --with-mininet to start them.${NC}"
    fi
fi

# ============================================================================
# DISPLAY STATUS
# ============================================================================

echo ""
echo -e "${GREEN}======================================================================${NC}"
echo -e "${GREEN}                    System Started Successfully!                      ${NC}"
echo -e "${GREEN}======================================================================${NC}"
echo ""
echo -e "${BLUE}System Status:${NC}"
echo -e "   ${GREEN}*${NC} Flask Controller:     http://localhost:5000 (PID: $CONTROLLER_PID)"
if [ ! -z "$RYU_PID" ]; then
    echo -e "   ${GREEN}*${NC} Ryu SDN Controller:   Running (PID: $RYU_PID)"
fi
if [ ! -z "$ZERO_TRUST_PID" ]; then
    echo -e "   ${GREEN}*${NC} Zero Trust Framework: Running (PID: $ZERO_TRUST_PID)"
fi
if [ "$DOCKER_AVAILABLE" = true ] && [ "$DOCKER_RUNNING" = true ]; then
    if [ ! -z "$HONEYPOT_CONTAINER" ]; then
        echo -e "   ${GREEN}*${NC} Honeypot:             Running ($HONEYPOT_CONTAINER)"
    else
        echo -e "   ${YELLOW}*${NC} Honeypot:             Available (on demand)"
    fi
fi
if [ ! -z "$MININET_PID" ]; then
    echo -e "   ${GREEN}*${NC} Virtual Devices:      Running (PID: $MININET_PID)"
fi

echo ""
echo -e "${BLUE}Access Points:${NC}"
echo -e "   * Web Dashboard:    ${GREEN}http://localhost:5000${NC}"
echo -e "   * API Endpoints:    ${GREEN}http://localhost:5000/api/*${NC}"
if [ ! -z "$RYU_PID" ]; then
    echo -e "   * SDN Controller:   ${GREEN}Port 6653 (OpenFlow)${NC}"
fi

echo ""
echo -e "${BLUE}Log Files:${NC}"
echo -e "   * Controller:       ${YELLOW}logs/controller.log${NC}"
if [ ! -z "$RYU_PID" ]; then
    echo -e "   * Ryu:              ${YELLOW}logs/ryu.log${NC}"
fi
if [ ! -z "$ZERO_TRUST_PID" ]; then
    echo -e "   * Zero Trust:       ${YELLOW}logs/zero_trust.log${NC}"
fi

echo ""
echo -e "${YELLOW}Press Ctrl+C to stop all components${NC}"
echo ""
echo -e "${GREEN}System is running... Monitoring components...${NC}"
echo ""

# ============================================================================
# MONITOR PROCESSES
# ============================================================================

while true; do
    sleep 10
    
    # Check if controller is still running
    if [ ! -z "$CONTROLLER_PID" ] && ! kill -0 $CONTROLLER_PID 2>/dev/null; then
        if [ "$CONTROLLER_STOPPED_REPORTED" != "true" ]; then
            echo ""
            echo -e "${RED}Flask Controller stopped unexpectedly!${NC}"
            echo -e "${YELLOW}Attempting to restart...${NC}"
            
            # Try to restart the controller
            nohup $PYTHON_CMD controller.py > logs/controller.log 2>&1 &
            CONTROLLER_PID=$!
            sleep 3
            if kill -0 $CONTROLLER_PID 2>/dev/null; then
                echo -e "${GREEN}Flask Controller restarted (PID: $CONTROLLER_PID)${NC}"
            else
                echo -e "${RED}Failed to restart Flask Controller${NC}"
                CONTROLLER_STOPPED_REPORTED="true"
                cleanup
                exit 1
            fi
        fi
    fi
    
    # Check Ryu
    if [ ! -z "$RYU_PID" ] && ! kill -0 $RYU_PID 2>/dev/null; then
        if [ "$RYU_STOPPED_REPORTED" != "true" ]; then
            echo ""
            echo -e "${RED}Ryu SDN Controller stopped unexpectedly!${NC}"
            RYU_STOPPED_REPORTED="true"
            echo -e "${YELLOW}Attempting to restart Ryu...${NC}"
            export PYTHONPATH="${PYTHONPATH}:$(pwd)"
            if command -v ryu-manager &> /dev/null; then
                ryu-manager --ofp-tcp-listen-port 6653 --verbose ryu_controller.sdn_policy_engine >> logs/ryu.log 2>&1 &
                RYU_PID=$!
                sleep 3
                if kill -0 $RYU_PID 2>/dev/null; then
                    echo -e "${GREEN}Ryu SDN Controller restarted (PID: $RYU_PID)${NC}"
                    RYU_STOPPED_REPORTED="false"
                fi
            fi
        fi
    fi
    
    # Check Zero Trust
    if [ ! -z "$ZERO_TRUST_PID" ] && ! kill -0 $ZERO_TRUST_PID 2>/dev/null; then
        if [ "$ZERO_TRUST_STOPPED_REPORTED" != "true" ]; then
            echo ""
            echo -e "${YELLOW}Zero Trust Framework stopped unexpectedly${NC}"
            ZERO_TRUST_STOPPED_REPORTED="true"
        fi
        ZERO_TRUST_PID=""
    fi
    
    # Check Mininet
    if [ ! -z "$MININET_PID" ] && ! kill -0 $MININET_PID 2>/dev/null; then
        if [ "$MININET_STOPPED_REPORTED" != "true" ]; then
            echo ""
            echo -e "${YELLOW}Virtual Devices (Mininet) stopped unexpectedly${NC}"
            MININET_STOPPED_REPORTED="true"
        fi
        MININET_PID=""
    fi
    
    # Check honeypot container status
    if [ "$DOCKER_AVAILABLE" = true ] && [ "$DOCKER_RUNNING" = true ]; then
        if [ ! -z "$HONEYPOT_CONTAINER" ]; then
            if ! docker ps --format "{{.Names}}" 2>/dev/null | grep -q "$HONEYPOT_CONTAINER"; then
                HONEYPOT_CONTAINER=""
            fi
        else
            NEW_CONTAINER=$(docker ps --format "{{.Names}}" 2>/dev/null | grep "iot_honeypot" | head -1)
            if [ ! -z "$NEW_CONTAINER" ]; then
                HONEYPOT_CONTAINER="$NEW_CONTAINER"
            fi
        fi
    fi
done
