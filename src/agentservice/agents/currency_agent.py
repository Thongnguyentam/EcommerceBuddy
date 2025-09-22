"""
Currency Agent

Specializes in:
- Currency conversion and exchange rates
- Price formatting and display
- Multi-currency support
"""

import json
import logging
import uuid
from typing import Dict, Any, List, Optional
from agents.base_agent import BaseAgent
from agents.utils import clean_and_parse_json, validate_tool_plan
logger = logging.getLogger(__name__)

class CurrencyAgent(BaseAgent):
    """Agent specialized in currency operations."""
    
    @property
    def name(self) -> str:
        return "Currency Agent"
    
    @property
    def description(self) -> str:
        return "Specialized in currency conversion, exchange rates, and price formatting"
    
    @property
    def domain_tools(self) -> List[str]:
        return [
            "get_supported_currencies",
            "convert_currency",
            "get_exchange_rates",
            "format_money"
        ]
    
    async def process_request(self, message: str, user_id: Optional[str] = None,
                            session_id: Optional[str] = None, 
                            context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process a currency-related request."""
        
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
                    
                    result = await self.call_tool(tool_name, parameters)
                    results.append({
                        'tool': tool_name,
                        'result': result
                    })
                    tools_called.append(tool_name)
                    
                except Exception as e:
                    logger.error(f"Currency agent tool call failed: {tool_call['tool_name']} - {str(e)}")
                    results.append({
                        'tool': tool_call['tool_name'],
                        'error': str(e)
                    })
            
            # Generate response based on results
            response = await self._generate_currency_response(message, results, tool_plan)
            
            # Update session
            self.update_session(session_id, message, response, tools_called)
            
            return {
                "response": response,
                "agent_used": "currency",
                "tools_called": tools_called,
                "session_id": session_id
            }
            
        except Exception as e:
            logger.error(f"Currency agent request processing failed: {str(e)}")
            return {
                "response": f"I apologize, but I encountered an error with currency operations: {str(e)}",
                "agent_used": "currency",
                "tools_called": [],
                "session_id": session_id
            }
    
    async def _plan_tool_usage(self, message: str, available_tools: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Plan which tools to use for the currency request."""
        
        prompt = self.create_tool_calling_prompt(message, available_tools)
        
        # Add currency-specific guidance
        prompt += """

Currency-specific guidelines:
- Use convert_currency when user wants to convert between currencies (need from_currency, to_currency, amount)
- Use get_supported_currencies when user asks what currencies are available
- Use get_exchange_rates when user wants current exchange rates
- Use format_money when user wants to format an amount with currency symbol

Examples:
- "Convert $100 to EUR" → convert_currency with from_currency="USD", to_currency="EUR", amount=100
- "What currencies do you support?" → get_supported_currencies
- "Show me exchange rates" → get_exchange_rates
- "Format 50.99 as USD" → format_money with amount=50.99, currency_code="USD" """

        try:        
            response = await self.generate_response(prompt)
            parsed_plan = clean_and_parse_json(response)
            return validate_tool_plan(parsed_plan)
            
        except Exception as e:
            logger.error(f"Currency tool planning failed: {str(e)}")
            # Fallback to showing supported currencies
            return {
                "reasoning": "Fallback to showing supported currencies",
                "tools_to_call": [
                    {
                        "tool_name": "get_supported_currencies",
                        "parameters": {},
                        "reasoning": "Default to showing available currencies"
                    }
                ],
                "response_strategy": "Show available currencies"
            }
    
    async def _generate_currency_response(self, original_message: str, results: List[Dict[str, Any]], 
                                        tool_plan: Dict[str, Any]) -> str:
        """Generate a natural response based on currency operation results."""
        
        response_prompt = f"""Generate a helpful response for a currency request.

Original request: {original_message}
Strategy: {tool_plan.get('response_strategy', 'Present results')}

Currency operation results:
{json.dumps(results, indent=2)}

Create a response that:
1. Clearly shows currency conversion results or information requested
2. Includes relevant exchange rates if applicable
3. Formats monetary amounts properly
4. Provides context about the conversion or rates
5. Is conversational and helpful

If errors occurred, explain what went wrong and suggest alternatives.

Response:"""

        try:
            response = await self.generate_response(response_prompt)
            return response.strip()
            
        except Exception as e:
            logger.error(f"Currency response generation failed: {str(e)}")
            
            # Fallback response based on results
            if results and any('result' in r for r in results):
                return "I've processed your currency request. Here are the results!"
            else:
                return "I wasn't able to complete that currency operation. Please check your currency codes and amounts and try again." 