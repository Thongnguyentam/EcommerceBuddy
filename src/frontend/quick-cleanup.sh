#!/bin/bash

# Quick cleanup - kills all kubectl port-forward processes
echo "🛑 Quick cleanup: Killing all kubectl port-forward processes..."

# Kill all kubectl port-forward processes
pkill -f "kubectl port-forward"

# Clean up PID file
rm -f /tmp/frontend-portforward-pids.txt

echo "✅ Done! All kubectl port-forward processes stopped." 