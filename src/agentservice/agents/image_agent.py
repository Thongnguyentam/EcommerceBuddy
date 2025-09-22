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
import re
from typing import Dict, Any, List, Optional
from base_agent import BaseAgent
from utils import clean_and_parse_json, extract_parameters_safely

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
            # Extract URLs from the message and context first
            urls = self._extract_urls(message, context)
            
            # Analyze request and determine tools to use
            available_tools = self.get_available_tools()
            tool_plan = await self._plan_tool_usage(message, available_tools, context, urls)
            
            # Execute tools
            results = []
            tools_called = []
            
            for tool_call in tool_plan.get('tools_to_call', []):
                try:
                    tool_name = tool_call['tool_name']
                    parameters = tool_call['parameters']
                    
                    # Validate and enhance parameters
                    parameters = self._validate_and_enhance_parameters(tool_name, parameters, urls, message, context)
                    
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
    
    def _extract_urls(self, message: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, List[str]]:
        """Extract URLs from message and context, including GCS URLs."""
        urls = {
            "all_urls": [],
            "image_urls": [],
            "potential_base_urls": [],
            "potential_product_urls": []
        }
        
        # Enhanced URL pattern matching to include GCS and other cloud storage URLs
        url_patterns = [
            # Standard HTTP/HTTPS URLs
            r'https?://[^\s<>"{}|\\^`\[\]]+(?:\.[^\s<>"{}|\\^`\[\]]+)*',
            # Google Cloud Storage URLs
            r'gs://[^\s<>"{}|\\^`\[\]]+',
            # Google Cloud Storage HTTP URLs
            r'https://storage\.googleapis\.com/[^\s<>"{}|\\^`\[\]]+',
            r'https://storage\.cloud\.google\.com/[^\s<>"{}|\\^`\[\]]+',
            # Firebase Storage URLs
            r'https://firebasestorage\.googleapis\.com/[^\s<>"{}|\\^`\[\]]+',
            # AWS S3 URLs
            r'https://[^.\s]+\.s3\.amazonaws\.com/[^\s<>"{}|\\^`\[\]]+',
            r's3://[^\s<>"{}|\\^`\[\]]+',
            # Azure Blob Storage URLs
            r'https://[^.\s]+\.blob\.core\.windows\.net/[^\s<>"{}|\\^`\[\]]+',
        ]
        
        # Extract from message
        for pattern in url_patterns:
            message_urls = re.findall(pattern, message, re.IGNORECASE)
            urls["all_urls"].extend(message_urls)
        
        # Extract from context
        if context:
            for key, value in context.items():
                if isinstance(value, str):
                    for pattern in url_patterns:
                        context_urls = re.findall(pattern, value, re.IGNORECASE)
                        urls["all_urls"].extend(context_urls)
                    
                    # Map specific context keys to URL types
                    if key in ['base_image_url', 'room_image_url', 'scene_url']:
                        urls["potential_base_urls"].extend([url for url in urls["all_urls"] if url in value])
                    elif key in ['product_image_url', 'product_url', 'item_url']:
                        urls["potential_product_urls"].extend([url for url in urls["all_urls"] if url in value])
        
        # Remove duplicates while preserving order
        urls["all_urls"] = list(dict.fromkeys(urls["all_urls"]))
        
        # Classify URLs as likely image URLs based on extension, path, or cloud storage patterns
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg', '.tiff', '.ico']
        image_keywords = ['image', 'photo', 'picture', 'img', 'pic', 'thumbnail', 'avatar']
        
        for url in urls["all_urls"]:
            url_lower = url.lower()
            
            # Check for image file extensions
            if any(url_lower.endswith(ext) for ext in image_extensions):
                urls["image_urls"].append(url)
            # Check for image-related keywords in URL
            elif any(keyword in url_lower for keyword in image_keywords):
                urls["image_urls"].append(url)
            # GCS and cloud storage URLs are often images if they don't have obvious non-image extensions
            elif any(url_lower.startswith(prefix) for prefix in ['gs://', 'https://storage.googleapis.com/', 'https://firebasestorage.googleapis.com/']):
                # Assume cloud storage URLs are images unless they have non-image extensions
                non_image_extensions = ['.txt', '.json', '.xml', '.html', '.css', '.js', '.pdf', '.doc', '.docx']
                if not any(url_lower.endswith(ext) for ext in non_image_extensions):
                    urls["image_urls"].append(url)
            # S3 and Azure blob URLs - similar logic
            elif any(pattern in url_lower for pattern in ['.s3.amazonaws.com/', 's3://', '.blob.core.windows.net/']):
                non_image_extensions = ['.txt', '.json', '.xml', '.html', '.css', '.js', '.pdf', '.doc', '.docx']
                if not any(url_lower.endswith(ext) for ext in non_image_extensions):
                    urls["image_urls"].append(url)
        
        # If no specific classification, treat all URLs as potential image URLs
        if not urls["image_urls"] and urls["all_urls"]:
            urls["image_urls"] = urls["all_urls"][:]
        
        # Remove duplicates from image URLs
        urls["image_urls"] = list(dict.fromkeys(urls["image_urls"]))
        urls["potential_base_urls"] = list(dict.fromkeys(urls["potential_base_urls"]))
        urls["potential_product_urls"] = list(dict.fromkeys(urls["potential_product_urls"]))
        
        logger.info(f"Extracted URLs: {len(urls['all_urls'])} total, {len(urls['image_urls'])} image URLs")
        logger.debug(f"Image URLs found: {urls['image_urls'][:3]}...")  # Log first 3 URLs for debugging
        return urls
    
    async def _plan_tool_usage(self, message: str, available_tools: List[Dict[str, Any]], 
                              context: Optional[Dict[str, Any]] = None, 
                              urls: Optional[Dict[str, List[str]]] = None) -> Dict[str, Any]:
        """Plan which tools to use for the image request."""
        
        # Create enhanced prompt with URL information
        prompt = self.create_tool_calling_prompt(message, available_tools)
        
        # Add image-specific guidance with URL context
        prompt += f"""

Context: {json.dumps(context) if context else "None"}
Available URLs: {urls['all_urls'] if urls else []}
Image URLs detected: {urls['image_urls'] if urls else []}

Image-specific guidelines:
- Use analyze_image when user wants to understand what's in an image (objects, style, colors)
- Use visualize_product when user wants to see how a product would look in their space
- For analyze_image: requires image_url parameter
- For visualize_product: requires base_image_url, product_image_url, and prompt parameters
- Always extract URLs from the user message or context
- If multiple URLs are provided, determine which is the base image and which is the product

Examples:
- "What's in this image? [URL]" → analyze_image with image_url
- "Show me how this couch would look in my room [room_URL] [couch_URL]" → visualize_product
- "Analyze my living room [URL]" → analyze_image with image_url

URL Assignment Rules:
- For visualization: First URL or room/scene context → base_image_url, Second URL or product context → product_image_url
- For analysis: Any single URL → image_url
- Always include URLs in parameters, never leave them empty"""

        try:
            response = await self.generate_response(prompt)
            tool_plan = clean_and_parse_json(response)
            
            # Validate and enhance the tool plan with URL information
            tool_plan = self._enhance_tool_plan_with_urls(tool_plan, urls, message, context)
            
            return tool_plan
            
        except Exception as e:
            logger.error(f"Image tool planning failed: {str(e)}")
            # Create intelligent fallback based on URLs and message content
            return self._create_fallback_tool_plan(message, urls, context)
    
    def _enhance_tool_plan_with_urls(self, tool_plan: Dict[str, Any], 
                                   urls: Optional[Dict[str, List[str]]], 
                                   message: str, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Enhance tool plan by ensuring URLs are properly assigned to parameters."""
        
        if not urls or not urls.get('all_urls'):
            return tool_plan
        
        enhanced_tools = []
        for tool_call in tool_plan.get('tools_to_call', []):
            tool_name = tool_call.get('tool_name')
            parameters = tool_call.get('parameters', {})
            
            if tool_name == 'analyze_image':
                # Ensure image_url is set
                if not parameters.get('image_url') and urls['image_urls']:
                    parameters['image_url'] = urls['image_urls'][0]
                
                # Add context if not present
                if not parameters.get('context') and context:
                    parameters['context'] = message[:200]  # First 200 chars as context
            
            elif tool_name == 'visualize_product':
                # Ensure both URLs are set for visualization
                if not parameters.get('base_image_url'):
                    if urls['potential_base_urls']:
                        parameters['base_image_url'] = urls['potential_base_urls'][0]
                    elif len(urls['image_urls']) >= 2:
                        parameters['base_image_url'] = urls['image_urls'][0]
                    elif urls['image_urls']:
                        parameters['base_image_url'] = urls['image_urls'][0]
                
                if not parameters.get('product_image_url'):
                    if urls['potential_product_urls']:
                        parameters['product_image_url'] = urls['potential_product_urls'][0]
                    elif len(urls['image_urls']) >= 2:
                        parameters['product_image_url'] = urls['image_urls'][1]
                    elif len(urls['image_urls']) == 1 and parameters.get('base_image_url'):
                        # If we only have one URL and it's already used as base, we need to ask for product URL
                        logger.warning("Only one URL available for visualization, need both base and product URLs")
                
                # Ensure prompt is set
                if not parameters.get('prompt'):
                    parameters['prompt'] = f"Show how this product would look in the space: {message[:100]}"
            
            enhanced_tools.append({
                'tool_name': tool_name,
                'parameters': parameters,
                'reasoning': tool_call.get('reasoning', f'Enhanced parameters for {tool_name}')
            })
        
        tool_plan['tools_to_call'] = enhanced_tools
        return tool_plan
    
    def _create_fallback_tool_plan(self, message: str, urls: Optional[Dict[str, List[str]]], 
                                 context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Create fallback tool plan when planning fails."""
        
        if not urls or not urls.get('image_urls'):
            return {
                "reasoning": "No URLs found in message or context",
                "tools_to_call": [],
                "response_strategy": "Ask user to provide image URLs"
            }
        
        # Determine tool based on number of URLs and message content
        visualize_keywords = ['visualize', 'show', 'place', 'put', 'how would', 'look in']
        analyze_keywords = ['analyze', 'what', 'describe', 'identify', 'objects', 'scene']
        
        message_lower = message.lower()
        is_visualization = any(keyword in message_lower for keyword in visualize_keywords)
        is_analysis = any(keyword in message_lower for keyword in analyze_keywords)
        
        # If we have 2+ URLs and visualization intent, use visualize_product
        if len(urls['image_urls']) >= 2 and (is_visualization or not is_analysis):
            return {
                "reasoning": "Multiple URLs detected with visualization intent",
                "tools_to_call": [
                    {
                        "tool_name": "visualize_product",
                        "parameters": {
                            "base_image_url": urls['image_urls'][0],
                            "product_image_url": urls['image_urls'][1],
                            "prompt": f"Visualize this product in the space: {message[:100]}"
                        },
                        "reasoning": "Using first URL as base image and second as product"
                    }
                ],
                "response_strategy": "Show visualization result"
            }
        
        # Default to image analysis
        return {
            "reasoning": "Single URL or analysis intent detected",
            "tools_to_call": [
                {
                    "tool_name": "analyze_image",
                    "parameters": {
                        "image_url": urls['image_urls'][0],
                        "context": message[:200]
                    },
                    "reasoning": "Analyzing the provided image"
                }
            ],
            "response_strategy": "Describe image analysis results"
        }
    
    def _validate_and_enhance_parameters(self, tool_name: str, parameters: Dict[str, Any], 
                                       urls: Dict[str, List[str]], message: str, 
                                       context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate and enhance parameters before tool call."""
        
        # Get tool schema for validation
        tool_schema = None
        for tool in self.get_available_tools():
            if tool['name'] == tool_name:
                tool_schema = tool
                break
        
        if not tool_schema:
            logger.warning(f"No schema found for tool: {tool_name}")
            return parameters
        
        enhanced_params = parameters.copy()
        schema_params = tool_schema.get('parameters', {})
        
        # Validate required parameters and provide defaults
        for param_name, param_info in schema_params.items():
            if param_name not in enhanced_params or not enhanced_params[param_name]:
                # Try to fill missing parameters
                if param_name == 'image_url' and urls.get('image_urls'):
                    enhanced_params[param_name] = urls['image_urls'][0]
                elif param_name == 'base_image_url' and urls.get('image_urls'):
                    enhanced_params[param_name] = urls['image_urls'][0]
                elif param_name == 'product_image_url' and len(urls.get('image_urls', [])) > 1:
                    enhanced_params[param_name] = urls['image_urls'][1]
                elif param_name == 'prompt' and not enhanced_params.get('prompt'):
                    enhanced_params[param_name] = f"Process this request: {message[:100]}"
                elif param_name == 'context' and not enhanced_params.get('context'):
                    enhanced_params[param_name] = message[:200]
        
        # Log parameter validation
        logger.info(f"Enhanced parameters for {tool_name}: {list(enhanced_params.keys())}")
        
        return enhanced_params
    
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
                if result.get('result', {}).get('success'):
                    results_summary.append("Image analysis completed successfully")
                else:
                    results_summary.append("Image analysis failed")
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