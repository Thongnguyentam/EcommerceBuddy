#!/bin/bash

# Agent Service Development Environment Setup
# This script sets up the development environment for local testing

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🛠️ Setting up Agent Service Development Environment${NC}"
echo -e "${BLUE}================================================${NC}"

# Check if we're in the right directory
if [ ! -f "main.py" ]; then
    echo -e "${RED}❌ Please run this script from the src/agentservice directory${NC}"
    exit 1
fi

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check dependencies
echo -e "${YELLOW}📋 Checking dependencies...${NC}"
if ! command_exists python3; then
    echo -e "${RED}❌ Python 3 is not installed${NC}"
    exit 1
fi

if ! command_exists kubectl; then
    echo -e "${RED}❌ kubectl is not installed${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Dependencies found${NC}"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}🐍 Creating Python virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
echo -e "${YELLOW}🔄 Activating virtual environment...${NC}"
source venv/bin/activate

# Install dependencies
echo -e "${YELLOW}📦 Installing Python dependencies...${NC}"
pip install --upgrade pip
pip install -r requirements.txt

# Create .env file from example if it doesn't exist
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}📝 Creating .env file from example...${NC}"
    cp env.development.example .env
    echo -e "${YELLOW}⚠️ Please edit .env file with your Google Cloud project settings${NC}"
    echo -e "   Required: GOOGLE_CLOUD_PROJECT"
    echo -e "   Optional: GOOGLE_CLOUD_REGION (defaults to us-central1)"
fi

echo -e "${GREEN}✅ Development environment setup complete!${NC}"
echo ""
echo -e "${BLUE}📋 Next steps:${NC}"
echo -e "1. Edit .env file with your Google Cloud project ID:"
echo -e "   ${YELLOW}nano .env${NC}"
echo -e ""
echo -e "2. Set up port forwarding to MCP server (in another terminal):"
echo -e "   ${YELLOW}kubectl port-forward svc/mcpserver 8081:8080${NC}"
echo -e ""
echo -e "3. Start the development server:"
echo -e "   ${YELLOW}source venv/bin/activate${NC}"
echo -e "   ${YELLOW}python main.py${NC}"
echo -e ""
echo -e "4. Test the service:"
echo -e "   ${YELLOW}curl http://localhost:8080/health${NC}"
echo -e ""
echo -e "5. Run the image agent test:"
echo -e "   ${YELLOW}python tests/test_image_agent.py${NC}" 