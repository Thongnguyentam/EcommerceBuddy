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
logger.setLevel(logging.DEBUG)
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
            tool_plan = await self._plan_tool_usage(message, available_tools, user_id, context)
            logger.info(f"SentimentAgent tool plan: {tool_plan}")
            
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
                              user_id: Optional[str] = None, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Plan which tools to use for the sentiment/review request."""
        
        prompt = self.create_tool_calling_prompt(message, available_tools)
        
        # Add sentiment-specific guidance
        prompt += f"""
Context for previous steps: {json.dumps(context) if context else "No context"}

User ID: {user_id or "Not provided"}

Review/Sentiment-specific guidelines:
- Use get_product_reviews when user asks about reviews for a specific product
- Use get_user_reviews when user wants to see their own reviews (needs user_id)
- Use create_review when user wants to write a review (needs user_id, product_id, rating)
- Use get_product_review_summary for overall sentiment analysis of a product
- Use update_review when user wants to modify an existing review
- Use delete_review when user wants to remove a review

IMPORTANT: If context contains responses from other agents (like product_agent_response), use that information to find product IDs and get their reviews.
- If context has product data with product IDs, use those IDs to get reviews
- If context has product_agent_response, parse it for product IDs and get reviews for those products
- Look for product information in the context and get reviews for those products
- If context contains product recommendations, get reviews for the top products

Examples:
- "What do people think about this product?" → get_product_reviews or get_product_review_summary
- "Show me my reviews" → get_user_reviews (needs user_id)
- "I want to review this product" → create_review (needs user_id, product_id, rating, review_text)
- "How is this product rated overall?" → get_product_review_summary

Context Analysis:
- Check if context contains product data with product IDs
- Look for product recommendations in the context
- Extract product IDs from context and get reviews for those products
- If multiple products are found in context, get reviews for the top-rated or most relevant ones

"""

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
        """Return raw tool results instead of generating a natural response."""
        
        # Extract review/sentiment data from results
        review_results = []
        summary_results = []
        
        for result in results:
            if 'result' in result and result['result']:
                tool_result = result['result']
                logger.debug(f"===========Tool result: {tool_result} ===========")
                if tool_result.get('status') == 'ok':
                    # Extract the actual review/sentiment data
                    if 'reviews' in tool_result:
                        # Handle review data
                        reviews = tool_result.get('reviews', [])
                        logger.debug(f"===========Reviews: {reviews} ===========")
                        for review in reviews:
                            review_data = {
                                'id': review.get('id', ''),
                                'user_id': review.get('user_id', ''),
                                'product_id': review.get('product_id', ''),
                                'rating': review.get('rating', ''),
                                'review_text': review.get('review_text', ''),
                                'created_at': review.get('created_at', ''),
                                'updated_at': review.get('updated_at', '')
                            }
                            review_results.append(review_data)
                    
                    elif 'summary' in tool_result:
                        # Handle summary data
                        summary_dict = tool_result.get('summary', {})
                        summary_data = {
                            'product_id': summary_dict.get('product_id', ''),
                            'average_rating': summary_dict.get('average_rating', ''),
                            'total_reviews': summary_dict.get('total_reviews', ''),
                            'rating_distribution': summary_dict.get('rating_distribution', {})
                        }
                        logger.debug(f"===========Summary data: {summary_data} ===========")
                        summary_results.append(summary_data)
                    
                    elif 'message' in tool_result:
                        # Handle operation results (create, update, delete)
                        operation_data = {
                            'status': tool_result.get('status', ''),
                            'message': tool_result.get('message', ''),
                            'review_id': tool_result.get('review_id', ''),
                            'affected_rows': tool_result.get('affected_rows', '')
                        }
                        review_results.append(operation_data)
        
        # Build response with raw data
        response_parts = []
        logger.debug(f"===========Review results: {review_results} ===========")
        logger.debug(f"===========Summary results: {summary_results} ===========")
        if review_results:
            response_parts.append("**Review/Sentiment Results:**")
            for i, review in enumerate(review_results, 1):
                response_parts.append(f"\n**Result {i}:**")
                if 'id' in review:  # Review data
                    response_parts.append(f"Review ID: {review['id']}")
                    response_parts.append(f"User ID: {review['user_id']}")
                    response_parts.append(f"Product ID: {review['product_id']}")
                    response_parts.append(f"Rating: {review['rating']}")
                    response_parts.append(f"Review Text: {review['review_text']}")
                    if review['created_at']:
                        response_parts.append(f"Created: {review['created_at']}")
                    if review['updated_at']:
                        response_parts.append(f"Updated: {review['updated_at']}")
                else:  # Operation result
                    response_parts.append(f"Status: {review['status']}")
                    response_parts.append(f"Message: {review['message']}")
                    if review['review_id']:
                        response_parts.append(f"Review ID: {review['review_id']}")
                    if review['affected_rows']:
                        response_parts.append(f"Affected Rows: {review['affected_rows']}")
        
        if summary_results:
            response_parts.append("**Review Summary Results:**")
            for i, summary in enumerate(summary_results, 1):
                response_parts.append(f"\n**Summary {i}:**")
                response_parts.append(f"Product ID: {summary['product_id']}")
                response_parts.append(f"Average Rating: {summary['average_rating']}")
                response_parts.append(f"Total Reviews: {summary['total_reviews']}")
                response_parts.append(f"Rating Distribution: {summary['rating_distribution']}")

        if not response_parts:
            response_parts.append("No review/sentiment data found.")
        
        return "\n".join(response_parts)