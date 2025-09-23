#!/bin/bash

# Stop All Port Forwards Script
echo "🛑 Stopping all port-forward processes..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to kill port forwards by PID file
cleanup_by_pid_file() {
    if [ -f /tmp/frontend-portforward-pids.txt ]; then
        echo -e "${BLUE}📋 Cleaning up port-forwards from PID file...${NC}"
        while read pid; do
            if kill -0 $pid 2>/dev/null; then
                kill $pid
                echo -e "${GREEN}✅ Stopped port-forward (PID: $pid)${NC}"
            else
                echo -e "${YELLOW}⚠️  Process $pid already stopped${NC}"
            fi
        done < /tmp/frontend-portforward-pids.txt
        rm -f /tmp/frontend-portforward-pids.txt
        echo -e "${GREEN}✅ Cleaned up PID file${NC}"
    else
        echo -e "${YELLOW}⚠️  No PID file found at /tmp/frontend-portforward-pids.txt${NC}"
    fi
}

# Function to kill all kubectl port-forward processes
cleanup_all_kubectl_port_forwards() {
    echo -e "${BLUE}🔍 Finding all kubectl port-forward processes...${NC}"
    
    # Find all kubectl port-forward processes
    pids=$(ps aux | grep "kubectl port-forward" | grep -v grep | awk '{print $2}')
    
    if [ -z "$pids" ]; then
        echo -e "${YELLOW}⚠️  No kubectl port-forward processes found${NC}"
        return
    fi
    
    echo -e "${BLUE}📋 Found kubectl port-forward processes:${NC}"
    ps aux | grep "kubectl port-forward" | grep -v grep | while read line; do
        echo -e "${BLUE}   $line${NC}"
    done
    
    echo -e "\n${BLUE}🛑 Stopping all kubectl port-forward processes...${NC}"
    for pid in $pids; do
        if kill -0 $pid 2>/dev/null; then
            kill $pid
            echo -e "${GREEN}✅ Stopped kubectl port-forward (PID: $pid)${NC}"
        fi
    done
}

# Function to kill frontend processes
cleanup_frontend() {
    echo -e "${BLUE}🔍 Looking for frontend processes...${NC}"
    
    frontend_pids=$(ps aux | grep "./frontend" | grep -v grep | awk '{print $2}')
    
    if [ -z "$frontend_pids" ]; then
        echo -e "${YELLOW}⚠️  No frontend processes found${NC}"
        return
    fi
    
    echo -e "${BLUE}🛑 Stopping frontend processes...${NC}"
    for pid in $frontend_pids; do
        if kill -0 $pid 2>/dev/null; then
            kill $pid
            echo -e "${GREEN}✅ Stopped frontend (PID: $pid)${NC}"
        fi
    done
}

# Function to check specific ports
check_and_free_ports() {
    echo -e "${BLUE}🔍 Checking specific ports...${NC}"
    
    ports=(3550 7000 7070 8080 8081 8082 8083 5050 50051 9555)
    
    for port in "${ports[@]}"; do
        pid=$(lsof -ti:$port 2>/dev/null)
        if [ ! -z "$pid" ]; then
            process_info=$(ps -p $pid -o comm= 2>/dev/null)
            echo -e "${YELLOW}⚠️  Port $port is in use by process $pid ($process_info)${NC}"
            read -p "Kill process on port $port? (y/N): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                kill $pid
                echo -e "${GREEN}✅ Killed process on port $port${NC}"
            fi
        else
            echo -e "${GREEN}✅ Port $port is free${NC}"
        fi
    done
}

# Main execution
main() {
    echo -e "${BLUE}🚀 Starting cleanup process...${NC}"
    
    # Method 1: Clean up using PID file (most reliable)
    cleanup_by_pid_file
    
    # Method 2: Kill all kubectl port-forward processes
    cleanup_all_kubectl_port_forwards
    
    # Method 3: Clean up frontend processes
    cleanup_frontend
    
    # Wait a moment for processes to stop
    sleep 2
    
    # Method 4: Check specific ports and offer to kill processes
    echo -e "\n${BLUE}🔍 Final port check...${NC}"
    check_and_free_ports
    
    echo -e "\n${GREEN}🎉 Cleanup complete!${NC}"
    echo -e "${GREEN}   You can now run the setup script again.${NC}"
}

# Run main function
main 