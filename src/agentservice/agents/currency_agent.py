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
            
        logger.info(f"CurrencyAgent context: {context}")
        
        try:
            # Analyze request and determine tools to use
            available_tools = self.get_available_tools()
            tool_plan = await self._plan_tool_usage(message, available_tools, context)
            logger.info(f"CurrencyAgent tool plan: {tool_plan}")
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
    
    async def _plan_tool_usage(self, 
                               message: str, 
                               available_tools: List[Dict[str, Any]], 
                               context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Plan which tools to use for the currency request."""
        
        prompt = self.create_tool_calling_prompt(message, available_tools)
        
        # Add currency-specific guidance
        prompt += f"""
Context for previous steps: {json.dumps(context) if context else "No context"}

Currency-specific guidelines:
- Use convert_currency when user wants to convert between currencies (need from_currency, to_currency, amount)
- Use get_supported_currencies when user asks what currencies are available
- Use get_exchange_rates when user wants current exchange rates
- Use format_money when user wants to format an amount with currency symbol

IMPORTANT: If context contains responses from other agents (like product_agent_response), look for product data with prices and convert them.
- If context has product data with prices, extract the prices and convert them to the requested currency
- If context has product_agent_response, parse it for product prices and convert them
- Look for price information in the context and convert to the target currency

Examples:
- "Convert $100 to EUR" → convert_currency with from_currency="USD", to_currency="EUR", amount=100
- "What currencies do you support?" → get_supported_currencies
- "Show me exchange rates" → get_exchange_rates
- "Format 50.99 as USD" → format_money with amount=50.99, currency_code="USD" 

Context Analysis:
- Check if context contains product data with prices
- Look for currency conversion requests in the user message
- Extract target currency from user message (e.g., "Japanese Yen" → "JPY")
- If product prices are found in context, convert them to the target currency

"""

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
        """Return raw tool results instead of generating a natural response."""
        
        # Extract currency data from results
        currency_results = []
        conversion_results = []
        exchange_rate_results = []
        format_results = []
        
        for result in results:
            if 'result' in result and result['result']:
                tool_result = result['result']
                logger.debug(f"===========Currency tool result: {tool_result} ===========")
                
                if tool_result.get('success'):
                    # Handle different currency operations
                    if 'currencies' in tool_result:
                        # Supported currencies response
                        currency_data = {
                            'currencies': tool_result.get('currencies', []),
                            'count': tool_result.get('count', 0),
                            'message': tool_result.get('message', ''),
                            'success': tool_result.get('success', False)
                        }
                        currency_results.append(currency_data)
                    
                    elif 'converted_amount' in tool_result:
                        # Currency conversion response
                        conversion_data = {
                            'from_currency': tool_result.get('from_currency', ''),
                            'to_currency': tool_result.get('to_currency', ''),
                            'original_amount': tool_result.get('original_amount', 0),
                            'converted_amount': tool_result.get('converted_amount', 0),
                            'currency_code': tool_result.get('currency_code', ''),
                            'units': tool_result.get('units', 0),
                            'nanos': tool_result.get('nanos', 0),
                            'message': tool_result.get('message', ''),
                            'success': tool_result.get('success', False)
                        }
                        conversion_results.append(conversion_data)
                    
                    elif 'rates' in tool_result:
                        # Exchange rates response
                        exchange_data = {
                            'base_currency': tool_result.get('base_currency', ''),
                            'rates': tool_result.get('rates', {}),
                            'count': tool_result.get('count', 0),
                            'message': tool_result.get('message', ''),
                            'success': tool_result.get('success', False)
                        }
                        exchange_rate_results.append(exchange_data)
                    
                    elif 'formatted_amount' in tool_result:
                        # Money formatting response
                        format_data = {
                            'formatted_amount': tool_result.get('formatted_amount', ''),
                            'success': tool_result.get('success', False)
                        }
                        format_results.append(format_data)
                
                elif 'error' in tool_result:
                    # Handle error responses
                    error_data = {
                        'success': False,
                        'error': tool_result.get('error', ''),
                        'operation': result.get('tool', 'unknown')
                    }
                    currency_results.append(error_data)
        
        # Build response with raw data
        response_parts = []
        logger.debug(f"===========Currency results: {currency_results} ===========")
        logger.debug(f"===========Conversion results: {conversion_results} ===========")
        logger.debug(f"===========Exchange rate results: {exchange_rate_results} ===========")
        logger.debug(f"===========Format results: {format_results} ===========")
        
        if currency_results:
            response_parts.append("**Supported Currencies:**")
            for currency in currency_results:
                if currency.get('success'):
                    response_parts.append(f"Count: {currency['count']}")
                    response_parts.append(f"Message: {currency['message']}")
                    if currency['currencies']:
                        response_parts.append(f"Currencies: {', '.join(currency['currencies'][:10])}{'...' if len(currency['currencies']) > 10 else ''}")
                else:
                    response_parts.append(f"Error: {currency.get('error', 'Unknown error')}")
        
        if conversion_results:
            response_parts.append("**Currency Conversion Results:**")
            for conversion in conversion_results:
                response_parts.append(f"From: {conversion['from_currency']}")
                response_parts.append(f"To: {conversion['to_currency']}")
                response_parts.append(f"Original Amount: {conversion['original_amount']}")
                response_parts.append(f"Converted Amount: {conversion['converted_amount']}")
                response_parts.append(f"Currency Code: {conversion['currency_code']}")
                response_parts.append(f"Units: {conversion['units']}")
                response_parts.append(f"Nanos: {conversion['nanos']}")
                response_parts.append(f"Message: {conversion['message']}")
        
        if exchange_rate_results:
            response_parts.append("**Exchange Rate Results:**")
            for exchange in exchange_rate_results:
                response_parts.append(f"Base Currency: {exchange['base_currency']}")
                response_parts.append(f"Count: {exchange['count']}")
                response_parts.append(f"Message: {exchange['message']}")
                if exchange['rates']:
                    response_parts.append("Rates:")
                    for currency, rate in list(exchange['rates'].items())[:5]:  # Show first 5 rates
                        response_parts.append(f"  {currency}: {rate}")
                    if len(exchange['rates']) > 5:
                        response_parts.append(f"  ... and {len(exchange['rates']) - 5} more rates")
        
        if format_results:
            response_parts.append("**Money Formatting Results:**")
            for format_result in format_results:
                response_parts.append(f"Formatted Amount: {format_result['formatted_amount']}")
        
        if not response_parts:
            response_parts.append("No currency data available.")
        
        return "\n".join(response_parts)