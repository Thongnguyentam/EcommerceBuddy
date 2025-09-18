#!/usr/bin/env python3
"""
Online Boutique Unified MCP Server

This server acts as a centralized gateway that exposes all relevant microservice 
operations (e.g., cart, product catalog, reviews, currency) as a unified set of 
MCP (Model Context Protocol) tools.

Architecture:
- Centralized Gateway: Provides a single endpoint for multiple AI agents or assistants. 
  This simplifies agent logic, as they don't need to connect to multiple servers 
  for cross-domain tasks (like searching for a product and then adding it to the cart).
- Unified Tool Schema: All available tools across the microservices are discoverable
  from a single `/tools/schema` endpoint.

This approach is designed for general-purpose shopping assistants that require 
access to a wide range of functionalities.
"""

import os
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from tools.cart_tool import CartTools
from tools.product_tools import ProductTools
from tools.review_tools import ReviewTools
from tools.currency_tools import CurrencyTools
from clients.cart_client import CartServiceClient
from clients.product_client import ProductCatalogServiceClient
from clients.review_client import ReviewServiceClient
from clients.currency_client import CurrencyServiceClient

# Import routers
from routers import cart_router, product_catalog_router, review_router, currency_router


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global clients and tools
cart_client: CartServiceClient = None
product_client: ProductCatalogServiceClient = None
review_client: ReviewServiceClient = None
currency_client: CurrencyServiceClient = None
cart_tools: CartTools = None
product_tools: ProductTools = None
review_tools: ReviewTools = None
currency_tools: CurrencyTools = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle - startup and shutdown."""
    global cart_client, product_client, review_client, currency_client, cart_tools, product_tools, review_tools, currency_tools
    
    # Startup
    logger.info("🚀 Starting MCP Server...")
    
    # Initialize clients
    cart_host = os.getenv("CART_SERVICE_HOST", "cartservice:7070")
    product_host = os.getenv("PRODUCT_SERVICE_HOST", "productcatalogservice:3550")
    review_host = os.getenv("REVIEW_SERVICE_HOST", "reviewservice:8080")
    currency_host = os.getenv("CURRENCY_SERVICE_HOST", "currencyservice:7000")
    
    cart_client = CartServiceClient(host=cart_host)
    product_client = ProductCatalogServiceClient(host=product_host)
    review_client = ReviewServiceClient(host=review_host)
    currency_client = CurrencyServiceClient(address=currency_host)
    
    # Initialize tools
    cart_tools = CartTools(client=cart_client)
    product_tools = ProductTools(client=product_client)
    review_tools = ReviewTools(client=review_client)
    currency_tools = CurrencyTools(client=currency_client)
    
    # Set tools in routers
    cart_router.set_cart_tools(cart_tools)
    product_catalog_router.set_product_tools(product_tools)
    review_router.set_review_tools(review_tools)
    currency_router.set_currency_tools(currency_tools)
    
    logger.info(f"✅ Connected to cartservice at {cart_host}")
    logger.info(f"✅ Connected to productcatalogservice at {product_host}")
    logger.info(f"✅ Connected to reviewservice at {review_host}")
    logger.info(f"✅ Connected to currencyservice at {currency_host}")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down MCP Server...")
    if cart_client:
        cart_client.close()
    if product_client:
        product_client.close()
    if review_client:
        review_client.close()
    if currency_client:
        currency_client.close()


# Create FastAPI app
app = FastAPI(
    title="Online Boutique MCP Server",
    description="Model Context Protocol server for Online Boutique microservices",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware for cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(cart_router.router)
app.include_router(product_catalog_router.router)
app.include_router(review_router.router)
app.include_router(currency_router.router)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "online-boutique-mcp-server",
        "version": "1.0.0"
    }


# MCP Schema Endpoints (for tool discovery)
@app.get("/tools/schema")
async def get_tools_schema() -> Dict[str, Any]:
    """Get schema of all available MCP tools."""
    return {
        "tools": [
            {
                "name": "add_to_cart",
                "description": "Add item to user's shopping cart",
                "parameters": {
                    "user_id": {"type": "string", "description": "User identifier"},
                    "product_id": {"type": "string", "description": "Product ID to add"},
                    "quantity": {"type": "integer", "description": "Quantity to add"}
                },
                "endpoint": "/tools/cart/add"
            },
            {
                "name": "get_cart_contents",
                "description": "Get contents of user's shopping cart",
                "parameters": {
                    "user_id": {"type": "string", "description": "User identifier"}
                },
                "endpoint": "/tools/cart/get"
            },
            {
                "name": "clear_cart",
                "description": "Clear user's shopping cart",
                "parameters": {
                    "user_id": {"type": "string", "description": "User identifier"}
                },
                "endpoint": "/tools/cart/clear"
            },
            {
                "name": "list_all_products",
                "description": "Get all products from the catalog",
                "parameters": {},
                "endpoint": "/tools/products/list"
            },
            {
                "name": "get_product_by_id",
                "description": "Get specific product by ID",
                "parameters": {
                    "product_id": {"type": "string", "description": "Product ID to retrieve"}
                },
                "endpoint": "/tools/products/get"
            },
            {
                "name": "search_products",
                "description": "Search for products by query",
                "parameters": {
                    "query": {"type": "string", "description": "Search query"}
                },
                "endpoint": "/tools/products/search"
            },
            {
                "name": "get_products_by_category",
                "description": "Get products filtered by category",
                "parameters": {
                    "category": {"type": "string", "description": "Category to filter by"}
                },
                "endpoint": "/tools/products/category"
            },
            {
                "name": "create_review",
                "description": "Create a new review for a product",
                "parameters": {
                    "user_id": {"type": "string", "description": "User identifier"},
                    "product_id": {"type": "string", "description": "Product ID to review"},
                    "rating": {"type": "integer", "description": "Rating from 1-5 stars"},
                    "review_text": {"type": "string", "description": "Review text/comment", "required": False}
                },
                "endpoint": "/tools/reviews/create"
            },
            {
                "name": "get_product_reviews",
                "description": "Get all reviews for a specific product",
                "parameters": {
                    "product_id": {"type": "string", "description": "Product ID"},
                    "limit": {"type": "integer", "description": "Maximum reviews to return", "required": False},
                    "offset": {"type": "integer", "description": "Number of reviews to skip", "required": False}
                },
                "endpoint": "/tools/reviews/product"
            },
            {
                "name": "get_user_reviews",
                "description": "Get all reviews by a specific user",
                "parameters": {
                    "user_id": {"type": "string", "description": "User identifier"},
                    "limit": {"type": "integer", "description": "Maximum reviews to return", "required": False},
                    "offset": {"type": "integer", "description": "Number of reviews to skip", "required": False}
                },
                "endpoint": "/tools/reviews/user"
            },
            {
                "name": "update_review",
                "description": "Update an existing review",
                "parameters": {
                    "review_id": {"type": "integer", "description": "Review ID to update"},
                    "rating": {"type": "integer", "description": "New rating from 1-5 stars"},
                    "review_text": {"type": "string", "description": "New review text", "required": False}
                },
                "endpoint": "/tools/reviews/update"
            },
            {
                "name": "delete_review",
                "description": "Delete a review",
                "parameters": {
                    "review_id": {"type": "integer", "description": "Review ID to delete"}
                },
                "endpoint": "/tools/reviews/delete"
            },
            {
                "name": "get_product_review_summary",
                "description": "Get review summary statistics for a product",
                "parameters": {
                    "product_id": {"type": "string", "description": "Product ID"}
                },
                "endpoint": "/tools/reviews/summary"
            },
            {
                "name": "get_supported_currencies",
                "description": "Get list of all supported currency codes",
                "parameters": {},
                "endpoint": "/currency/supported-currencies"
            },
            {
                "name": "convert_currency",
                "description": "Convert currency from one type to another",
                "parameters": {
                    "from_currency": {"type": "string", "description": "Source currency code (e.g., 'USD')"},
                    "to_currency": {"type": "string", "description": "Target currency code (e.g., 'EUR')"},
                    "amount": {"type": "number", "description": "Amount to convert as decimal"}
                },
                "endpoint": "/currency/convert"
            },
            {
                "name": "get_exchange_rates",
                "description": "Get current exchange rates for all supported currencies",
                "parameters": {},
                "endpoint": "/currency/exchange-rates"
            },
            {
                "name": "format_money",
                "description": "Format money amount with currency symbol",
                "parameters": {
                    "amount": {"type": "number", "description": "Amount to format"},
                    "currency_code": {"type": "string", "description": "Currency code (e.g., 'USD')"}
                },
                "endpoint": "/currency/format-money"
            }
        ]
    }


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("MCP_SERVER_PORT", "8080"))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        log_level="info",
        reload=True
    )
