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
from base_agent import BaseAgent
from utils import clean_and_parse_json, validate_tool_plan
logger = logging.getLogger(__name__)

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
            # Analyze request and determine tools to use
            available_tools = self.get_available_tools()
            tool_plan = await self._plan_tool_usage(message, available_tools)
            
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
    
    async def _plan_tool_usage(self, message: str, available_tools: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Plan which tools to use for the product request."""
        
        prompt = self.create_tool_calling_prompt(message, available_tools)
        
        # Add product-specific guidance
        prompt += """

Product-specific guidelines:
- Use semantic_search_products for natural language queries about product features or style
- Use search_products for keyword-based searches  
- Use get_products_by_category when user mentions specific categories
- Use list_all_products only when user wants to browse everything
- Use get_product_by_id when user mentions a specific product ID

Examples:
- "Find me a red couch" → semantic_search_products with query "red couch"
- "Show me kitchen items" → get_products_by_category with category "kitchen"
- "What products do you have?" → list_all_products"""

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
        """Generate a natural response based on product search results."""
        
        response_prompt = f"""Generate a helpful response for a product search request.

Original request: {original_message}
Strategy: {tool_plan.get('response_strategy', 'Present results')}

Search results:
{json.dumps(results, indent=2)}

Create a response that:
1. Acknowledges what the user was looking for
2. Presents the most relevant products clearly
3. Highlights key features and prices
4. Suggests next steps (like adding to cart)
5. Is conversational and helpful

If no products found, suggest alternatives or broader searches.
If errors occurred, acknowledge them gracefully.

Response:"""

        try:
            response = await self.generate_response(response_prompt)
            return response.strip()
            
        except Exception as e:
            logger.error(f"Product response generation failed: {str(e)}")
            
            # Fallback response based on results
            if results and any('result' in r for r in results):
                return "I found some products that might interest you. Let me know if you'd like more details about any of them!"
            else:
                return "I wasn't able to find products matching your request. Could you try a different search term or browse our categories?" 