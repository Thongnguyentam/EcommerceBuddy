#!/usr/bin/env python3
"""
Shopping Assistant Service Client

This client communicates with the shopping assistant service which provides
AI-powered product recommendations based on user queries and room images.
"""

import os
import logging
import requests
import base64
from typing import Dict, Any, Optional
from io import BytesIO
from PIL import Image

logger = logging.getLogger(__name__)


class ShoppingAssistantServiceClient:
    """Client for Shopping Assistant Service HTTP operations."""
    
    def __init__(self, address: Optional[str] = None):
        self.address = address or os.getenv("SHOPPING_ASSISTANT_SERVICE_ADDR", "shoppingassistantservice:80")
        # Ensure http:// prefix for HTTP requests
        if not self.address.startswith(('http://', 'https://')):
            self.address = f"http://{self.address}"
        
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
    
    def close(self):
        """Close the HTTP session."""
        if self.session:
            self.session.close()
    
    def get_ai_recommendations(self, user_message: str, image_data: Optional[str] = None) -> Dict[str, Any]:
        """
        Get AI-powered product recommendations based on user query and optional room image.
        
        Args:
            user_message: User's request/query for product recommendations
            image_data: Optional base64-encoded image data of the room
            
        Returns:
            dict: Response containing AI recommendations and product IDs
        """
        try:
            payload = {
                "message": user_message
            }
            
            if image_data:
                # Ensure proper base64 format for image
                if not image_data.startswith('data:image'):
                    # Add data URL prefix if missing
                    payload["image"] = f"data:image/jpeg;base64,{image_data}"
                else:
                    payload["image"] = image_data
            
            logger.info(f"Sending request to shopping assistant: {self.address}")
            logger.debug(f"Request payload: {user_message[:100]}...")
            
            response = self.session.post(
                f"{self.address}/",
                json=payload,
                timeout=30  # Generous timeout for AI processing
            )
            
            response.raise_for_status()
            result = response.json()
            
            logger.info("Successfully received AI recommendations")
            return result
            
        except requests.exceptions.ConnectionError as e:
            raise Exception(f"Failed to connect to shopping assistant service at {self.address}: {e}")
        except requests.exceptions.Timeout as e:
            raise Exception(f"Shopping assistant service request timed out: {e}")
        except requests.exceptions.HTTPError as e:
            raise Exception(f"Shopping assistant service returned error {response.status_code}: {e}")
        except Exception as e:
            raise Exception(f"Failed to get AI recommendations: {e}")
    
    def encode_image_file(self, image_path: str) -> str:
        """
        Encode an image file to base64 string.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            str: Base64 encoded image data
        """
        try:
            with open(image_path, "rb") as image_file:
                image_data = image_file.read()
                encoded = base64.b64encode(image_data).decode('utf-8')
                return encoded
        except Exception as e:
            raise Exception(f"Failed to encode image file {image_path}: {e}")
    
    def encode_image_bytes(self, image_bytes: bytes, format: str = "JPEG") -> str:
        """
        Encode image bytes to base64 string.
        
        Args:
            image_bytes: Image data as bytes
            format: Image format (JPEG, PNG, etc.)
            
        Returns:
            str: Base64 encoded image data with data URL prefix
        """
        try:
            # Convert to PIL Image to ensure proper format
            image = Image.open(BytesIO(image_bytes))
            
            # Convert to RGB if necessary (for JPEG)
            if format.upper() == "JPEG" and image.mode != "RGB":
                image = image.convert("RGB")
            
            # Save to bytes
            buffer = BytesIO()
            image.save(buffer, format=format.upper())
            buffer.seek(0)
            
            # Encode to base64
            encoded = base64.b64encode(buffer.getvalue()).decode('utf-8')
            mime_type = f"image/{format.lower()}"
            
            return f"data:{mime_type};base64,{encoded}"
            
        except Exception as e:
            raise Exception(f"Failed to encode image bytes: {e}")
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check if the shopping assistant service is healthy.
        
        Returns:
            dict: Health status information
        """
        try:
            # Try a simple request to check connectivity
            response = self.session.post(
                f"{self.address}/",
                json={"message": "health check"},
                timeout=5
            )
            
            if response.status_code == 200:
                return {
                    "status": "healthy",
                    "service": "shopping-assistant",
                    "address": self.address
                }
            else:
                return {
                    "status": "unhealthy",
                    "service": "shopping-assistant", 
                    "address": self.address,
                    "error": f"HTTP {response.status_code}"
                }
                
        except Exception as e:
            return {
                "status": "unhealthy",
                "service": "shopping-assistant",
                "address": self.address,
                "error": str(e)
            } 