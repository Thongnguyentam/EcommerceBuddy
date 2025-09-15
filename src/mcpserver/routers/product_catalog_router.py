import logging
from typing import Dict, Any

from fastapi import APIRouter, HTTPException

from models.product_catalog import ProductSearchRequest, ProductByIdRequest, ProductByCategoryRequest
from tools.product_tools import ProductTools

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tools/products", tags=["products"])

# Global product tools instance (will be set by main.py)
product_tools: ProductTools = None


def set_product_tools(tools: ProductTools):
    """Set the product tools instance."""
    global product_tools
    product_tools = tools


@router.get("/list")
async def list_all_products() -> Dict[str, Any]:
    """Get all products from the catalog."""
    try:
        result = product_tools.list_all_products()
        return result
    except Exception as e:
        logger.error(f"Error in list_all_products: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/get")
async def get_product_by_id(request: ProductByIdRequest) -> Dict[str, Any]:
    """Get specific product by ID."""
    try:
        result = product_tools.get_product_by_id(product_id=request.product_id)
        return result
    except Exception as e:
        logger.error(f"Error in get_product_by_id: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search")
async def search_products(request: ProductSearchRequest) -> Dict[str, Any]:
    """Search for products by query."""
    try:
        result = product_tools.search_products(query=request.query)
        return result
    except Exception as e:
        logger.error(f"Error in search_products: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/category")
async def get_products_by_category(request: ProductByCategoryRequest) -> Dict[str, Any]:
    """Get products filtered by category."""
    try:
        result = product_tools.get_products_by_category(category=request.category)
        return result
    except Exception as e:
        logger.error(f"Error in get_products_by_category: {e}")
        raise HTTPException(status_code=500, detail=str(e))
