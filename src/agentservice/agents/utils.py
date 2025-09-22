"""
Utility functions for agent operations.

Common utilities used across all agents including:
- JSON response cleaning and parsing
- Response validation
- Error handling helpers
"""

import json
import logging
import re
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

def clean_and_parse_json(response_text: str, fallback: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Clean and parse JSON response from Gemini.
    
    Handles common formatting issues like:
    - Markdown code blocks (```json)
    - Extra whitespace
    - Malformed JSON
    
    Args:
        response_text: Raw response text from Gemini
        fallback: Optional fallback dict if parsing fails
        
    Returns:
        Parsed JSON dict or fallback dict
    """
    try:
        # Clean the response text
        cleaned_text = clean_json_response(response_text)
        
        # Try to parse JSON
        parsed_data = json.loads(cleaned_text)
        
        logger.debug(f"Successfully parsed JSON response")
        return parsed_data
        
    except json.JSONDecodeError as e:
        logger.warning(f"JSON parsing failed: {str(e)}")
        logger.debug(f"Failed to parse: {cleaned_text[:200]}...")
        
        # Try to fix common JSON issues
        fixed_text = fix_common_json_issues(cleaned_text)
        try:
            parsed_data = json.loads(fixed_text)
            logger.info("Successfully parsed JSON after fixing common issues")
            return parsed_data
        except json.JSONDecodeError:
            logger.error("JSON parsing failed even after attempting fixes")
            
        # Return fallback if provided
        if fallback is not None:
            logger.info("Using fallback response due to JSON parsing failure")
            return fallback
            
        # Return minimal valid structure
        return {
            "reasoning": "JSON parsing failed",
            "tools_to_call": [],
            "response_strategy": "Provide general assistance"
        }
    
    except Exception as e:
        logger.error(f"Unexpected error during JSON parsing: {str(e)}")
        return fallback or {
            "reasoning": "Unexpected parsing error",
            "tools_to_call": [],
            "response_strategy": "Handle error gracefully"
        }

def clean_json_response(response_text: str) -> str:
    """
    Clean raw response text to prepare for JSON parsing.
    
    Args:
        response_text: Raw response from Gemini
        
    Returns:
        Cleaned text ready for JSON parsing
    """
    if not response_text:
        return "{}"
    
    # Strip whitespace
    cleaned = response_text.strip()
    
    # Remove markdown code blocks
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]  # Remove ```json
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]   # Remove ```
    
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]  # Remove closing ```
    
    # Strip again after removing markdown
    cleaned = cleaned.strip()
    
    # If empty after cleaning, return empty object
    if not cleaned:
        return "{}"
    
    return cleaned

def fix_common_json_issues(json_text: str) -> str:
    """
    Attempt to fix common JSON formatting issues.
    
    Args:
        json_text: JSON text that failed to parse
        
    Returns:
        Potentially fixed JSON text
    """
    fixed = json_text
    
    # Fix missing commas between object properties
    # Look for patterns like: "value"\n    "key"
    fixed = re.sub(r'"\s*\n\s*"', '",\n    "', fixed)
    
    # Fix missing commas in arrays
    # Look for patterns like: }\n    {
    fixed = re.sub(r'}\s*\n\s*{', '},\n    {', fixed)
    
    # Fix trailing commas (remove them)
    fixed = re.sub(r',\s*([}\]])', r'\1', fixed)
    
    # Fix single quotes to double quotes
    fixed = re.sub(r"'([^']*)':", r'"\1":', fixed)
    fixed = re.sub(r":\s*'([^']*)'", r': "\1"', fixed)
    
    # Fix unquoted keys (common mistake)
    fixed = re.sub(r'([{\s,])(\w+):', r'\1"\2":', fixed)
    
    return fixed

def validate_tool_plan(tool_plan: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and ensure tool plan has required structure.
    
    Args:
        tool_plan: Parsed tool plan from Gemini
        
    Returns:
        Validated tool plan with required fields
    """
    validated = {
        "reasoning": tool_plan.get("reasoning", "No reasoning provided"),
        "tools_to_call": [],
        "response_strategy": tool_plan.get("response_strategy", "Provide assistance")
    }
    
    # Validate tools_to_call
    tools = tool_plan.get("tools_to_call", [])
    if isinstance(tools, list):
        for tool in tools:
            if isinstance(tool, dict) and "tool_name" in tool:
                validated_tool = {
                    "tool_name": tool["tool_name"],
                    "parameters": tool.get("parameters", {}),
                    "reasoning": tool.get("reasoning", "No reasoning provided")
                }
                validated["tools_to_call"].append(validated_tool)
    
    return validated

def validate_analysis_response(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and ensure analysis response has required structure.
    
    Args:
        analysis: Parsed analysis from orchestrator
        
    Returns:
        Validated analysis with required fields
    """
    validated = {
        "intent": analysis.get("intent", "General assistance"),
        "complexity": analysis.get("complexity", "simple"),
        "domains_needed": analysis.get("domains_needed", ["product"]),
        "workflow_steps": [],
        "expected_outcome": analysis.get("expected_outcome", "Provide helpful assistance")
    }
    
    # Validate workflow steps
    steps = analysis.get("workflow_steps", [])
    if isinstance(steps, list):
        for i, step in enumerate(steps):
            if isinstance(step, dict):
                validated_step = {
                    "step": step.get("step", i + 1),
                    "domain": step.get("domain", "product"),
                    "action": step.get("action", "Handle request"),
                    "tools": step.get("tools", []),
                    "depends_on": step.get("depends_on", [])
                }
                validated["workflow_steps"].append(validated_step)
    
    # Ensure at least one step exists
    if not validated["workflow_steps"]:
        validated["workflow_steps"] = [{
            "step": 1,
            "domain": "product",
            "action": "Handle user request",
            "tools": ["list_all_products"],
            "depends_on": []
        }]
    
    return validated

def extract_parameters_safely(param_text: str, tool_schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Safely extract parameters from Gemini response.
    
    Args:
        param_text: Raw parameter text from Gemini
        tool_schema: Schema of the tool to validate against
        
    Returns:
        Extracted and validated parameters
    """
    try:
        # Clean and parse the parameters
        cleaned = clean_json_response(param_text)
        params = json.loads(cleaned)
        
        if not isinstance(params, dict):
            logger.warning("Parameters are not a dictionary, using empty dict")
            return {}
        
        # Validate against schema if available
        schema_params = tool_schema.get("parameters", {})
        validated_params = {}
        
        for key, value in params.items():
            if key in schema_params:
                validated_params[key] = value
            else:
                logger.debug(f"Ignoring unknown parameter: {key}")
        
        return validated_params
        
    except Exception as e:
        logger.error(f"Parameter extraction failed: {str(e)}")
        return {}

def log_agent_decision(agent_name: str, decision_type: str, details: Dict[str, Any]):
    """
    Log agent decisions for debugging and monitoring.
    
    Args:
        agent_name: Name of the agent making the decision
        decision_type: Type of decision (tool_planning, parameter_extraction, etc.)
        details: Decision details
    """
    logger.info(f"[{agent_name}] {decision_type}: {json.dumps(details, indent=2)}")

def create_error_response(agent_name: str, error_message: str, session_id: str) -> Dict[str, Any]:
    """
    Create standardized error response for agents.
    
    Args:
        agent_name: Name of the agent that encountered the error
        error_message: Error message to include
        session_id: Session ID for tracking
        
    Returns:
        Standardized error response
    """
    return {
        "response": f"I apologize, but I encountered an error: {error_message}",
        "agent_used": agent_name,
        "tools_called": [],
        "session_id": session_id,
        "error": True
    } 