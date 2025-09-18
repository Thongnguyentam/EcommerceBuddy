#!/usr/bin/env python3
"""
Helper script to set up port forwards and run integration tests.

This script will:
1. Start port forwards for required services
2. Run integration tests
3. Clean up port forwards

Usage:
    python run_integration_tests.py [test_name]
    
    test_name can be: product, cart, review, currency, all (default: all)
"""

import subprocess
import sys
import time
import signal
import os
from typing import List, Dict

# Port forward configurations
PORT_FORWARDS = {
    'product': {
        'service': 'productcatalogservice',
        'local_port': 3550,
        'service_port': 3550,
        'command': ['kubectl', 'port-forward', 'svc/productcatalogservice', '3550:3550']
    },
    'cart': {
        'service': 'cartservice', 
        'local_port': 7070,
        'service_port': 7070,
        'command': ['kubectl', 'port-forward', 'svc/cartservice', '7070:7070']
    },
    'review': {
        'service': 'reviewservice',
        'local_port': 8082,
        'service_port': 8080,
        'command': ['kubectl', 'port-forward', 'svc/reviewservice', '8082:8080']
    },
    'currency': {
        'service': 'currencyservice',
        'local_port': 7000,
        'service_port': 7000,
        'command': ['kubectl', 'port-forward', 'svc/currencyservice', '7000:7000']
    }
}

# Test configurations
TESTS = {
    'product': {
        'script': 'test_product_integration.py',
        'description': 'Product Catalog Service Integration Test',
        'requires': ['product']
    },
    'cart': {
        'script': 'test_cart_integration.py', 
        'description': 'Cart Service Integration Test',
        'requires': ['cart']
    },
    'review': {
        'script': 'test_review_real_integration.py',
        'description': 'Review Service Integration Test (Full CRUD + Content Verification)', 
        'requires': ['review']
    },
    'review_unit': {
        'script': 'test_review_integration.py',
        'description': 'Review Service Unit Test',
        'requires': []  # No port forwards needed for unit tests
    },
    'currency': {
        'script': 'test_currency_real_integration.py',
        'description': 'Currency Service Integration Test (Real Conversions)',
        'requires': ['currency']
    }
}

class PortForwardManager:
    """Manages kubectl port-forward processes."""
    
    def __init__(self):
        self.processes: Dict[str, subprocess.Popen] = {}
    
    def start_port_forward(self, service_name: str) -> bool:
        """Start port forward for a service."""
        if service_name in self.processes:
            print(f"   ⚠️  Port forward for {service_name} already running")
            return True
        
        config = PORT_FORWARDS[service_name]
        print(f"   🚀 Starting port forward: {config['service']} -> localhost:{config['local_port']}")
        
        try:
            process = subprocess.Popen(
                config['command'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                preexec_fn=os.setsid  # Create new process group for easier cleanup
            )
            
            self.processes[service_name] = process
            
            # Wait a bit for port forward to establish
            time.sleep(3)
            
            # Check if process is still running
            if process.poll() is None:
                print(f"   ✅ Port forward started for {service_name}")
                return True
            else:
                print(f"   ❌ Port forward failed to start for {service_name}")
                return False
                
        except Exception as e:
            print(f"   ❌ Failed to start port forward for {service_name}: {e}")
            return False
    
    def stop_port_forward(self, service_name: str):
        """Stop port forward for a service."""
        if service_name not in self.processes:
            return
        
        process = self.processes[service_name]
        try:
            # Kill the entire process group
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            process.wait(timeout=5)
        except (ProcessLookupError, subprocess.TimeoutExpired):
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            except ProcessLookupError:
                pass
        
        del self.processes[service_name]
        print(f"   🛑 Stopped port forward for {service_name}")
    
    def stop_all(self):
        """Stop all port forwards."""
        for service_name in list(self.processes.keys()):
            self.stop_port_forward(service_name)
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop_all()


def run_test(test_name: str, port_manager: PortForwardManager) -> bool:
    """Run a specific test."""
    if test_name not in TESTS:
        print(f"❌ Unknown test: {test_name}")
        return False
    
    test_config = TESTS[test_name]
    
    print(f"\n🧪 Running {test_config['description']}")
    print("=" * 60)
    
    # Start required port forwards
    for service in test_config['requires']:
        if not port_manager.start_port_forward(service):
            print(f"❌ Failed to start required service: {service}")
            return False
    
    # Run the test
    try:
        script_path = os.path.join(os.path.dirname(__file__), test_config['script'])
        result = subprocess.run([sys.executable, script_path], 
                              capture_output=False, 
                              text=True)
        
        if result.returncode == 0:
            print(f"✅ {test_config['description']} PASSED")
            return True
        else:
            print(f"❌ {test_config['description']} FAILED (exit code: {result.returncode})")
            return False
            
    except Exception as e:
        print(f"❌ Error running test {test_name}: {e}")
        return False


def main():
    """Main function."""
    
    # Parse command line arguments
    test_to_run = sys.argv[1] if len(sys.argv) > 1 else 'all'
    
    if test_to_run not in TESTS and test_to_run != 'all':
        print(f"❌ Unknown test: {test_to_run}")
        print(f"Available tests: {', '.join(TESTS.keys())}, all")
        sys.exit(1)
    
    print("🚀 MCP Server Integration Test Runner")
    print("=" * 60)
    
    # Check if kubectl is available
    try:
        subprocess.run(['kubectl', 'version', '--client'], 
                      capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ kubectl not found or not working")
        print("Make sure kubectl is installed and configured")
        sys.exit(1)
    
    tests_to_run = [test_to_run] if test_to_run != 'all' else list(TESTS.keys())
    passed_tests = []
    failed_tests = []
    
    with PortForwardManager() as port_manager:
        try:
            for test_name in tests_to_run:
                if run_test(test_name, port_manager):
                    passed_tests.append(test_name)
                else:
                    failed_tests.append(test_name)
                
                # Small delay between tests
                time.sleep(1)
        
        except KeyboardInterrupt:
            print("\n⏹️  Tests cancelled by user")
            sys.exit(0)
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    if passed_tests:
        print(f"✅ PASSED ({len(passed_tests)}): {', '.join(passed_tests)}")
    
    if failed_tests:
        print(f"❌ FAILED ({len(failed_tests)}): {', '.join(failed_tests)}")
    
    if failed_tests:
        print("\n💡 TROUBLESHOOTING TIPS:")
        print("1. Make sure all services are deployed: kubectl get pods")
        print("2. Check service status: kubectl get svc")
        print("3. Verify database connections are working")
        print("4. Check service logs: kubectl logs <pod-name>")
        sys.exit(1)
    else:
        print(f"\n🎉 ALL TESTS PASSED! ({len(passed_tests)}/{len(tests_to_run)})")
        sys.exit(0)


if __name__ == "__main__":
    main() 