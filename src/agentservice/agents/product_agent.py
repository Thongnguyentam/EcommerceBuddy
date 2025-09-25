"""
Product Agent

Specializes in:
- Product catalog browsing and search
- Product recommendations
- Product information retrieval
- Semantic product search
"""

import json
import logging
import uuid
from typing import Dict, Any, List, Optional
from agents.base_agent import BaseAgent
from agents.utils import clean_and_parse_json, validate_tool_plan
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
class ProductAgent(BaseAgent):
    """Agent specialized in product catalog operations."""
    
    @property
    def name(self) -> str:
        return "Product Agent"
    
    @property
    def description(self) -> str:
        return "Specialized in product search, recommendations, and catalog browsing"
    
    @property
    def domain_tools(self) -> List[str]:
        return [
            "list_all_products",
            "get_product_by_id", 
            "search_products",
            "get_products_by_category",
            "semantic_search_products"
        ]
    
    async def process_request(self, message: str, user_id: Optional[str] = None,
                            session_id: Optional[str] = None, 
                            context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process a product-related request."""
        
        if not session_id:
            session_id = str(uuid.uuid4())
        
        try:
            # Debug logging
            logger.info(f"ProductAgent processing: '{message}' (user_id: {user_id}, session_id: {session_id})")
            logger.info(f"ProductAgent context: {context}")
            
            # Analyze request and determine tools to use
            available_tools = self.get_available_tools()
            logger.info(f"ProductAgent available tools: {[t['name'] for t in available_tools]}")
            
            tool_plan = await self._plan_tool_usage(message, available_tools, context)
            logger.info(f"ProductAgent tool plan: {tool_plan}")
            
            # Execute tools
            results = []
            tools_called = []
            
            for tool_call in tool_plan.get('tools_to_call', []):
                try:
                    tool_name = tool_call['tool_name']
                    parameters = tool_call['parameters']
                    
                    # Add user_id if needed
                    if user_id and 'user_id' in parameters:
                        parameters['user_id'] = user_id
                    
                    result = await self.call_tool(tool_name, parameters)
                    results.append({
                        'tool': tool_name,
                        'result': result
                    })
                    tools_called.append(tool_name)
                    
                except Exception as e:
                    logger.error(f"Product agent tool call failed: {tool_call['tool_name']} - {str(e)}")
                    results.append({
                        'tool': tool_call['tool_name'],
                        'error': str(e)
                    })
            
            # Generate response based on results
            response = await self._generate_product_response(message, results, tool_plan)
            
            # Update session
            self.update_session(session_id, message, response, tools_called)
            
            return {
                "response": response,
                "agent_used": "product",
                "tools_called": tools_called,
                "session_id": session_id
            }
            
        except Exception as e:
            logger.error(f"Product agent request processing failed: {str(e)}")
            return {
                "response": f"I apologize, but I encountered an error while searching for products: {str(e)}",
                "agent_used": "product",
                "tools_called": [],
                "session_id": session_id
            }
    
    async def _plan_tool_usage(self, message: str, available_tools: List[Dict[str, Any]], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Plan which tools to use for the product request."""
        
        prompt = self.create_tool_calling_prompt(message, available_tools)
        
        # Add product-specific guidance
        prompt += f"""
Context for previous steps: {json.dumps(context) if context else "No context"}

Product-specific guidelines:
- Use semantic_search_products for natural language queries about product features or style
- Use search_products for keyword-based searches (most of the time, semantic_search_products is preferred unless user explicitly asks for a specific product) 
- Use get_products_by_category when user mentions specific categories
- Use list_all_products only when user wants to browse everything
- Use get_product_by_id when user mentions a specific product ID

IMPORTANT: If context contains responses from other agents, use that information to search for relevant products.
- If context has image_agent_response with analysis results (objects, styles, colors, tags), use those to search for matching products
- If context has sentiment_agent_response with product IDs, get details for those products
- If context has cart_agent_response with product IDs, get details for those products
- Look for product information in the context and search for related products
- If context contains room analysis (objects, styles, colors), search for products that match those characteristics
- If context contains product recommendations, get details for the top products

Context Analysis:
- Check if context contains image analysis with objects, styles, colors, or tags
- Look for product IDs from other agents in the context
- Extract product characteristics from context and search for matching products
- If multiple products are found in context, get details for the most relevant ones

Examples:
- "Find me a red couch" → semantic_search_products with query "red couch"
- "Show me kitchen items" → get_products_by_category with category "kitchen"
- "What products do you have?" → list_all_products
- If context has "red, modern, living room" → semantic_search_products with "red modern living room furniture"

"""

        try:
            response = await self.generate_response(prompt)
            parsed_plan = clean_and_parse_json(response)
            return validate_tool_plan(parsed_plan)
            
        except Exception as e:
            logger.error(f"Product tool planning failed: {str(e)}")
            # Fallback to semantic search
            return {
                "reasoning": "Fallback to semantic search",
                "tools_to_call": [
                    {
                        "tool_name": "semantic_search_products",
                        "parameters": {"query": message, "limit": 10},
                        "reasoning": "Using semantic search as fallback"
                    }
                ],
                "response_strategy": "Present search results to user"
            }
        
    async def _generate_product_response(self, original_message: str, results: List[Dict[str, Any]], 
                                    tool_plan: Dict[str, Any]) -> str:
        """Return raw tool results instead of generating a natural response."""
        
        # Extract product data from results
        product_results = []
        for result in results:
            if 'result' in result and result['result']:
                tool_result = result['result']
                if tool_result.get('success') or tool_result.get('status'):
                    # Extract the actual product data
                    products = tool_result.get('products', [])
                    logger.debug(f"===========Products: {products} ===========")
                    if products:
                        for product in products:
                            product_data = {
                                'id': product.get('id', ''),
                                'name': product.get('name', ''),
                                'description': product.get('description', ''),
                                'price': product.get('price', ''),
                                'categories': product.get('categories', []),
                                'image_url': product.get('picture', ''),
                                'target_tags': product.get('target_tags', []),
                                'use_context': product.get('use_context', [])
                            }
                            product_results.append(product_data)
        
        # Build response with raw data
        response_parts = []
        
        if product_results:
            response_parts.append("**Product Search Results:**")
            for i, product in enumerate(product_results, 1):
                response_parts.append(f"\n**Product {i}:**")
                response_parts.append(f"ID: {product['id']}")
                response_parts.append(f"Name: {product['name']}")
                response_parts.append(f"Description: {product['description']}")
                response_parts.append(f"Price: {product['price']}")
                response_parts.append(f"Categories: {product['categories']}")
                response_parts.append(f"Target Tags: {product['target_tags']}")
                response_parts.append(f"Use Context: {product['use_context']}")
                response_parts.append(f"Image: {product['image_url']}")
        else:
            response_parts.append("No products found matching your search criteria.")
        
        return "\n".join(response_parts)