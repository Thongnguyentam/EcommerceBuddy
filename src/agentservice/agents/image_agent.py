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
from agents.base_agent import BaseAgent
from agents.utils import clean_and_parse_json, extract_parameters_safely

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.DEBUG,  # show DEBUG and above
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger.setLevel(logging.DEBUG)
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
            logger.info(f"ImageAgent tool plan: {tool_plan}")
            
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
        """Extract image URLs from context (frontend uploads)."""
        urls = {
            "all_urls": [],
            "image_urls": [],
            "potential_base_urls": [],
            "potential_product_urls": []
        }
        
        # Check for image_url in context (from frontend upload)
        if context and 'image_url' in context:
            image_url = context['image_url']
            urls["all_urls"].append(image_url)
            urls["image_urls"].append(image_url)
            # User uploaded image is typically the base/room image
            urls["potential_base_urls"].append(image_url)
            
            logger.debug(f"Found uploaded image URL in context: {image_url}...")
        else:
            logger.debug("No image_url found in context - user may not have uploaded an image")
        
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

IMPORTANT: If context contains responses from other agents, use that information to enhance image processing.
- If context has product_agent_response with product images urls, use those for visualization or analysis
- Look for product information in the context and use those products' images urls for visualization or analysis

Context Analysis:
- Check if context contains product data with product images urls
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
        logger.debug(f"Enhanced parameters for {tool_name}: {list(enhanced_params.keys())}")
        
        return enhanced_params
    
    async def _generate_image_response(self, original_message: str, results: List[Dict[str, Any]], 
                                     tool_plan: Dict[str, Any]) -> str:
        """Return raw tool results instead of generating a natural response."""
        
        # Extract URLs directly from results
        visualization_urls = []
        analysis_results = []
        
        for result in results:
            if result.get('tool') == 'visualize_product' and 'result' in result:
                tool_result = result['result']
                if (tool_result.get('success') or tool_result.get('status')) and 'visualization' in tool_result:
                    render_url = tool_result['visualization'].get('render_url')
                    logger.debug(f"===========Render url: {render_url} ===========")
                    if render_url:
                        visualization_urls.append(render_url)
            elif result.get('tool') == 'analyze_image' and 'result' in result:
                tool_result = result['result']
                if tool_result.get('success') or tool_result.get('status'):                    # Extract the actual analysis data
                    analysis_data_dict = tool_result.get('analysis', {})
                    logger.debug(f"===========Analysis data dictionary: {analysis_data_dict} ===========")
                    analysis_data = {
                        'objects': analysis_data_dict.get('objects', []),
                        'scene_type': analysis_data_dict.get('scene_type', ''),
                        'styles': analysis_data_dict.get('styles', []),
                        'colors': analysis_data_dict.get('colors', []),
                        'tags': analysis_data_dict.get('tags', [])
                    }
                    analysis_results.append(analysis_data)
        
        # Build response with raw data
        response_parts = []
        logger.debug(f"===========Analysis results: {analysis_results} ===========")
        logger.debug(f"===========Visualization urls: {visualization_urls} ===========")
        if analysis_results:
            response_parts.append("**Image Analysis Results:**")
            for analysis in analysis_results:
                if analysis.get('objects'):
                    response_parts.append(f"Objects detected: {[obj.get('label', 'unknown') for obj in analysis['objects']]}")
                if analysis.get('scene_type'):
                    response_parts.append(f"Scene type: {analysis['scene_type']}")
                if analysis.get('styles'):
                    response_parts.append(f"Styles: {analysis['styles']}")
                if analysis.get('colors'):
                    response_parts.append(f"Colors: {analysis['colors']}")
                if analysis.get('tags'):
                    response_parts.append(f"Tags: {analysis['tags']}")
        
        if visualization_urls:
            response_parts.append("**Visualization Results:**")
            for i, url in enumerate(visualization_urls, 1):
                response_parts.append(f"Generated image {i}: {url}")
        if not response_parts:
            return "No results available from image processing tools."
        logger.debug(f"===========Response parts: {response_parts} ===========")
        return "\n\n".join(response_parts)
    