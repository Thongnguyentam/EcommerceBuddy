#!/usr/bin/env python3
"""
Shopping Assistant Tools for MCP Server

Provides AI-powered product recommendation tools that integrate with the
shopping assistant service for intelligent, context-aware product suggestions.
"""

import logging
import re
from typing import Dict, Any, List, Optional

from clients.shopping_assistant_client import ShoppingAssistantServiceClient

logger = logging.getLogger(__name__)


class ShoppingAssistantTools:
    """High-level shopping assistant operations for MCP server."""
    
    def __init__(self, client: ShoppingAssistantServiceClient):
        self.client = client
    
    def get_ai_recommendations(self, user_query: str, room_image: Optional[str] = None) -> Dict[str, Any]:
        """
        Get AI-powered product recommendations based on user query and optional room image.
        
        Args:
            user_query: User's request for product recommendations (e.g., "I need furniture for my living room")
            room_image: Optional base64-encoded image of the room for visual context
            
        Returns:
            dict: AI recommendations with product suggestions and IDs
        """
        try:
            # Validate inputs
            if not user_query or not user_query.strip():
                return {
                    "success": False,
                    "error": "User query cannot be empty",
                    "recommendations": "",
                    "product_ids": []
                }
            
            # Get AI recommendations from the shopping assistant service
            result = self.client.get_ai_recommendations(user_query, room_image)
            
            # Extract product IDs from the response content
            product_ids = self._extract_product_ids(result.get('content', ''))
            
            return {
                "success": True,
                "user_query": user_query,
                "recommendations": result.get('content', ''),
                "product_ids": product_ids,
                "has_image": room_image is not None,
                "message": f"Generated AI recommendations for query: '{user_query}'"
            }
            
        except Exception as e:
            logger.error(f"Error getting AI recommendations: {e}")
            return {
                "success": False,
                "error": str(e),
                "user_query": user_query,
                "recommendations": "",
                "product_ids": []
            }
    
    def get_style_based_recommendations(self, room_style: str, budget_max: Optional[float] = None) -> Dict[str, Any]:
        """
        Get product recommendations based on interior design style.
        
        Args:
            room_style: Interior design style (e.g., "modern", "rustic", "minimalist", "industrial")
            budget_max: Optional maximum budget for recommendations
            
        Returns:
            dict: Style-based product recommendations
        """
        try:
            # Construct style-specific query
            query = f"Recommend products that match a {room_style} interior design style"
            
            if budget_max:
                query += f" with a budget under ${budget_max:.2f}"
            
            # Get recommendations using the main method
            result = self.get_ai_recommendations(query)
            
            if result["success"]:
                result["room_style"] = room_style
                result["budget_max"] = budget_max
                result["recommendation_type"] = "style-based"
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting style-based recommendations: {e}")
            return {
                "success": False,
                "error": str(e),
                "room_style": room_style,
                "budget_max": budget_max,
                "recommendations": "",
                "product_ids": []
            }
    
    def get_room_specific_recommendations(self, room_type: str, specific_needs: Optional[str] = None) -> Dict[str, Any]:
        """
        Get product recommendations for specific room types.
        
        Args:
            room_type: Type of room (e.g., "living room", "bedroom", "kitchen", "bathroom", "office")
            specific_needs: Optional specific requirements (e.g., "storage solutions", "lighting", "seating")
            
        Returns:
            dict: Room-specific product recommendations
        """
        try:
            # Construct room-specific query
            query = f"Recommend products for a {room_type}"
            
            if specific_needs:
                query += f" focusing on {specific_needs}"
            
            # Get recommendations using the main method
            result = self.get_ai_recommendations(query)
            
            if result["success"]:
                result["room_type"] = room_type
                result["specific_needs"] = specific_needs
                result["recommendation_type"] = "room-specific"
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting room-specific recommendations: {e}")
            return {
                "success": False,
                "error": str(e),
                "room_type": room_type,
                "specific_needs": specific_needs,
                "recommendations": "",
                "product_ids": []
            }
    
    def analyze_room_image(self, room_image: str, user_preferences: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze a room image and provide tailored product recommendations.
        
        Args:
            room_image: Base64-encoded image of the room
            user_preferences: Optional user preferences or requirements
            
        Returns:
            dict: Image-based analysis and product recommendations
        """
        try:
            if not room_image:
                return {
                    "success": False,
                    "error": "Room image is required for image analysis",
                    "recommendations": "",
                    "product_ids": []
                }
            
            # Construct image analysis query
            query = "Analyze this room and recommend products that would complement the existing style and decor"
            
            if user_preferences:
                query += f". User preferences: {user_preferences}"
            
            # Get recommendations with image
            result = self.get_ai_recommendations(query, room_image)
            
            if result["success"]:
                result["user_preferences"] = user_preferences
                result["recommendation_type"] = "image-based"
                result["analysis_performed"] = True
            
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing room image: {e}")
            return {
                "success": False,
                "error": str(e),
                "user_preferences": user_preferences,
                "recommendations": "",
                "product_ids": []
            }
    
    def get_complementary_products(self, existing_products: List[str], room_context: Optional[str] = None) -> Dict[str, Any]:
        """
        Get product recommendations that complement existing products.
        
        Args:
            existing_products: List of existing product names or descriptions
            room_context: Optional context about the room (e.g., "modern living room")
            
        Returns:
            dict: Complementary product recommendations
        """
        try:
            if not existing_products:
                return {
                    "success": False,
                    "error": "At least one existing product must be specified",
                    "recommendations": "",
                    "product_ids": []
                }
            
            # Construct complementary products query
            products_list = ", ".join(existing_products)
            query = f"I have these products: {products_list}. Recommend complementary items that would go well with them"
            
            if room_context:
                query += f" in a {room_context}"
            
            # Get recommendations
            result = self.get_ai_recommendations(query)
            
            if result["success"]:
                result["existing_products"] = existing_products
                result["room_context"] = room_context
                result["recommendation_type"] = "complementary"
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting complementary product recommendations: {e}")
            return {
                "success": False,
                "error": str(e),
                "existing_products": existing_products,
                "room_context": room_context,
                "recommendations": "",
                "product_ids": []
            }
    
    def _extract_product_ids(self, content: str) -> List[str]:
        """
        Extract product IDs from AI response content.
        
        The shopping assistant service returns product IDs in the format:
        [<product_id>], [<product_id>], [<product_id>]
        
        Args:
            content: AI response content
            
        Returns:
            list: Extracted product IDs
        """
        try:
            # Pattern to match [PRODUCT_ID] format
            pattern = r'\[([A-Z0-9]+)\]'
            matches = re.findall(pattern, content)
            
            # Remove duplicates while preserving order
            seen = set()
            unique_ids = []
            for product_id in matches:
                if product_id not in seen:
                    seen.add(product_id)
                    unique_ids.append(product_id)
            
            logger.debug(f"Extracted {len(unique_ids)} product IDs: {unique_ids}")
            return unique_ids
            
        except Exception as e:
            logger.warning(f"Failed to extract product IDs from content: {e}")
            return []
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check the health of the shopping assistant service.
        
        Returns:
            dict: Health status of the shopping assistant service
        """
        try:
            return self.client.health_check()
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "service": "shopping-assistant",
                "error": str(e)
            } 