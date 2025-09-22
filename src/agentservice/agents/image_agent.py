"""
Image Agent

Specializes in:
- Image analysis and scene understanding
- Product visualization in user photos
- Room analysis for product recommendations
"""

import json
import logging
import uuid
from typing import Dict, Any, List, Optional
from base_agent import BaseAgent
from utils import clean_and_parse_json

logger = logging.getLogger(__name__)

class ImageAgent(BaseAgent):
    """Agent specialized in image analysis and product visualization."""
    
    @property
    def name(self) -> str:
        return "Image Agent"
    
    @property
    def description(self) -> str:
        return "Specialized in image analysis and product visualization using AI"
    
    @property
    def domain_tools(self) -> List[str]:
        return [
            "analyze_image",
            "visualize_product"
        ]
    
    async def process_request(self, message: str, user_id: Optional[str] = None,
                            session_id: Optional[str] = None, 
                            context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process an image-related request."""
        
        if not session_id:
            session_id = str(uuid.uuid4())
        
        try:
            # Analyze request and determine tools to use
            available_tools = self.get_available_tools()
            tool_plan = await self._plan_tool_usage(message, available_tools, context)
            
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
                    logger.error(f"Image agent tool call failed: {tool_call['tool_name']} - {str(e)}")
                    results.append({
                        'tool': tool_call['tool_name'],
                        'error': str(e)
                    })
            
            # Generate response based on results
            response = await self._generate_image_response(message, results, tool_plan)
            
            # Update session
            self.update_session(session_id, message, response, tools_called)
            
            return {
                "response": response,
                "agent_used": "image",
                "tools_called": tools_called,
                "session_id": session_id
            }
            
        except Exception as e:
            logger.error(f"Image agent request processing failed: {str(e)}")
            return {
                "response": f"I apologize, but I encountered an error processing your image request: {str(e)}",
                "agent_used": "image",
                "tools_called": [],
                "session_id": session_id
            }
    
    async def _plan_tool_usage(self, message: str, available_tools: List[Dict[str, Any]], 
                              context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Plan which tools to use for the image request."""
        
        prompt = self.create_tool_calling_prompt(message, available_tools)
        
        # Add image-specific guidance
        prompt += f"""

Context: {json.dumps(context) if context else "None"}

Image-specific guidelines:
- Use analyze_image when user wants to understand what's in an image (objects, style, colors)
- Use visualize_product when user wants to see how a product would look in their space
- For visualization, you need both a base image (room/scene) and product image URLs
- Analysis can help understand room style before making product recommendations

Examples:
- "What's in this image?" → analyze_image
- "Show me how this couch would look in my room" → visualize_product
- "Analyze my living room" → analyze_image"""

        try:
            response = await self.generate_response(prompt)
            return clean_and_parse_json(response)
            
        except Exception as e:
            logger.error(f"Image tool planning failed: {str(e)}")
            # Fallback based on context
            if context and context.get('base_image_url') and context.get('product_image_url'):
                return {
                    "reasoning": "Fallback to product visualization",
                    "tools_to_call": [
                        {
                            "tool_name": "visualize_product",
                            "parameters": {
                                "base_image_url": context['base_image_url'],
                                "product_image_url": context['product_image_url'],
                                "prompt": message
                            },
                            "reasoning": "Using visualization as fallback"
                        }
                    ],
                    "response_strategy": "Show visualization result"
                }
            else:
                return {
                    "reasoning": "Need more information for image processing",
                    "tools_to_call": [],
                    "response_strategy": "Ask for image URLs or clarification"
                }
    
    async def _generate_image_response(self, original_message: str, results: List[Dict[str, Any]], 
                                     tool_plan: Dict[str, Any]) -> str:
        """Generate a natural response based on image processing results."""
        
        # Extract URLs directly from results to avoid Gemini processing them
        visualization_urls = []
        for result in results:
            if result.get('tool') == 'visualize_product' and 'result' in result:
                tool_result = result['result']
                if tool_result.get('success') and 'visualization' in tool_result:
                    render_url = tool_result['visualization'].get('render_url')
                    if render_url:
                        visualization_urls.append(render_url)
        
        # Create a simplified prompt without the full JSON to avoid URL encoding issues
        results_summary = []
        for result in results:
            if 'error' in result:
                results_summary.append(f"Error with {result.get('tool', 'unknown tool')}: {result['error']}")
            elif result.get('tool') == 'analyze_image':
                results_summary.append("Image analysis completed successfully")
            elif result.get('tool') == 'visualize_product':
                if result.get('result', {}).get('success'):
                    results_summary.append("Product visualization completed successfully")
                else:
                    results_summary.append("Product visualization failed")
        
        response_prompt = f"""Generate a helpful response for an image processing request.

Original request: {original_message}
Strategy: {tool_plan.get('response_strategy', 'Present results')}

Results summary: {'; '.join(results_summary)}

Create a response that:
1. Acknowledges what the user requested
2. Describes what was found or created clearly
3. For visualizations, mentions that an image was generated
4. Is conversational and helpful

Do not include any URLs in your response - they will be added separately.

Response:"""

        try:
            base_response = await self.generate_response(response_prompt)
            base_response = base_response.strip()
            
            # Add visualization URLs directly without letting Gemini process them
            if visualization_urls:
                base_response += "\n\n"
                for i, url in enumerate(visualization_urls, 1):
                    base_response += f"[Generated Image {i}]({url})\n\n"
                base_response += "Take a look and see how it fits with your decor. Would you like to try visualizing it in another spot, or perhaps with a different product?"
            
            return base_response
            
        except Exception as e:
            logger.error(f"Image response generation failed: {str(e)}")
            
            # Fallback response with direct URL if available
            if visualization_urls:
                return f"I've generated a visualization for you! You can view it here: {visualization_urls[0]}"
            elif results and any('result' in r for r in results):
                return "I've processed your image request. The results are ready for you to view!"
            else:
                return "I wasn't able to process your image request. Please make sure you've provided valid image URLs and try again." 