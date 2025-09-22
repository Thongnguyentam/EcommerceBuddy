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
from tools.shopping_assistant_tools import ShoppingAssistantTools
from tools.image_assistant_tools import ImageAssistantTools
from clients.cart_client import CartServiceClient
from clients.product_client import ProductCatalogServiceClient
from clients.review_client import ReviewServiceClient
from clients.currency_client import CurrencyServiceClient
from clients.shopping_assistant_client import ShoppingAssistantServiceClient
from clients.image_assistant_client import ImageAssistantServiceClient

# Import routers
from routers import cart_router, product_catalog_router, review_router, currency_router, shopping_assistant_router, image_assistant_router


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global clients and tools
cart_client: CartServiceClient = None
product_client: ProductCatalogServiceClient = None
review_client: ReviewServiceClient = None
currency_client: CurrencyServiceClient = None
shopping_assistant_client: ShoppingAssistantServiceClient = None
image_assistant_client: ImageAssistantServiceClient = None
cart_tools: CartTools = None
product_tools: ProductTools = None
review_tools: ReviewTools = None
currency_tools: CurrencyTools = None
shopping_assistant_tools: ShoppingAssistantTools = None
image_assistant_tools: ImageAssistantTools = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle - startup and shutdown."""
    global cart_client, product_client, review_client, currency_client, shopping_assistant_client, image_assistant_client, cart_tools, product_tools, review_tools, currency_tools, shopping_assistant_tools, image_assistant_tools
    
    # Startup
    logger.info("🚀 Starting MCP Server...")
    
    # Initialize clients
    cart_host = os.getenv("CART_SERVICE_HOST", "cartservice:7070")
    product_host = os.getenv("PRODUCT_SERVICE_HOST", "productcatalogservice:3550")
    review_host = os.getenv("REVIEW_SERVICE_HOST", "reviewservice:8080")
    currency_host = os.getenv("CURRENCY_SERVICE_HOST", "currencyservice:7000")
    shopping_assistant_host = os.getenv("SHOPPING_ASSISTANT_SERVICE_HOST", "shoppingassistantservice:80")
    image_assistant_host = os.getenv("IMAGE_ASSISTANT_SERVICE_HOST", "imageassistantservice:8080")
    
    cart_client = CartServiceClient(host=cart_host)
    product_client = ProductCatalogServiceClient(host=product_host)
    review_client = ReviewServiceClient(host=review_host)
    currency_client = CurrencyServiceClient(address=currency_host)
    shopping_assistant_client = ShoppingAssistantServiceClient(address=shopping_assistant_host)
    image_assistant_client = ImageAssistantServiceClient(address=image_assistant_host)
    
    # Initialize tools
    cart_tools = CartTools(client=cart_client)
    product_tools = ProductTools(client=product_client)
    review_tools = ReviewTools(client=review_client)
    currency_tools = CurrencyTools(client=currency_client)
    shopping_assistant_tools = ShoppingAssistantTools(client=shopping_assistant_client)
    image_assistant_tools = ImageAssistantTools(client=image_assistant_client)
    
    # Set tools in routers
    cart_router.set_cart_tools(cart_tools)
    product_catalog_router.set_product_tools(product_tools)
    review_router.set_review_tools(review_tools)
    currency_router.set_currency_tools(currency_tools)
    shopping_assistant_router.set_shopping_assistant_tools(shopping_assistant_tools)
    image_assistant_router.set_image_assistant_tools(image_assistant_tools)
    
    logger.info(f"✅ Connected to cartservice at {cart_host}")
    logger.info(f"✅ Connected to productcatalogservice at {product_host}")
    logger.info(f"✅ Connected to reviewservice at {review_host}")
    logger.info(f"✅ Connected to currencyservice at {currency_host}")
    logger.info(f"✅ Connected to shoppingassistantservice at {shopping_assistant_host}")
    logger.info(f"✅ Connected to imageassistantservice at {image_assistant_host}")
    
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
    if shopping_assistant_client:
        shopping_assistant_client.close()
    if image_assistant_client:
        image_assistant_client.close()


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
app.include_router(shopping_assistant_router.router)
app.include_router(image_assistant_router.router)


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
                "endpoint": "/tools/cart/add",
                "method": "POST"
            },
            {
                "name": "get_cart_contents",
                "description": "Get contents of user's shopping cart",
                "parameters": {
                    "user_id": {"type": "string", "description": "User identifier"}
                },
                "endpoint": "/tools/cart/get",
                "method": "POST"
            },
            {
                "name": "clear_cart",
                "description": "Clear user's shopping cart",
                "parameters": {
                    "user_id": {"type": "string", "description": "User identifier"}
                },
                "endpoint": "/tools/cart/clear",
                "method": "POST"
            },
            {
                "name": "list_all_products",
                "description": "Get all products from the catalog",
                "parameters": {},
                "endpoint": "/tools/products/list",
                "method": "GET"
            },
            {
                "name": "get_product_by_id",
                "description": "Get specific product by ID",
                "parameters": {
                    "product_id": {"type": "string", "description": "Product ID to retrieve"}
                },
                "endpoint": "/tools/products/get",
                "method": "POST"
            },
            {
                "name": "search_products",
                "description": "Search for products by query",
                "parameters": {
                    "query": {"type": "string", "description": "Search query"}
                },
                "endpoint": "/tools/products/search",
                "method": "POST"
            },
            {
                "name": "get_products_by_category",
                "description": "Get products filtered by category",
                "parameters": {
                    "category": {"type": "string", "description": "Category to filter by"}
                },
                "endpoint": "/tools/products/category",
                "method": "POST"
            },
            {
                "name": "semantic_search_products",
                "description": "Search for products using AI-powered semantic search with vector embeddings",
                "parameters": {
                    "query": {"type": "string", "description": "Natural language search query"},
                    "limit": {"type": "integer", "description": "Maximum number of results (default: 10, max: 50)", "required": False}
                },
                "endpoint": "/tools/products/semantic-search",
                "method": "POST"
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
                "endpoint": "/tools/reviews/create",
                "method": "POST"
            },
            {
                "name": "get_product_reviews",
                "description": "Get all reviews for a specific product",
                "parameters": {
                    "product_id": {"type": "string", "description": "Product ID"},
                    "limit": {"type": "integer", "description": "Maximum reviews to return", "required": False},
                    "offset": {"type": "integer", "description": "Number of reviews to skip", "required": False}
                },
                "endpoint": "/tools/reviews/product",
                "method": "POST"
            },
            {
                "name": "get_user_reviews",
                "description": "Get all reviews by a specific user",
                "parameters": {
                    "user_id": {"type": "string", "description": "User identifier"},
                    "limit": {"type": "integer", "description": "Maximum reviews to return", "required": False},
                    "offset": {"type": "integer", "description": "Number of reviews to skip", "required": False}
                },
                "endpoint": "/tools/reviews/user",
                "method": "POST"
            },
            {
                "name": "update_review",
                "description": "Update an existing review",
                "parameters": {
                    "review_id": {"type": "integer", "description": "Review ID to update"},
                    "rating": {"type": "integer", "description": "New rating from 1-5 stars"},
                    "review_text": {"type": "string", "description": "New review text", "required": False}
                },
                "endpoint": "/tools/reviews/update",
                "method": "POST"
            },
            {
                "name": "delete_review",
                "description": "Delete a review",
                "parameters": {
                    "review_id": {"type": "integer", "description": "Review ID to delete"}
                },
                "endpoint": "/tools/reviews/delete",
                "method": "POST"
            },
            {
                "name": "get_product_review_summary",
                "description": "Get review summary statistics for a product",
                "parameters": {
                    "product_id": {"type": "string", "description": "Product ID"}
                },
                "endpoint": "/tools/reviews/summary",
                "method": "POST"
            },
            {
                "name": "get_supported_currencies",
                "description": "Get list of all supported currency codes",
                "parameters": {},
                "endpoint": "/currency/supported-currencies",
                "method": "GET"
            },
            {
                "name": "convert_currency",
                "description": "Convert currency from one type to another",
                "parameters": {
                    "from_currency": {"type": "string", "description": "Source currency code (e.g., 'USD')"},
                    "to_currency": {"type": "string", "description": "Target currency code (e.g., 'EUR')"},
                    "amount": {"type": "number", "description": "Amount to convert as decimal"}
                },
                "endpoint": "/currency/convert",
                "method": "POST"
            },
            {
                "name": "get_exchange_rates",
                "description": "Get current exchange rates for all supported currencies",
                "parameters": {},
                "endpoint": "/currency/exchange-rates",
                "method": "GET"
            },
            {
                "name": "format_money",
                "description": "Format money amount with currency symbol",
                "parameters": {
                    "amount": {"type": "number", "description": "Amount to format"},
                    "currency_code": {"type": "string", "description": "Currency code (e.g., 'USD')"}
                },
                "endpoint": "/currency/format-money",
                "method": "POST"
            },
            {
                "name": "get_ai_recommendations",
                "description": "Get AI-powered product recommendations based on user query and optional room image",
                "parameters": {
                    "user_query": {"type": "string", "description": "User's request for product recommendations"},
                    "room_image": {"type": "string", "description": "Optional base64-encoded image of the room", "required": False}
                },
                "endpoint": "/shopping-assistant/ai-recommendations"
            },
            {
                "name": "get_style_based_recommendations",
                "description": "Get product recommendations based on interior design style",
                "parameters": {
                    "room_style": {"type": "string", "description": "Interior design style (e.g., 'modern', 'rustic', 'minimalist')"},
                    "budget_max": {"type": "number", "description": "Optional maximum budget for recommendations", "required": False}
                },
                "endpoint": "/shopping-assistant/style-recommendations"
            },
            {
                "name": "get_room_specific_recommendations",
                "description": "Get product recommendations for specific room types",
                "parameters": {
                    "room_type": {"type": "string", "description": "Type of room (e.g., 'living room', 'bedroom', 'kitchen')"},
                    "specific_needs": {"type": "string", "description": "Optional specific requirements", "required": False}
                },
                "endpoint": "/shopping-assistant/room-recommendations"
            },
            {
                "name": "analyze_room_image",
                "description": "Analyze a room image and provide tailored product recommendations",
                "parameters": {
                    "room_image": {"type": "string", "description": "Base64-encoded image of the room"},
                    "user_preferences": {"type": "string", "description": "Optional user preferences or requirements", "required": False}
                },
                "endpoint": "/shopping-assistant/analyze-room"
            },
            {
                "name": "get_complementary_products",
                "description": "Get product recommendations that complement existing products",
                "parameters": {
                    "existing_products": {"type": "array", "items": {"type": "string"}, "description": "List of existing product names or descriptions"},
                    "room_context": {"type": "string", "description": "Optional context about the room", "required": False}
                },
                "endpoint": "/shopping-assistant/complementary-products"
            },
            {
                "name": "analyze_image",
                "description": "Analyze an image for objects, scene type, styles, and colors using AI",
                "parameters": {
                    "image_url": {"type": "string", "description": "URL of the image to analyze"},
                    "context": {"type": "string", "description": "Optional context for better analysis", "required": False}
                },
                "endpoint": "/image-assistant/tools/analyze-image",
                "method": "POST"
            },
            {
                "name": "visualize_product",
                "description": "Visualize a product in a user photo using AI-powered image generation (Nano Banana)",
                "parameters": {
                    "base_image_url": {"type": "string", "description": "URL of the base scene/room image"},
                    "product_image_url": {"type": "string", "description": "URL of the product image"},
                    "prompt": {"type": "string", "description": "Description of how to place the product (e.g., 'Place this vase on the table')"}
                },
                "endpoint": "/image-assistant/tools/visualize-product",
                "method": "POST"
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
