#!/bin/bash

# Frontend with Auto Port-Forward Setup Script
echo "🚀 Setting up Frontend with automatic port-forwarding..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to check if kubectl is available
check_kubectl() {
    if ! command -v kubectl &> /dev/null; then
        echo -e "${RED}❌ kubectl not found. Please install kubectl first.${NC}"
        exit 1
    fi
}

# Function to check if services exist in cluster
check_services() {
    echo -e "${BLUE}🔍 Checking if services exist in cluster...${NC}"
    
    services=(
        "productcatalogservice"
        "currencyservice" 
        "cartservice"
        "recommendationservice"
        "checkoutservice"
        "shippingservice"
        "adservice"
        "agentservice"
        "reviewservice"
    )
    
    missing_services=()
    
    for service in "${services[@]}"; do
        if ! kubectl get svc "$service" &> /dev/null; then
            missing_services+=("$service")
        fi
    done
    
    if [ ${#missing_services[@]} -gt 0 ]; then
        echo -e "${YELLOW}⚠️  Some services are not deployed:${NC}"
        for service in "${missing_services[@]}"; do
            echo -e "${YELLOW}   - $service${NC}"
        done
        echo -e "${YELLOW}   The frontend will work with available services only.${NC}"
    else
        echo -e "${GREEN}✅ All services found in cluster${NC}"
    fi
}

# Function to start port forwarding
start_port_forward() {
    local service=$1
    local local_port=$2
    local remote_port=$3
    local display_name=$4
    
    # Check if port is already in use
    if lsof -Pi :$local_port -sTCP:LISTEN -t >/dev/null ; then
        echo -e "${YELLOW}⚠️  Port $local_port already in use by another process${NC}"
        local pid=$(lsof -ti:$local_port)
        local process_info=$(ps -p $pid -o comm= 2>/dev/null)
        echo -e "${YELLOW}   Process: $pid ($process_info)${NC}"
        echo -e "${YELLOW}   Run './stop-port-forwards.sh' to clean up old port forwards${NC}"
        return 1
    fi
    
    # Check if service exists
    if kubectl get svc "$service" &> /dev/null; then
        echo -e "${BLUE}🔗 Starting port-forward: $display_name (localhost:$local_port -> $service:$remote_port)${NC}"
        kubectl port-forward svc/$service $local_port:$remote_port &
        local pf_pid=$!
        echo $pf_pid >> /tmp/frontend-portforward-pids.txt
        sleep 2
        
        # Verify port forward is working
        if kill -0 $pf_pid 2>/dev/null; then
            echo -e "${GREEN}✅ $display_name port-forward active (PID: $pf_pid)${NC}"
            return 0
        else
            echo -e "${RED}❌ Failed to start port-forward for $display_name${NC}"
            return 1
        fi
    else
        echo -e "${YELLOW}⚠️  Service $service not found, skipping $display_name${NC}"
        return 1
    fi
}

# Function to cleanup port forwards
cleanup() {
    echo -e "\n${YELLOW}🧹 Cleaning up port-forwards...${NC}"
    if [ -f /tmp/frontend-portforward-pids.txt ]; then
        while read pid; do
            if kill -0 $pid 2>/dev/null; then
                kill $pid
                echo -e "${GREEN}✅ Stopped port-forward (PID: $pid)${NC}"
            fi
        done < /tmp/frontend-portforward-pids.txt
        rm -f /tmp/frontend-portforward-pids.txt
    fi
    
    # Kill the frontend if it's running
    if [ ! -z "$FRONTEND_PID" ] && kill -0 $FRONTEND_PID 2>/dev/null; then
        kill $FRONTEND_PID
        echo -e "${GREEN}✅ Stopped frontend server${NC}"
    fi
    
    echo -e "${GREEN}🎉 Cleanup complete${NC}"
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Function to check for existing port forwards
check_existing_port_forwards() {
    local ports_in_use=()
    local ports=(3550 7000 7070 8080 8081 8082 8083 5050 50051 9555)
    
    for port in "${ports[@]}"; do
        if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
            ports_in_use+=($port)
        fi
    done
    
    if [ ${#ports_in_use[@]} -gt 0 ]; then
        echo -e "${YELLOW}⚠️  Some required ports are already in use:${NC}"
        for port in "${ports_in_use[@]}"; do
            local pid=$(lsof -ti:$port 2>/dev/null)
            local process_info=$(ps -p $pid -o comm= 2>/dev/null)
            echo -e "${YELLOW}   Port $port: PID $pid ($process_info)${NC}"
        done
        echo -e "\n${BLUE}💡 Options:${NC}"
        echo -e "${BLUE}   1. Run './stop-port-forwards.sh' to clean up${NC}"
        echo -e "${BLUE}   2. Press Ctrl+C to exit and clean up manually${NC}"
        echo -e "${BLUE}   3. Continue anyway (may cause conflicts)${NC}"
        
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo -e "${YELLOW}Exiting. Run './stop-port-forwards.sh' first.${NC}"
            exit 1
        fi
    fi
}

# Main execution
main() {
    check_kubectl
    check_services
    check_existing_port_forwards
    
    # Clean up any existing port-forward PIDs file
    rm -f /tmp/frontend-portforward-pids.txt
    
    echo -e "\n${BLUE}🔗 Setting up port-forwarding for services...${NC}"
    
    # Start port forwarding for all services
    start_port_forward "productcatalogservice" "3550" "3550" "Product Catalog"
    start_port_forward "currencyservice" "7000" "7000" "Currency Service"  
    start_port_forward "cartservice" "7070" "7070" "Cart Service"
    start_port_forward "recommendationservice" "8081" "8080" "Recommendation Service"
    start_port_forward "checkoutservice" "5050" "5050" "Checkout Service"
    start_port_forward "shippingservice" "50051" "50051" "Shipping Service"
    start_port_forward "adservice" "9555" "9555" "Ad Service"
    start_port_forward "agentservice" "8082" "8080" "AI Agent Service"
    start_port_forward "reviewservice" "8083" "8080" "Review Service"
    
    echo -e "\n${GREEN}✅ Port-forwarding setup complete${NC}"
    
    # Set environment variables for frontend
    export PORT=8080
    export LISTEN_ADDR=""
    export BASE_URL=""
    export ENABLE_TRACING=0
    export ENABLE_PROFILER=0
    export ENABLE_ASSISTANT=true
    
    # Service addresses pointing to port-forwarded services
    export PRODUCT_CATALOG_SERVICE_ADDR="localhost:3550"
    export CURRENCY_SERVICE_ADDR="localhost:7000"
    export CART_SERVICE_ADDR="localhost:7070"
    export RECOMMENDATION_SERVICE_ADDR="localhost:8081"
    export CHECKOUT_SERVICE_ADDR="localhost:5050"
    export SHIPPING_SERVICE_ADDR="localhost:50051"
    export AD_SERVICE_ADDR="localhost:9555"
    export SHOPPING_ASSISTANT_SERVICE_ADDR="localhost:8082"
    export REVIEW_SERVICE_ADDR="localhost:8083"
    
    echo -e "\n${BLUE}📋 Frontend Configuration:${NC}"
    echo -e "  Frontend URL: ${GREEN}http://localhost:$PORT${NC}"
    echo -e "  Assistant enabled: ${GREEN}$ENABLE_ASSISTANT${NC}"
    
    # Build frontend if needed
    if [ ! -f "./frontend" ]; then
        echo -e "\n${BLUE}🔨 Building frontend binary...${NC}"
        go build -o frontend .
        if [ $? -ne 0 ]; then
            echo -e "${RED}❌ Build failed!${NC}"
            cleanup
            exit 1
        fi
        echo -e "${GREEN}✅ Frontend built successfully${NC}"
    fi
    
    echo -e "\n${GREEN}🌐 Starting frontend server...${NC}"
    echo -e "${GREEN}   Frontend: http://localhost:$PORT${NC}"
    echo -e "${GREEN}   Chatbot UI: Click the chat icon in the header or the floating button${NC}"
    echo -e "${YELLOW}   Press Ctrl+C to stop all services${NC}"
    echo -e "\n${BLUE}📊 Service Status:${NC}"
    
    # Show which services are available
    services=(
        "Product Catalog:3550"
        "Currency:7000"
        "Cart:7070" 
        "Recommendations:8081"
        "Checkout:5050"
        "Shipping:50051"
        "Ads:9555"
        "AI Agents:8082"
        "Reviews:8083"
    )
    
    for service_info in "${services[@]}"; do
        IFS=':' read -r name port <<< "$service_info"
        if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
            echo -e "   ${GREEN}✅ $name (localhost:$port)${NC}"
        else
            echo -e "   ${RED}❌ $name (localhost:$port)${NC}"
        fi
    done
    
    echo ""
    
    # Start the frontend
    ./frontend &
    FRONTEND_PID=$!
    
    # Wait for frontend to start
    sleep 3
    
    if kill -0 $FRONTEND_PID 2>/dev/null; then
        echo -e "${GREEN}🎉 Frontend is running at http://localhost:$PORT${NC}"
        echo -e "${GREEN}   Test the chatbot by clicking the chat icon!${NC}"
        
        # Keep the script running
        wait $FRONTEND_PID
    else
        echo -e "${RED}❌ Frontend failed to start${NC}"
        cleanup
        exit 1
    fi
}

# Run main function
main 