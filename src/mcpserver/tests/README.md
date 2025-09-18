# MCP Server Tests

This directory contains tests for the MCP (Model Context Protocol) server integration with microservices.

## Test Types

### Unit Tests
- **`test_review_integration.py`** - Unit tests for review tools with mocked dependencies
- No external services required

### Integration Tests  
- **`test_product_integration.py`** - Tests product catalog service integration
- **`test_cart_integration.py`** - Tests cart service integration  
- **`test_review_real_integration.py`** - Tests review service CRUD operations
- **`test_mcp_server.py`** - Tests the full MCP server HTTP API

## Running Tests

### Quick Start - Run All Tests
```bash
# Automatically sets up port forwards and runs all tests
python tests/run_integration_tests.py
```

### Run Specific Tests
```bash
# Run only product tests
python tests/run_integration_tests.py product

# Run only review tests  
python tests/run_integration_tests.py review

# Run unit tests (no port forwards needed)
python tests/run_integration_tests.py review_unit
```

### Manual Testing

If you prefer to manage port forwards manually:

1. **Set up port forwards:**
```bash
# Product catalog service
kubectl port-forward svc/productcatalogservice 3550:3550 &

# Cart service  
kubectl port-forward svc/cartservice 7070:7070 &

# Review service
kubectl port-forward svc/reviewservice 8082:8080 &
```

2. **Run individual tests:**
```bash
cd tests/
python test_product_integration.py
python test_cart_integration.py  
python test_review_real_integration.py
python test_review_integration.py  # Unit test, no port forward needed
```

## Prerequisites

1. **Kubernetes cluster** with Online Boutique deployed
2. **kubectl** configured to access the cluster
3. **Python environment** with dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Test Structure

```
tests/
├── README.md                          # This file
├── __init__.py                        # Python package marker
├── run_integration_tests.py           # Test runner with port forward management
├── test_cart_integration.py           # Cart service integration test
├── test_product_integration.py        # Product catalog integration test  
├── test_review_integration.py         # Review service unit test
├── test_review_real_integration.py    # Review service integration test
└── test_mcp_server.py                 # Full MCP server API test
```

## What Each Test Does

### Product Integration Test
- Lists all products from catalog
- Gets specific products by ID
- Searches products by query
- Filters products by category
- Tests error handling for non-existent products

### Cart Integration Test  
- Adds items to cart
- Retrieves cart contents
- Clears cart
- Tests input validation

### Review Integration Test (Unit)
- Tests review tools validation logic
- Tests error handling with mocked responses
- Tests data formatting
- No external dependencies

### Review Real Integration Test
- **Creates** a new review for a product
- **Reads** reviews by product and user
- **Updates** the review rating and text
- **Deletes** the review
- Verifies CRUD operations work end-to-end
- Tests review summary statistics

### MCP Server Test
- Tests HTTP API endpoints
- Tests tool schema discovery
- Tests actual tool execution via HTTP

## Troubleshooting

### Common Issues

1. **Port forward failed**
   - Check if services are running: `kubectl get pods`
   - Verify service exists: `kubectl get svc`
   - Try different ports if conflicts exist

2. **Connection refused**  
   - Wait a few seconds after starting port forward
   - Check if port is already in use: `netstat -an | grep :3550`

3. **Test failures**
   - Check service logs: `kubectl logs <pod-name>`
   - Verify database connections are working
   - Ensure services are fully initialized

4. **Import errors**
   - Make sure you're in the mcpserver directory
   - Verify virtual environment is activated
   - Check that all dependencies are installed

### Debug Mode

For more verbose output, you can run tests directly:
```bash
cd tests/
python -v test_review_real_integration.py
```

## Adding New Tests

To add a new integration test:

1. Create the test file in `tests/` directory
2. Add appropriate import path setup:
   ```python
   sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
   ```
3. Update `run_integration_tests.py` to include the new test
4. Add port forward configuration if needed
5. Update this README

## CI/CD Integration

The test runner is designed to work in CI/CD pipelines:
- Returns proper exit codes (0 for success, 1 for failure)
- Automatically manages port forwards
- Provides clear output for debugging
- Handles cleanup on interruption 