"""
Sentiment Agent

Specializes in:
- Product review analysis
- Sentiment evaluation of reviews
- Review management and insights
- Product rating analysis
"""

import json
import logging
import uuid
from typing import Dict, Any, List, Optional
from agents.base_agent import BaseAgent
from agents.utils import clean_and_parse_json, validate_tool_plan

logger = logging.getLogger(__name__)

class SentimentAgent(BaseAgent):
    """Agent specialized in review analysis and sentiment evaluation."""
    
    @property
    def name(self) -> str:
        return "Sentiment Agent"
    
    @property
    def description(self) -> str:
        return "Specialized in review analysis, sentiment evaluation, and product ratings"
    
    @property
    def domain_tools(self) -> List[str]:
        return [
            "create_review",
            "get_product_reviews",
            "get_user_reviews",
            "update_review",
            "delete_review",
            "get_product_review_summary"
        ]
    
    async def process_request(self, message: str, user_id: Optional[str] = None,
                            session_id: Optional[str] = None, 
                            context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process a sentiment/review-related request."""
        
        if not session_id:
            session_id = str(uuid.uuid4())
        
        try:
            # Analyze request and determine tools to use
            available_tools = self.get_available_tools()
            tool_plan = await self._plan_tool_usage(message, available_tools, user_id)
            
            # Execute tools
            results = []
            tools_called = []
            
            for tool_call in tool_plan.get('tools_to_call', []):
                try:
                    tool_name = tool_call['tool_name']
                    parameters = tool_call['parameters']
                    
                    # Add user_id if needed and available
                    if user_id and 'user_id' in parameters:
                        parameters['user_id'] = user_id
                    
                    result = await self.call_tool(tool_name, parameters)
                    results.append({
                        'tool': tool_name,
                        'result': result
                    })
                    tools_called.append(tool_name)
                    
                except Exception as e:
                    logger.error(f"Sentiment agent tool call failed: {tool_call['tool_name']} - {str(e)}")
                    results.append({
                        'tool': tool_call['tool_name'],
                        'error': str(e)
                    })
            
            # Generate response based on results
            response = await self._generate_sentiment_response(message, results, tool_plan)
            
            # Update session
            self.update_session(session_id, message, response, tools_called)
            
            return {
                "response": response,
                "agent_used": "sentiment",
                "tools_called": tools_called,
                "session_id": session_id
            }
            
        except Exception as e:
            logger.error(f"Sentiment agent request processing failed: {str(e)}")
            return {
                "response": f"I apologize, but I encountered an error analyzing reviews: {str(e)}",
                "agent_used": "sentiment",
                "tools_called": [],
                "session_id": session_id
            }
    
    async def _plan_tool_usage(self, message: str, available_tools: List[Dict[str, Any]], 
                              user_id: Optional[str] = None) -> Dict[str, Any]:
        """Plan which tools to use for the sentiment/review request."""
        
        prompt = self.create_tool_calling_prompt(message, available_tools)
        
        # Add sentiment-specific guidance
        prompt += f"""

User ID: {user_id or "Not provided"}

Review/Sentiment-specific guidelines:
- Use get_product_reviews when user asks about reviews for a specific product
- Use get_user_reviews when user wants to see their own reviews (needs user_id)
- Use create_review when user wants to write a review (needs user_id, product_id, rating)
- Use get_product_review_summary for overall sentiment analysis of a product
- Use update_review when user wants to modify an existing review
- Use delete_review when user wants to remove a review

Examples:
- "What do people think about this product?" → get_product_reviews or get_product_review_summary
- "Show me my reviews" → get_user_reviews (needs user_id)
- "I want to review this product" → create_review (needs user_id, product_id, rating, review_text)
- "How is this product rated overall?" → get_product_review_summary"""

        try:
            response = await self.generate_response(prompt)
            parsed_plan = clean_and_parse_json(response)
            return validate_tool_plan(parsed_plan)
            
        except Exception as e:
            logger.error(f"Sentiment tool planning failed: {str(e)}")
            # Fallback - if we can extract a product context, show its review summary
            return {
                "reasoning": "Fallback to general review information",
                "tools_to_call": [],
                "response_strategy": "Ask user to specify product or provide more context"
            }
    
    async def _generate_sentiment_response(self, original_message: str, results: List[Dict[str, Any]], 
                                         tool_plan: Dict[str, Any]) -> str:
        """Generate a natural response based on review/sentiment analysis results."""
        
        response_prompt = f"""Generate a helpful response for a review/sentiment analysis request.

Original request: {original_message}
Strategy: {tool_plan.get('response_strategy', 'Present results')}

Review analysis results:
{json.dumps(results, indent=2)}

Create a response that:
1. Summarizes review insights and sentiment trends
2. Highlights key positive and negative feedback
3. Provides overall rating information if available
4. Mentions review counts and patterns
5. Is conversational and insightful

For review creation/updates, confirm the action was successful.
If errors occurred, explain what went wrong and suggest alternatives.

Response:"""

        try:
            response = await self.generate_response(response_prompt)
            return response.strip()
            
        except Exception as e:
            logger.error(f"Sentiment response generation failed: {str(e)}")
            
            # Fallback response based on results
            if results and any('result' in r for r in results):
                return "I've analyzed the review information. The sentiment analysis shows mixed feedback with some interesting patterns!"
            else:
                return "I wasn't able to analyze the reviews for that product. Please specify which product you'd like me to analyze or check if the product has any reviews." 