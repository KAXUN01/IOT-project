#!/bin/bash
set +e

# ==========================
# GLOBAL FLAGS & STATE
# ==========================
NO_ML=false
NO_MININET=false
WITH_MININET=false

CLEANUP_RUNNING=false

CONTROLLER_PID=""
RYU_PID=""
ZERO_TRUST_PID=""
MININET_PID=""
HONEYPOT_CONTAINER=""

LAST_CONTROLLER_RESTART=0
LAST_RYU_RESTART=0
RESTART_COOLDOWN=10

# ==========================
# ARGUMENT PARSING
# ==========================
for arg in "$@"; do
  case $arg in
    --no-ml) NO_ML=true ;;
    --no-mininet) NO_MININET=true ;;
    --with-mininet) WITH_MININET=true ;;
    --help|-h)
      echo "Usage: ./start.sh [--with-mininet | --no-mininet | --no-ml]"
      exit 0
      ;;
  esac
done

# ==========================
# COLORS
# ==========================
GREEN="\033[0;32m"
YELLOW="\033[1;33m"
RED="\033[0;31m"
BLUE="\033[0;34m"
NC="\033[0m"

# ==========================
# CLEANUP (RUNS ONCE ONLY)
# ==========================
cleanup() {
  if [ "$CLEANUP_RUNNING" = true ]; then return; fi
  CLEANUP_RUNNING=true
  trap - SIGINT SIGTERM

  echo -e "\n${YELLOW}Shutting down Zero Trust SDN Framework...${NC}"

  for pid in "$CONTROLLER_PID" "$RYU_PID" "$ZERO_TRUST_PID" "$MININET_PID"; do
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null
    fi
  done

  pkill -f controller.py 2>/dev/null
  pkill -f ryu-manager 2>/dev/null
  pkill -f zero_trust_integration.py 2>/dev/null
  pkill -f mininet 2>/dev/null
  sudo mn -c 2>/dev/null || true

  if [ -n "$HONEYPOT_CONTAINER" ] && command -v docker &>/dev/null; then
    docker stop "$HONEYPOT_CONTAINER" 2>/dev/null || true
  fi

  echo -e "${GREEN}All components stopped cleanly${NC}"
  exit 0
}

trap cleanup SIGINT SIGTERM

# ==========================
# SYSTEM DEPENDENCIES & DOCKER
# ==========================
echo -e "${BLUE}Checking system dependencies...${NC}"

# 1. Install System Packages (Python 3.8, Build Tools)
if command -v apt-get &> /dev/null; then
    # Only try to install if we have sudo or are root
    if [ "$EUID" -eq 0 ] || command -v sudo &> /dev/null; then
         # Check for critical build dependencies
         if ! dpkg -s python3.8-venv build-essential libssl-dev libffi-dev &> /dev/null; then
            echo -e "${YELLOW}Installing critical system dependencies (Python headers, build tools)...${NC}"
            # Add deadsnakes PPA if python3.8 is missing
            if ! command -v python3.8 &> /dev/null; then
                sudo apt-get update -qq
                sudo apt-get install -y software-properties-common -qq
                sudo add-apt-repository ppa:deadsnakes/ppa -y
            fi
            
            sudo apt-get update -qq
            sudo apt-get install -y python3.8 python3.8-venv python3.8-dev \
                                    build-essential libssl-dev libffi-dev \
                                    curl net-tools
         fi
    fi
fi

# 2. Auto-install Docker if missing
if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}Docker not found. Attempting automatic installation...${NC}"
    if command -v curl &> /dev/null; then
        curl -fsSL https://get.docker.com -o get-docker.sh
        sudo sh get-docker.sh
        rm get-docker.sh
        
        # Add user to docker group
        if [ "$EUID" -ne 0 ]; then
            echo -e "${YELLOW}Adding user $USER to docker group...${NC}"
            sudo usermod -aG docker "$USER"
            echo -e "${YELLOW}NOTE: You may need to log out and back in for Docker group changes to take effect.${NC}"
        fi
        
        echo -e "${GREEN}Docker installed successfully${NC}"
    else
        echo -e "${RED}curl not found, cannot install Docker automatically${NC}"
    fi
fi

# ==========================
# PYTHON + VENV
# ==========================
PYTHON_BASE_CMD="python3.8"
if ! command -v python3.8 &>/dev/null; then
  echo -e "${RED}Python 3.8 not found. Please install python3.8 and python3.8-venv.${NC}"
  exit 1
fi

if [ ! -d venv ]; then
  echo -e "${YELLOW}Creating Python 3.8 virtual environment...${NC}"
  # Ensure pip is installed
  python3.8 -m venv venv || {
     echo -e "${RED}Failed to create venv. Is python3.8-venv installed?${NC}"
     echo -e "${YELLOW}Try: sudo apt-get install python3.8-venv${NC}"
     exit 1
  }
fi

PYTHON_CMD="./venv/bin/python"
PIP_CMD="./venv/bin/pip"

# Install core packaging tools
echo -e "${BLUE}Updating pip and setuptools...${NC}"
$PIP_CMD install --quiet --upgrade pip "setuptools==58.0.0" wheel

# Install Requirements
echo -e "${BLUE}Installing dependencies from requirements.txt...${NC}"
$PIP_CMD install --quiet -r requirements.txt

# Re-install Ryu with no-build-isolation to respect pinned setuptools 58.0.0
# This is critical for compatibility
echo -e "${BLUE}Ensuring Ryu installation compatibility...${NC}"
$PIP_CMD install --quiet --no-build-isolation ryu eventlet==0.30.2

# ==========================
# ASK MININET
# ==========================
ask_mininet() {
  if [ "$NO_MININET" = true ]; then return 1; fi
  if [ "$WITH_MININET" = true ]; then return 0; fi
  
  # Always ask if no flags provided, even if not strictly interactive (fallback safety)
  if [ -t 0 ]; then
    echo ""
    echo -e "${YELLOW}======================================================${NC}"
    echo -e "${YELLOW}   VIRTUAL IoT DEVICE SIMULATION (MININET)            ${NC}"
    echo -e "${YELLOW}======================================================${NC}"
    echo -e "${BLUE}Do you want to start virtual IoT test devices? [y/N]${NC}"
    echo -e "${BLUE}(Requires sudo privileges)${NC}"
    read -r ans
    if [[ "$ans" =~ ^[Yy]$ ]]; then
        return 0
    fi
  fi
  return 1
}

# ==========================
# START SERVICES
# ==========================

# Create logs directory
mkdir -p logs

# 1. Flask Controller
echo -e "${BLUE}Starting Flask Controller...${NC}"
nohup $PYTHON_CMD controller.py > logs/controller.log 2>&1 &
CONTROLLER_PID=$!

sleep 3
if ! kill -0 $CONTROLLER_PID 2>/dev/null; then
  echo -e "${RED}Flask failed to start${NC}"
  # Check logs
  tail -n 10 logs/controller.log
  cleanup
fi

# 2. Ryu Controller
echo -e "${BLUE}Starting Ryu SDN Controller...${NC}"
export PYTHONPATH="$(pwd)"
# Use venv python to run ryu-manager if possible, or assume it's in venv/bin
RYU_MANAGER="./venv/bin/ryu-manager"
if [ ! -f "$RYU_MANAGER" ]; then
    RYU_MANAGER="ryu-manager" # Fallback to path
fi

nohup $RYU_MANAGER --ofp-tcp-listen-port 6653 ryu_controller.sdn_policy_engine > logs/ryu.log 2>&1 &
RYU_PID=$!

sleep 4
if ! kill -0 $RYU_PID 2>/dev/null; then
  echo -e "${RED}Ryu failed to start${NC}"
  # Check logs
  tail -n 10 logs/ryu.log
  cleanup
fi

# 3. Zero Trust Framework
if [ -f zero_trust_integration.py ]; then
  echo -e "${BLUE}Starting Zero Trust Framework...${NC}"
  nohup $PYTHON_CMD zero_trust_integration.py > logs/zero_trust.log 2>&1 &
  ZERO_TRUST_PID=$!
fi

# 4. Honeypot Deployment
if command -v docker &>/dev/null; then
    echo -e "${BLUE}Deploying Honeypot...${NC}"
    
    # Ensure Docker daemon is running
    if ! docker info &>/dev/null; then
        echo -e "${YELLOW}Starting Docker daemon...${NC}"
        sudo systemctl start docker 2>/dev/null || sudo service docker start 2>/dev/null || true
        sleep 3
    fi
    
    # Check Docker is now available
    if docker info &>/dev/null; then
        # Create honeypot data directory
        mkdir -p honeypot_data/cowrie
        
        # Pull Cowrie image if not present
        if ! docker images cowrie/cowrie --format "{{.Repository}}" 2>/dev/null | grep -q "cowrie"; then
            echo -e "${YELLOW}Pulling Cowrie honeypot image (this may take a moment)...${NC}"
            docker pull cowrie/cowrie:latest
        fi
        
        # Deploy using Python module
        if $PYTHON_CMD -c "from honeypot_manager.honeypot_deployer import HoneypotDeployer; print(f'DEPLOY_RESULT:{HoneypotDeployer().deploy()}')" 2>&1 | grep -q "DEPLOY_RESULT:True"; then
            HONEYPOT_CONTAINER="iot_honeypot_cowrie"
            echo -e "${GREEN}Honeypot deployed: $HONEYPOT_CONTAINER${NC}"
        else
            # Fallback: try direct docker run
            if ! docker ps --format "{{.Names}}" 2>/dev/null | grep -q "iot_honeypot"; then
                echo -e "${YELLOW}Trying direct Docker deployment...${NC}"
                docker run -d --name iot_honeypot_cowrie \
                    -p 2222:2222 -p 8080:8080 \
                    -v "$(pwd)/honeypot_data/cowrie:/data" \
                    cowrie/cowrie:latest 2>/dev/null && HONEYPOT_CONTAINER="iot_honeypot_cowrie"
            fi
            
            if docker ps --format "{{.Names}}" 2>/dev/null | grep -q "iot_honeypot"; then
                HONEYPOT_CONTAINER=$(docker ps --format "{{.Names}}" 2>/dev/null | grep "iot_honeypot" | head -1)
                echo -e "${GREEN}Honeypot container running: $HONEYPOT_CONTAINER${NC}"
            else
                echo -e "${YELLOW}Honeypot deployment failed (Docker may need configuration)${NC}"
            fi
        fi
    else
        echo -e "${YELLOW}Docker daemon not running, skipping honeypot${NC}"
    fi
fi

# 5. Mininet (Optional)
if [ -f mininet_topology.py ] && ask_mininet; then
  echo -e "${BLUE}Starting Mininet devices...${NC}"
  nohup $PYTHON_CMD mininet_topology.py > logs/mininet.log 2>&1 &
  MININET_PID=$!
fi

# ==========================
# STATUS
# ==========================
echo -e "\n${GREEN}System Started Successfully!${NC}"
echo "Flask PID: $CONTROLLER_PID"
echo "Ryu PID: $RYU_PID"
echo "Zero Trust PID: $ZERO_TRUST_PID"
echo "Mininet PID: $MININET_PID"
if [ -n "$HONEYPOT_CONTAINER" ]; then
    echo "Honeypot: $HONEYPOT_CONTAINER"
fi
echo "Dashboard: http://localhost:5000"

# ==========================
# MONITOR LOOP (STABLE)
# ==========================
while true; do
  sleep 10
  now=$(date +%s)

  if ! kill -0 $CONTROLLER_PID 2>/dev/null; then
    if (( now - LAST_CONTROLLER_RESTART > RESTART_COOLDOWN )); then
      echo -e "${YELLOW}Restarting Flask Controller...${NC}"
      LAST_CONTROLLER_RESTART=$now
      nohup $PYTHON_CMD controller.py > logs/controller.log 2>&1 &
      CONTROLLER_PID=$!
    fi
  fi

  if ! kill -0 $RYU_PID 2>/dev/null; then
    if (( now - LAST_RYU_RESTART > RESTART_COOLDOWN )); then
      echo -e "${YELLOW}Restarting Ryu SDN Controller...${NC}"
      LAST_RYU_RESTART=$now
      export PYTHONPATH="$(pwd)"
      nohup $RYU_MANAGER --ofp-tcp-listen-port 6653 ryu_controller.sdn_policy_engine >> logs/ryu.log 2>&1 &
      RYU_PID=$!
    fi
  fi
done
