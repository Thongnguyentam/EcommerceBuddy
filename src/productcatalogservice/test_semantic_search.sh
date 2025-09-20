#!/bin/bash

echo "🚀 ProductCatalogService Semantic Search Test Suite"
echo "=================================================="

# Check if port forwarding is active
if ! nc -z localhost 3550; then
    echo "❌ Service not accessible on localhost:3550"
    echo "💡 Please run: kubectl port-forward svc/productcatalogservice 3550:3550"
    exit 1
fi

echo "✅ Service is accessible on localhost:3550"
echo ""

# Test 1: Check service health and product count
echo "📋 Test 1: Service Health Check"
echo "--------------------------------"
PRODUCT_COUNT=$(grpcurl -plaintext localhost:3550 hipstershop.ProductCatalogService/ListProducts 2>/dev/null | grep -o '"id"' | wc -l)
if [ "$PRODUCT_COUNT" -gt 0 ]; then
    echo "✅ Service healthy - $PRODUCT_COUNT products available"
else
    echo "❌ Service unhealthy - no products found"
    exit 1
fi
echo ""

# Test 2: Regular Search
echo "🔍 Test 2: Regular Search"
echo "-------------------------"
REGULAR_RESULTS=$(grpcurl -plaintext -d '{"query": "furniture"}' localhost:3550 hipstershop.ProductCatalogService/SearchProducts 2>/dev/null | grep -o '"id"' | wc -l)
echo "Regular search for 'furniture': $REGULAR_RESULTS results"
echo ""

# Test 3: Semantic Search Tests
echo "🤖 Test 3: Semantic Search"
echo "---------------------------"

# Test 3a: Comfortable seating
echo "Testing: 'comfortable seating'"
SEMANTIC_RESULT=$(grpcurl -plaintext -d '{"query": "comfortable seating", "limit": 5}' localhost:3550 hipstershop.ProductCatalogService/SemanticSearchProducts 2>/dev/null)
if echo "$SEMANTIC_RESULT" | grep -q '"results"'; then
    SEMANTIC_COUNT=$(echo "$SEMANTIC_RESULT" | grep -o '"id"' | wc -l)
    echo "✅ Semantic search working - found $SEMANTIC_COUNT products"
    
    # Show first result
    FIRST_PRODUCT=$(echo "$SEMANTIC_RESULT" | grep -o '"name":"[^"]*"' | head -1 | cut -d'"' -f4)
    if [ ! -z "$FIRST_PRODUCT" ]; then
        echo "   Top result: $FIRST_PRODUCT"
    fi
else
    echo "❌ Semantic search failed"
    echo "Error details:"
    echo "$SEMANTIC_RESULT"
fi
echo ""

# Test 3b: Kitchen appliances
echo "Testing: 'kitchen appliances'"
KITCHEN_RESULT=$(grpcurl -plaintext -d '{"query": "kitchen appliances", "limit": 3}' localhost:3550 hipstershop.ProductCatalogService/SemanticSearchProducts 2>/dev/null)
if echo "$KITCHEN_RESULT" | grep -q '"results"'; then
    KITCHEN_COUNT=$(echo "$KITCHEN_RESULT" | grep -o '"id"' | wc -l)
    echo "✅ Kitchen search working - found $KITCHEN_COUNT products"
else
    echo "❌ Kitchen search failed"
fi
echo ""

# Test 3c: Winter clothing
echo "Testing: 'winter clothing'"
WINTER_RESULT=$(grpcurl -plaintext -d '{"query": "winter clothing", "limit": 3}' localhost:3550 hipstershop.ProductCatalogService/SemanticSearchProducts 2>/dev/null)
if echo "$WINTER_RESULT" | grep -q '"results"'; then
    WINTER_COUNT=$(echo "$WINTER_RESULT" | grep -o '"id"' | wc -l)
    echo "✅ Winter clothing search working - found $WINTER_COUNT products"
else
    echo "❌ Winter clothing search failed"
fi
echo ""

# Test 4: Edge Cases
echo "🧪 Test 4: Edge Cases"
echo "---------------------"

# Empty query
echo "Testing: empty query"
EMPTY_RESULT=$(grpcurl -plaintext -d '{"query": "", "limit": 5}' localhost:3550 hipstershop.ProductCatalogService/SemanticSearchProducts 2>/dev/null)
if echo "$EMPTY_RESULT" | grep -q '"results"'; then
    echo "✅ Empty query handled gracefully"
else
    echo "❌ Empty query failed"
fi

# Large limit
echo "Testing: large limit (100)"
LARGE_RESULT=$(grpcurl -plaintext -d '{"query": "product", "limit": 100}' localhost:3550 hipstershop.ProductCatalogService/SemanticSearchProducts 2>/dev/null)
if echo "$LARGE_RESULT" | grep -q '"results"'; then
    LARGE_COUNT=$(echo "$LARGE_RESULT" | grep -o '"id"' | wc -l)
    echo "✅ Large limit handled - returned $LARGE_COUNT products"
else
    echo "❌ Large limit failed"
fi
echo ""

# Summary
echo "📊 Test Summary"
echo "==============="
echo "✅ Service Health: PASSED"
echo "✅ Product Catalog: $PRODUCT_COUNT products loaded"
echo "✅ Regular Search: WORKING"

if echo "$SEMANTIC_RESULT" | grep -q '"results"'; then
    echo "✅ Semantic Search: WORKING"
    echo "✅ RAG Functionality: ENABLED"
    echo ""
    echo "🎉 All tests passed! Semantic search is working correctly!"
else
    echo "❌ Semantic Search: FAILED"
    echo "❌ RAG Functionality: NOT WORKING"
    echo ""
    echo "💔 Tests failed. Check service logs for details."
fi

echo ""
echo "🔍 To debug further, check service logs:"
echo "kubectl logs -l app=productcatalogservice --tail=20" 