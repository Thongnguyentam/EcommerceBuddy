#!/usr/bin/env python3
"""
Shopping Assistant Router for MCP Server

FastAPI router that exposes shopping assistant tools as HTTP endpoints
for AI agents to access intelligent product recommendations.
"""

import logging
from typing import Dict, Any, Optional, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from tools.shopping_assistant_tools import ShoppingAssistantTools

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/shopping-assistant", tags=["shopping-assistant"])

# Global shopping assistant tools instance (will be set by main.py)
shopping_assistant_tools: ShoppingAssistantTools = None


def set_shopping_assistant_tools(tools: ShoppingAssistantTools):
    """Set the shopping assistant tools instance."""
    global shopping_assistant_tools
    shopping_assistant_tools = tools


# Pydantic models for request validation
class AIRecommendationRequest(BaseModel):
    user_query: str
    room_image: Optional[str] = None


class StyleRecommendationRequest(BaseModel):
    room_style: str
    budget_max: Optional[float] = None


class RoomRecommendationRequest(BaseModel):
    room_type: str
    specific_needs: Optional[str] = None


class ImageAnalysisRequest(BaseModel):
    room_image: str
    user_preferences: Optional[str] = None


class ComplementaryProductsRequest(BaseModel):
    existing_products: List[str]
    room_context: Optional[str] = None


@router.post("/ai-recommendations")
async def get_ai_recommendations(request: AIRecommendationRequest) -> Dict[str, Any]:
    """Get AI-powered product recommendations based on user query and optional room image."""
    try:
        result = shopping_assistant_tools.get_ai_recommendations(
            user_query=request.user_query,
            room_image=request.room_image
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
        
    except Exception as e:
        logger.error(f"Error in get_ai_recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/style-recommendations")
async def get_style_based_recommendations(request: StyleRecommendationRequest) -> Dict[str, Any]:
    """Get product recommendations based on interior design style."""
    try:
        result = shopping_assistant_tools.get_style_based_recommendations(
            room_style=request.room_style,
            budget_max=request.budget_max
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
        
    except Exception as e:
        logger.error(f"Error in get_style_based_recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/room-recommendations")
async def get_room_specific_recommendations(request: RoomRecommendationRequest) -> Dict[str, Any]:
    """Get product recommendations for specific room types."""
    try:
        result = shopping_assistant_tools.get_room_specific_recommendations(
            room_type=request.room_type,
            specific_needs=request.specific_needs
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
        
    except Exception as e:
        logger.error(f"Error in get_room_specific_recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze-room")
async def analyze_room_image(request: ImageAnalysisRequest) -> Dict[str, Any]:
    """Analyze a room image and provide tailored product recommendations."""
    try:
        result = shopping_assistant_tools.analyze_room_image(
            room_image=request.room_image,
            user_preferences=request.user_preferences
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
        
    except Exception as e:
        logger.error(f"Error in analyze_room_image: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/complementary-products")
async def get_complementary_products(request: ComplementaryProductsRequest) -> Dict[str, Any]:
    """Get product recommendations that complement existing products."""
    try:
        result = shopping_assistant_tools.get_complementary_products(
            existing_products=request.existing_products,
            room_context=request.room_context
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
        
    except Exception as e:
        logger.error(f"Error in get_complementary_products: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Check the health of the shopping assistant service."""
    try:
        result = shopping_assistant_tools.health_check()
        
        if result["status"] != "healthy":
            raise HTTPException(status_code=503, detail=result)
        
        return result
        
    except Exception as e:
        logger.error(f"Error in health_check: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 