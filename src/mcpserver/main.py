#!/usr/bin/env python3
"""
Online Boutique MCP Server

Exposes cart and product catalog operations as MCP (Model Context Protocol) tools
for integration with AI assistants and Google Agent Kit.
"""

import os
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from tools.cart_tool import CartTools
from tools.product_tools import ProductTools
from clients.cart_client import CartServiceClient
from clients.product_client import ProductCatalogServiceClient

# Import routers
from routers import cart_router, product_catalog_router


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global clients and tools
cart_client: CartServiceClient = None
product_client: ProductCatalogServiceClient = None
cart_tools: CartTools = None
product_tools: ProductTools = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle - startup and shutdown."""
    global cart_client, product_client, cart_tools, product_tools
    
    # Startup
    logger.info("🚀 Starting MCP Server...")
    
    # Initialize clients
    cart_host = os.getenv("CART_SERVICE_HOST", "cartservice:7070")
    product_host = os.getenv("PRODUCT_SERVICE_HOST", "productcatalogservice:3550")
    
    cart_client = CartServiceClient(host=cart_host)
    product_client = ProductCatalogServiceClient(host=product_host)
    
    # Initialize tools
    cart_tools = CartTools(client=cart_client)
    product_tools = ProductTools(client=product_client)
    
    # Set tools in routers
    cart_router.set_cart_tools(cart_tools)
    product_catalog_router.set_product_tools(product_tools)
    
    logger.info(f"✅ Connected to cartservice at {cart_host}")
    logger.info(f"✅ Connected to productcatalogservice at {product_host}")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down MCP Server...")
    if cart_client:
        cart_client.close()
    if product_client:
        product_client.close()


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
