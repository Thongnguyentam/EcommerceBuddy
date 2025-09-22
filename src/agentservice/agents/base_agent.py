"""
Base Agent Class

Abstract base class for all specialized agents in the system.
Provides common functionality for tool calling, session management, and response generation.
"""

import json
import logging
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import httpx
from google import genai

logger = logging.getLogger(__name__)

class BaseAgent(ABC):
    """Abstract base class for all agents."""
    
    def __init__(self, gemini_client: genai.Client, http_client: httpx.AsyncClient, 
                 mcp_base_url: str, tools_schema: Dict[str, Any]):
        self.gemini_client = gemini_client
        self.http_client = http_client
        self.mcp_base_url = mcp_base_url
        self.tools_schema = tools_schema
        self.sessions = {}  # Simple in-memory session storage
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Agent name."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Agent description."""
        pass
    
    @property
    @abstractmethod
    def domain_tools(self) -> List[str]:
        """List of tool names this agent specializes in."""
        pass
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get tools available to this agent based on its domain."""
        available = []
        for tool in self.tools_schema.get('tools', []):
            if tool['name'] in self.domain_tools:
                available.append(tool)
        return available
    
    def update_tools_schema(self, tools_schema: Dict[str, Any]):
        """Update the tools schema."""
        self.tools_schema = tools_schema
        logger.info(f"{self.name} updated with {len(self.get_available_tools())} tools")
    
    async def call_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool via MCP server."""
        try:
            # Find the tool endpoint and method
            tool_info = None
            for tool in self.get_available_tools():
                if tool['name'] == tool_name:
                    tool_info = tool
                    break
            
            if not tool_info:
                raise ValueError(f"Tool '{tool_name}' not found in available tools")
            
            # Get endpoint and method
            tool_endpoint = tool_info['endpoint']
            method = tool_info.get('method', 'POST').upper()  # Default to POST if not specified
            
            # Make the API call
            url = f"{self.mcp_base_url}{tool_endpoint}"
            logger.info(f"{self.name} calling tool: {tool_name} -> {method} {url}")
            logger.info(f"{self.name} tool parameters: {parameters}")
            
            # Use appropriate HTTP method
            if method == 'GET':
                # For GET requests, pass parameters as query params
                response = await self.http_client.get(url, params=parameters)
            elif method == 'POST':
                # For POST requests, pass parameters as JSON body
                response = await self.http_client.post(url, json=parameters)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
                
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"{self.name} tool call successful: {tool_name}")
            return result
            
        except Exception as e:
            logger.error(f"{self.name} tool call failed: {tool_name} - {str(e)}")
            raise
    
    async def generate_response(self, prompt: str, context: Optional[str] = None) -> str:
        """Generate response using Gemini."""
        try:
            full_prompt = prompt
            if context:
                full_prompt = f"Context: {context}\n\n{prompt}"
            
            def _call():
                return self.gemini_client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=full_prompt
                )
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, _call)
            return response.text
            
        except Exception as e:
            logger.error(f"{self.name} response generation failed: {str(e)}")
            return "I apologize, but I'm having trouble generating a response right now."
    
    def get_session(self, session_id: str) -> Dict[str, Any]:
        """Get session data."""
        return self.sessions.get(session_id, {
            'messages': [],
            'context': {}
        })
    
    def update_session(self, session_id: str, user_message: str, 
                      agent_response: str, tools_used: List[str]):
        """Update session with new interaction."""
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                'messages': [],
                'context': {}
            }
        
        self.sessions[session_id]['messages'].extend([
            {'role': 'user', 'content': user_message},
            {'role': 'assistant', 'content': agent_response, 'tools_used': tools_used}
        ])
    
    def extract_urls_from_text(self, text: str) -> List[str]:
        """Extract URLs from text using regex, including cloud storage URLs."""
        import re
        
        # Enhanced URL patterns to include cloud storage
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
        
        urls = []
        for pattern in url_patterns:
            found_urls = re.findall(pattern, text, re.IGNORECASE)
            urls.extend(found_urls)
        
        # Remove duplicates while preserving order
        return list(dict.fromkeys(urls))
    
    def create_tool_calling_prompt(self, user_message: str, available_tools: List[Dict[str, Any]]) -> str:
        """Create a prompt for tool selection and parameter extraction."""
        tools_description = []
        for tool in available_tools:
            params = tool.get('parameters', {})
            param_desc = []
            for param_name, param_info in params.items():
                param_desc.append(f"  - {param_name}: {param_info.get('description', 'No description')}")
            
            tools_description.append(f"""
Tool: {tool['name']}
Description: {tool['description']}
Parameters:
{chr(10).join(param_desc) if param_desc else '  (no parameters)'}""")
        
        return f"""You are an AI agent that needs to decide which tools to call to help the user.

User request: {user_message}

Available tools:
{chr(10).join(tools_description)}

Analyze the user's request and respond with a JSON object containing:
1. "reasoning": Brief explanation of your analysis
2. "tools_to_call": Array of tools to call with their parameters
3. "response_strategy": How you plan to present the results

Format for tools_to_call:
[
  {{
    "tool_name": "exact_tool_name",
    "parameters": {{
      "param1": "value1",
      "param2": "value2"
    }},
    "reasoning": "why this tool is needed"
  }}
]

Return only the JSON object, no additional text."""

    @abstractmethod
    async def process_request(self, message: str, user_id: Optional[str] = None,
                            session_id: Optional[str] = None, 
                            context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process a user request. Must be implemented by subclasses."""
        pass 