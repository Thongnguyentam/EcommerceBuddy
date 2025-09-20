#!/bin/bash

echo "🚀 Testing ProductCatalogService Semantic Search"
echo "================================================"

# Start port forwarding in background
kubectl port-forward svc/productcatalogservice 3550:3550 > /dev/null 2>&1 &
PF_PID=$!

# Wait for port forward to be ready
sleep 5

# Run the integration test
echo "Running semantic search integration test..."
INTEGRATION_TEST=1 CLOUDSQL_HOST=10.103.0.3 go test -v -run TestSemanticSearchIntegration -count=1

# Check pod status
echo ""
echo "Pod status:"
kubectl get pods -l app=productcatalogservice

# Clean up port forward
kill $PF_PID 2>/dev/null || true