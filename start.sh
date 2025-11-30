#!/bin/bash

# Zero Trust SDN Framework - Complete System Startup Script
# Automatically starts all components of the Zero Trust SDN Framework

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

# Cleanup function
cleanup() {
    echo ""
    echo -e "${YELLOW}🛑 Shutting down Zero Trust SDN Framework...${NC}"
    
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
    
    if [ ! -z "$MININET_PID" ]; then
        echo "   Stopping Mininet topology (PID: $MININET_PID)..."
        kill $MININET_PID 2>/dev/null || true
    fi
    
    # Wait for processes to terminate
    sleep 2
    
    # Force kill if still running
    pkill -f "controller.py" 2>/dev/null || true
    pkill -f "ryu-manager" 2>/dev/null || true
    pkill -f "zero_trust_integration.py" 2>/dev/null || true
    pkill -f "mininet_topology.py" 2>/dev/null || true
    
    echo -e "${GREEN}✅ All components stopped${NC}"
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Banner
echo ""
echo -e "${BLUE}╔══════════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║          🔐 Zero Trust SDN Framework - Complete System Startup 🔐          ║${NC}"
echo -e "${BLUE}║                                                                              ║${NC}"
echo -e "${BLUE}║  • Flask Controller (Web Dashboard & API)                                  ║${NC}"
echo -e "${BLUE}║  • Ryu SDN Controller (OpenFlow Policy Enforcement)                        ║${NC}"
echo -e "${BLUE}║  • Zero Trust Integration Framework                                        ║${NC}"
echo -e "${BLUE}║  • Honeypot Management (Optional)                                          ║${NC}"
echo -e "${BLUE}║  • Virtual IoT Devices (Optional)                                           ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Error: Python 3 is not installed${NC}"
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo -e "${GREEN}✅ Python version: $PYTHON_VERSION${NC}"

# Check if we're in the right directory
if [ ! -f "controller.py" ]; then
    echo -e "${RED}❌ Error: controller.py not found. Please run this script from the project directory${NC}"
    exit 1
fi

# Check for virtual environment
if [ -d "venv" ]; then
    echo -e "${GREEN}✅ Virtual environment found${NC}"
    VENV_PYTHON="./venv/bin/python3"
    if [ -f "$VENV_PYTHON" ]; then
        PYTHON_CMD="$VENV_PYTHON"
    else
        PYTHON_CMD="python3"
    fi
else
    echo -e "${YELLOW}⚠️  Virtual environment not found, using system Python${NC}"
    PYTHON_CMD="python3"
fi

# Check dependencies
echo ""
echo -e "${BLUE}📦 Checking dependencies...${NC}"

# Check Flask
if $PYTHON_CMD -c "import flask" 2>/dev/null; then
    echo -e "${GREEN}  ✅ Flask${NC}"
else
    echo -e "${YELLOW}  ⚠️  Flask not found (will try to install)${NC}"
fi

# Check Ryu (optional)
if command -v ryu-manager &> /dev/null || $PYTHON_CMD -c "import ryu" 2>/dev/null; then
    RYU_AVAILABLE=true
    echo -e "${GREEN}  ✅ Ryu SDN Controller${NC}"
else
    RYU_AVAILABLE=false
    echo -e "${YELLOW}  ⚠️  Ryu SDN Controller not found (optional)${NC}"
fi

# Check Docker (optional)
if command -v docker &> /dev/null && $PYTHON_CMD -c "import docker" 2>/dev/null; then
    DOCKER_AVAILABLE=true
    echo -e "${GREEN}  ✅ Docker${NC}"
else
    DOCKER_AVAILABLE=false
    echo -e "${YELLOW}  ⚠️  Docker not found (optional, for honeypot)${NC}"
fi

# Create necessary directories
echo ""
echo -e "${BLUE}📁 Setting up directories...${NC}"
mkdir -p certs honeypot_data logs
echo -e "${GREEN}✅ Directories ready${NC}"

# Start Flask Controller
echo ""
echo -e "${BLUE}🚀 Starting Flask Controller...${NC}"
$PYTHON_CMD controller.py > logs/controller.log 2>&1 &
CONTROLLER_PID=$!
echo -e "${GREEN}✅ Flask Controller started (PID: $CONTROLLER_PID)${NC}"

# Wait for controller to be ready
echo -e "${YELLOW}⏳ Waiting for controller to initialize...${NC}"
CONTROLLER_READY=false
for i in {1..30}; do
    if curl -s http://localhost:5000 > /dev/null 2>&1; then
        echo ""
        echo -e "${GREEN}✅ Controller is ready!${NC}"
        CONTROLLER_READY=true
        break
    fi
    sleep 1
    echo -n "."
done

if [ "$CONTROLLER_READY" = false ]; then
    echo ""
    echo -e "${RED}❌ Controller failed to start within 30 seconds${NC}"
    echo -e "${YELLOW}   Check logs/controller.log for errors${NC}"
    cleanup
    exit 1
fi

# Start Ryu SDN Controller (if available)
if [ "$RYU_AVAILABLE" = true ]; then
    echo ""
    echo -e "${BLUE}🌐 Starting Ryu SDN Controller...${NC}"
    if command -v ryu-manager &> /dev/null; then
        ryu-manager ryu_controller/sdn_policy_engine.py > logs/ryu.log 2>&1 &
        RYU_PID=$!
        echo -e "${GREEN}✅ Ryu SDN Controller started (PID: $RYU_PID)${NC}"
    else
        $PYTHON_CMD -m ryu.app.simple_switch_13 ryu_controller/sdn_policy_engine.py > logs/ryu.log 2>&1 &
        RYU_PID=$!
        echo -e "${GREEN}✅ Ryu SDN Controller started (PID: $RYU_PID)${NC}"
    fi
    sleep 3
else
    echo ""
    echo -e "${YELLOW}⚠️  Skipping Ryu SDN Controller (not installed)${NC}"
    echo -e "${YELLOW}   Install with: pip install ryu eventlet${NC}"
fi

# Start Zero Trust Integration Framework (optional)
echo ""
echo -e "${BLUE}🔐 Starting Zero Trust Integration Framework...${NC}"
if [ -f "zero_trust_integration.py" ]; then
    $PYTHON_CMD zero_trust_integration.py > logs/zero_trust.log 2>&1 &
    ZERO_TRUST_PID=$!
    echo -e "${GREEN}✅ Zero Trust Framework started (PID: $ZERO_TRUST_PID)${NC}"
    sleep 2
else
    echo -e "${YELLOW}⚠️  Zero Trust integration file not found, skipping${NC}"
fi

# Start Mininet Topology (optional, for testing)
if [ -f "mininet_topology.py" ]; then
    echo ""
    read -p "Start virtual IoT devices (Mininet)? [y/N]: " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${BLUE}🌐 Starting Virtual IoT Devices...${NC}"
        $PYTHON_CMD mininet_topology.py > logs/mininet.log 2>&1 &
        MININET_PID=$!
        echo -e "${GREEN}✅ Virtual devices started (PID: $MININET_PID)${NC}"
    fi
fi

# Display status
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                    ✅ System Started Successfully! ✅                         ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}📊 System Status:${NC}"
echo -e "   ${GREEN}✅${NC} Flask Controller:     http://localhost:5000 (PID: $CONTROLLER_PID)"
if [ ! -z "$RYU_PID" ]; then
    echo -e "   ${GREEN}✅${NC} Ryu SDN Controller:   Running (PID: $RYU_PID)"
else
    echo -e "   ${YELLOW}⚠️${NC}  Ryu SDN Controller:   Not running (optional)"
fi
if [ ! -z "$ZERO_TRUST_PID" ]; then
    echo -e "   ${GREEN}✅${NC} Zero Trust Framework:  Running (PID: $ZERO_TRUST_PID)"
else
    echo -e "   ${YELLOW}⚠️${NC}  Zero Trust Framework:  Not running"
fi
if [ ! -z "$MININET_PID" ]; then
    echo -e "   ${GREEN}✅${NC} Virtual Devices:      Running (PID: $MININET_PID)"
fi

echo ""
echo -e "${BLUE}🌐 Access Points:${NC}"
echo -e "   • Web Dashboard:    ${GREEN}http://localhost:5000${NC}"
echo -e "   • API Endpoints:     ${GREEN}http://localhost:5000/api/*${NC}"
if [ ! -z "$RYU_PID" ]; then
    echo -e "   • SDN Controller:   ${GREEN}Port 6653 (OpenFlow)${NC}"
fi

echo ""
echo -e "${BLUE}📝 Log Files:${NC}"
echo -e "   • Controller:        ${YELLOW}logs/controller.log${NC}"
if [ ! -z "$RYU_PID" ]; then
    echo -e "   • Ryu:               ${YELLOW}logs/ryu.log${NC}"
fi
if [ ! -z "$ZERO_TRUST_PID" ]; then
    echo -e "   • Zero Trust:        ${YELLOW}logs/zero_trust.log${NC}"
fi

echo ""
echo -e "${YELLOW}⌨️  Press Ctrl+C to stop all components${NC}"
echo ""

# Monitor processes and keep script running
echo -e "${GREEN}🔄 System is running... Monitoring components...${NC}"
echo ""

# Keep script running and monitor
while true; do
    sleep 10
    
    # Check if controller is still running
    if [ ! -z "$CONTROLLER_PID" ] && ! kill -0 $CONTROLLER_PID 2>/dev/null; then
        echo -e "${RED}❌ Flask Controller stopped unexpectedly!${NC}"
        cleanup
        exit 1
    fi
    
    # Check Ryu if it was started
    if [ ! -z "$RYU_PID" ] && ! kill -0 $RYU_PID 2>/dev/null; then
        echo -e "${YELLOW}⚠️  Ryu SDN Controller stopped${NC}"
        RYU_PID=""
    fi
    
    # Check Zero Trust if it was started
    if [ ! -z "$ZERO_TRUST_PID" ] && ! kill -0 $ZERO_TRUST_PID 2>/dev/null; then
        echo -e "${YELLOW}⚠️  Zero Trust Framework stopped${NC}"
        ZERO_TRUST_PID=""
    fi
done
