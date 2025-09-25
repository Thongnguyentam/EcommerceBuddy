"""
Cart Agent

Specializes in:
- Shopping cart management
- Adding/removing items from cart
- Cart contents viewing
- Cart operations
"""

import json
import logging
import uuid
from typing import Dict, Any, List, Optional
from agents.base_agent import BaseAgent
from agents.utils import clean_and_parse_json, validate_tool_plan
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
class CartAgent(BaseAgent):
    """Agent specialized in shopping cart operations."""
    
    @property
    def name(self) -> str:
        return "Cart Agent"
    
    @property
    def description(self) -> str:
        return "Specialized in shopping cart management and operations"
    
    @property
    def domain_tools(self) -> List[str]:
        return [
            "add_to_cart",
            "get_cart_contents",
            "clear_cart"
        ]
    
    async def process_request(self, message: str, user_id: Optional[str] = None,
                            session_id: Optional[str] = None, 
                            context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process a cart-related request."""
        
        if not session_id:
            session_id = str(uuid.uuid4())
        
        if not user_id:
            return {
                "response": "I need a user ID to manage your shopping cart. Please provide your user identifier.",
                "agent_used": "cart",
                "tools_called": [],
                "session_id": session_id
            }
        
        try:
            # Analyze request and determine tools to use
            available_tools = self.get_available_tools()
            tool_plan = await self._plan_tool_usage(message, available_tools, user_id, context)
            logger.info(f"CartAgent tool plan: {tool_plan}")
            
            # Execute tools
            results = []
            tools_called = []
            
            for tool_call in tool_plan.get('tools_to_call', []):
                try:
                    tool_name = tool_call['tool_name']
                    parameters = tool_call['parameters']
                    
                    # Ensure user_id is included
                    parameters['user_id'] = user_id
                    
                    result = await self.call_tool(tool_name, parameters)
                    results.append({
                        'tool': tool_name,
                        'result': result
                    })
                    tools_called.append(tool_name)
                    
                except Exception as e:
                    logger.error(f"Cart agent tool call failed: {tool_call['tool_name']} - {str(e)}")
                    results.append({
                        'tool': tool_call['tool_name'],
                        'error': str(e)
                    })
            
            # Generate response based on results
            response = await self._generate_cart_response(message, results, tool_plan)
            
            # Update session
            self.update_session(session_id, message, response, tools_called)
            
            return {
                "response": response,
                "agent_used": "cart",
                "tools_called": tools_called,
                "session_id": session_id
            }
            
        except Exception as e:
            logger.error(f"Cart agent request processing failed: {str(e)}")
            return {
                "response": f"I apologize, but I encountered an error managing your cart: {str(e)}",
                "agent_used": "cart",
                "tools_called": [],
                "session_id": session_id
            }
    
    async def _plan_tool_usage(self, message: str, available_tools: List[Dict[str, Any]], 
                              user_id: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Plan which tools to use for the cart request."""
        
        prompt = self.create_tool_calling_prompt(message, available_tools)
        
        # Add cart-specific guidance
        prompt += f"""
Context for previous steps: {json.dumps(context) if context else "No context"}

User ID: {user_id}

Cart-specific guidelines:
- Use add_to_cart when user wants to add items (need product_id and quantity)
- Use get_cart_contents when user wants to see what's in their cart
- Use clear_cart when user wants to empty their cart
- Always include user_id in parameters

IMPORTANT: If context contains responses from other agents, use that information to identify products to work with the cart.
- If context has product_agent_response with product IDs, use those IDs
- If context has image_agent_response with product recommendations, operate on those products to cart
- If context has sentiment_agent_response with product IDs, operate on those products to cart

Context Analysis:
- Check if context contains product data with product IDs

Examples:
- "Add this item to my cart" → add_to_cart (need to identify product_id from context)
- "What's in my cart?" → get_cart_contents
- "Clear my cart" → clear_cart
- "Remove everything" → clear_cart"""

        try:
            response = await self.generate_response(prompt)
            parsed_plan = clean_and_parse_json(response)
            return validate_tool_plan(parsed_plan)
            
        except Exception as e:
            logger.error(f"Cart tool planning failed: {str(e)}")
            # Fallback to showing cart contents
            return {
                "reasoning": "Fallback to showing cart contents",
                "tools_to_call": [
                    {
                        "tool_name": "get_cart_contents",
                        "parameters": {"user_id": user_id},
                        "reasoning": "Default to showing current cart"
                    }
                ],
                "response_strategy": "Show current cart contents"
            }
        
    async def _generate_cart_response(self, original_message: str, results: List[Dict[str, Any]], 
                                    tool_plan: Dict[str, Any]) -> str:
        """Return raw tool results instead of generating a natural response."""
        
        # Extract cart data from results
        cart_results = []
        operation_results = []
        
        for result in results:
            if 'result' in result and result['result']:
                tool_result = result['result']
                logger.debug(f"===========Cart tool result: {tool_result} ===========")
                
                if tool_result.get('status') == 'ok':
                    # Handle different cart operations
                    if 'items' in tool_result:
                        # Cart contents response
                        cart_data = {
                            'user_id': tool_result.get('user_id', ''),
                            'items': tool_result.get('items', []),
                            'total_items': tool_result.get('total_items', 0),
                            'status': tool_result.get('status', '')
                        }
                        cart_results.append(cart_data)
                    
                    elif 'message' in tool_result:
                        # Operation response (add, clear)
                        operation_data = {
                            'status': tool_result.get('status', ''),
                            'message': tool_result.get('message', ''),
                            'operation': result.get('tool', 'unknown')
                        }
                        operation_results.append(operation_data)
        
        # Build response with raw data
        response_parts = []
        logger.debug(f"===========Cart results: {cart_results} ===========")
        logger.debug(f"===========Operation results: {operation_results} ===========")
        
        if cart_results:
            response_parts.append("**Cart Contents:**")
            for cart in cart_results:
                response_parts.append(f"User ID: {cart['user_id']}")
                response_parts.append(f"Total Items: {cart['total_items']}")
                response_parts.append(f"Status: {cart['status']}")
                
                if cart['items']:
                    response_parts.append("\n**Items in Cart:**")
                    for i, item in enumerate(cart['items'], 1):
                        response_parts.append(f"  {i}. Product ID: {item.get('product_id', 'N/A')}")
                        response_parts.append(f"     Quantity: {item.get('quantity', 'N/A')}")
                else:
                    response_parts.append("Cart is empty")
        
        if operation_results:
            response_parts.append("**Cart Operations:**")
            for operation in operation_results:
                response_parts.append(f"Operation: {operation['operation']}")
                response_parts.append(f"Status: {operation['status']}")
                response_parts.append(f"Message: {operation['message']}")
        
        if not response_parts:
            response_parts.append("No cart data available.")
        
        return "\n".join(response_parts)