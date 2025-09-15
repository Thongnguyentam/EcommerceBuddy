import logging
from typing import Dict, Any

from fastapi import APIRouter, HTTPException

from models.cart import AddToCartRequest, CartRequest
from tools.cart_tool import CartTools

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tools/cart", tags=["cart"])

# Global cart tools instance (will be set by main.py)
cart_tools: CartTools = None


def set_cart_tools(tools: CartTools):
    """Set the cart tools instance."""
    global cart_tools
    cart_tools = tools


@router.post("/add")
async def add_to_cart(request: AddToCartRequest) -> Dict[str, Any]:
    """Add item to user's shopping cart."""
    try:
        result = cart_tools.add_to_cart(
            user_id=request.user_id,
            product_id=request.product_id,
            quantity=request.quantity
        )
        return result
    except Exception as e:
        logger.error(f"Error in add_to_cart: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/get")
async def get_cart_contents(request: CartRequest) -> Dict[str, Any]:
    """Get contents of user's shopping cart."""
    try:
        result = cart_tools.get_cart_contents(user_id=request.user_id)
        return result
    except Exception as e:
        logger.error(f"Error in get_cart_contents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clear")
async def clear_cart(request: CartRequest) -> Dict[str, Any]:
    """Clear user's shopping cart."""
    try:
        result = cart_tools.clear_cart(user_id=request.user_id)
        return result
    except Exception as e:
        logger.error(f"Error in clear_cart: {e}")
        raise HTTPException(status_code=500, detail=str(e))
