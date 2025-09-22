#!/bin/bash
# Setup script for local agent testing

echo "🚀 Setting up local agent testing environment"
echo "=============================================="

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl not found. Please install kubectl first."
    exit 1
fi

# Check if MCP server is running in cluster
echo "📡 Checking MCP server status..."
if kubectl get svc mcpserver &> /dev/null; then
    echo "✅ MCP server found in cluster"
else
    echo "❌ MCP server not found in cluster. Please deploy it first."
    exit 1
fi

# Kill any existing port-forward processes
echo "🧹 Cleaning up existing port-forwards..."
pkill -f "kubectl port-forward.*mcpserver" || true

# Start port-forward in background
echo "🔗 Starting port-forward for MCP server..."
kubectl port-forward svc/mcpserver 8081:8080 &
PORT_FORWARD_PID=$!

# Wait a moment for port-forward to establish
sleep 3

# Test the connection
echo "🔍 Testing MCP server connection..."
if curl -s http://localhost:8081/health > /dev/null; then
    echo "✅ MCP server is accessible at http://localhost:8081"
else
    echo "❌ Failed to connect to MCP server"
    kill $PORT_FORWARD_PID 2>/dev/null
    exit 1
fi

echo ""
echo "🎉 Local testing environment is ready!"
echo ""
echo "Next steps:"
echo "1. Activate virtual environment: source venv/bin/activate"
echo "2. Run local tests: python test_local_agent.py"
echo "3. Or run the agent service: python main.py"
echo ""
echo "Port-forward PID: $PORT_FORWARD_PID"
echo "To stop port-forward: kill $PORT_FORWARD_PID"
echo ""
echo "Press Ctrl+C to stop port-forward and exit"

# Keep the script running to maintain port-forward
trap "echo '🛑 Stopping port-forward...'; kill $PORT_FORWARD_PID 2>/dev/null; exit 0" INT

# Wait for the port-forward process
wait $PORT_FORWARD_PID 