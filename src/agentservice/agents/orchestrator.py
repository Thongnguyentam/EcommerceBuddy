"""
Orchestrator Agent

The main coordinator that:
1. Analyzes user requests to determine which domain agents to engage
2. Plans multi-step workflows across different domains
3. Coordinates tool execution across multiple agents
4. Synthesizes responses from multiple agents
"""

import json
import logging
import uuid
from typing import Dict, Any, List, Optional
from base_agent import BaseAgent
from utils import clean_and_parse_json, validate_analysis_response, extract_parameters_safely
logger = logging.getLogger(__name__)

class OrchestratorAgent(BaseAgent):
    """Orchestrator agent that coordinates domain agents and complex workflows."""
    
    @property
    def name(self) -> str:
        return "Orchestrator Agent"
    
    @property
    def description(self) -> str:
        return "Coordinates complex shopping workflows across multiple domain agents"
    
    @property
    def domain_tools(self) -> List[str]:
        # Orchestrator has access to all tools for planning purposes
        if not self.tools_schema or 'tools' not in self.tools_schema:
            return []
        return [tool['name'] for tool in self.tools_schema['tools']]
    
    async def process_request(self, message: str, user_id: Optional[str] = None,
                            session_id: Optional[str] = None, 
                            context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process a user request by analyzing intent and coordinating agents."""
        
        if not session_id:
            session_id = str(uuid.uuid4())
        
        try:
            # Step 1: Analyze the request and determine strategy
            analysis = await self._analyze_request(message, context)
            
            # Step 2: Execute the planned workflow
            result = await self._execute_workflow(analysis, message, user_id, session_id)
            
            # Step 3: Update session
            self.update_session(session_id, message, result['response'], result['tools_called'])
            
            return {
                "response": result['response'],
                "agent_used": "orchestrator",
                "tools_called": result['tools_called'],
                "session_id": session_id,
                "workflow_steps": result.get('workflow_steps', [])
            }
            
        except Exception as e:
            logger.error(f"Orchestrator request processing failed: {str(e)}")
            return {
                "response": f"I apologize, but I encountered an error processing your request: {str(e)}",
                "agent_used": "orchestrator",
                "tools_called": [],
                "session_id": session_id
            }
    
    async def _analyze_request(self, message: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Analyze user request to determine intent and required agents/tools."""
        
        
        available_tools = self.get_available_tools()
        tools_by_domain = self._categorize_tools_by_domain()
        
        analysis_prompt = f"""You are an AI shopping assistant orchestrator. Analyze this user request and create an execution plan.

User request: {message}
Context: {json.dumps(context) if context else "None"}

Available tool domains:
{json.dumps(tools_by_domain, indent=2)}

Analyze the request and respond in JSON format:
{{
    "intent": "What the user wants to accomplish",
    "complexity": "simple|moderate|complex",
    "domains_needed": ["list", "of", "domain", "agents", "needed"],
    "workflow_steps": [
        {{
            "step": 1,
            "domain": "domain_name",
            "action": "what to do",
            "agent_delegation": true,
            "depends_on": []
        }}
    ],
    "expected_outcome": "What the final response should contain"
}}

Domain agents available:
- product: Product search, recommendations, catalog browsing
- image: Image analysis, product visualization, room analysis  
- cart: Shopping cart management, add/remove items
- currency: Currency conversion, pricing, formatting
- sentiment: Review analysis, sentiment evaluation, product ratings"""

        try:
            response = await self.generate_response(analysis_prompt)
            analysis = clean_and_parse_json(response, fallback={
                "intent": "General shopping assistance",
                "complexity": "simple",
                "domains_needed": ["product"],
                "workflow_steps": [
                    {
                        "step": 1,
                        "domain": "product",
                        "action": "Handle user request",
                        "agent_delegation": True,
                        "depends_on": []
                    }
                ],
                "expected_outcome": "Provide helpful shopping assistance"
            })
            
            # Validate and clean the analysis
            analysis = validate_analysis_response(analysis)
            logger.info(f"Request analysis: {analysis['intent']} - Complexity: {analysis['complexity']}")
            return analysis
            
        except Exception as e:
            logger.error(f"Request analysis failed: {str(e)}")
            # Fallback to simple analysis
            return {
                "intent": "General shopping assistance",
                "complexity": "simple",
                "domains_needed": ["product"],
                "workflow_steps": [
                    {
                        "step": 1,
                        "domain": "product",
                        "action": "Handle user request",
                        "agent_delegation": True,
                        "depends_on": []
                    }
                ],
                "expected_outcome": "Provide helpful shopping assistance"
            }
    
    async def _execute_workflow(self, analysis: Dict[str, Any], original_message: str, 
                               user_id: Optional[str], session_id: str) -> Dict[str, Any]:
        """Execute the planned workflow by delegating to domain agents."""
        
        workflow_steps = analysis.get('workflow_steps', [])
        tools_called = []
        step_results = []
        
        # Execute steps sequentially, delegating to appropriate agents
        for step in workflow_steps:
            try:
                # Check if this step should be delegated to a domain agent
                if step.get('agent_delegation', False):
                    step_result = await self._delegate_to_domain_agent(step, original_message, user_id, session_id)
                else:
                    # Fallback to direct tool execution for backward compatibility
                    step_result = await self._execute_step(step, original_message, user_id, session_id)
                
                step_results.append(step_result)
                tools_called.extend(step_result.get('tools_used', []))
                
            except Exception as e:
                logger.error(f"Workflow step {step['step']} failed: {str(e)}")
                step_results.append({
                    "step": step['step'],
                    "status": "failed",
                    "error": str(e)
                })
        
        # Synthesize final response
        final_response = await self._synthesize_response(analysis, step_results, original_message)
        
        return {
            "response": final_response,
            "tools_called": tools_called,
            "workflow_steps": step_results
        }
    
    async def _delegate_to_domain_agent(self, step: Dict[str, Any], original_message: str, 
                                      user_id: Optional[str], session_id: str) -> Dict[str, Any]:
        """Delegate a workflow step to the appropriate domain agent."""
        
        domain = step.get('domain', 'product')
        action = step.get('action', '')
        
        # Import domain agents dynamically to avoid circular imports
        domain_agents = self._get_domain_agents()
        
        if domain not in domain_agents:
            logger.warning(f"Domain agent '{domain}' not available, falling back to direct execution")
            return await self._execute_step(step, original_message, user_id, session_id)
        
        try:
            # Get the domain agent
            agent = domain_agents[domain]
            
            logger.info(f"Delegating to {domain} agent: {action}")
            
            # Delegate the request to the domain agent
            agent_result = await agent.process_request(
                message=original_message,
                user_id=user_id,
                session_id=session_id,
                context={"orchestrator_action": action, "step": step}
            )
            
            # Convert agent result to step result format
            step_result = {
                "step": step['step'],
                "domain": domain,
                "action": action,
                "agent_used": agent_result.get('agent_used', domain),
                "tools_used": agent_result.get('tools_called', []),
                "results": [{"agent_response": agent_result.get('response', '')}],
                "status": "completed" if not agent_result.get('error') else "failed"
            }
            
            return step_result
            
        except Exception as e:
            logger.error(f"Domain agent delegation failed for {domain}: {str(e)}")
            return {
                "step": step['step'],
                "domain": domain,
                "action": action,
                "status": "failed",
                "error": f"Agent delegation failed: {str(e)}"
            }
    
    def _get_domain_agents(self) -> Dict[str, Any]:
        """Get available domain agents. This will be set by the main application."""
        # This will be populated by the main application
        # For now, return empty dict to avoid errors
        return getattr(self, '_domain_agents', {})
    
    async def _execute_step(self, step: Dict[str, Any], original_message: str, 
                           user_id: Optional[str], session_id: str) -> Dict[str, Any]:
        """Execute a single workflow step."""
        
        domain = step.get('domain')
        tools = step.get('tools', [])
        action = step.get('action', '')
        
        step_result = {
            "step": step['step'],
            "domain": domain,
            "action": action,
            "tools_used": [],
            "results": [],
            "status": "completed"
        }
        
        # For MVP, execute tools directly rather than delegating to domain agents
        for tool_name in tools:
            try:
                # Determine parameters based on the tool and user message
                parameters = await self._determine_tool_parameters(tool_name, original_message, user_id)
                
                # Call the tool
                tool_result = await self.call_tool(tool_name, parameters)
                
                step_result["tools_used"].append(tool_name)
                step_result["results"].append(tool_result)
                
            except Exception as e:
                logger.error(f"Tool execution failed: {tool_name} - {str(e)}")
                step_result["status"] = "partial"
                step_result["results"].append({"error": str(e)})
        
        return step_result
    
    async def _determine_tool_parameters(self, tool_name: str, message: str, user_id: Optional[str]) -> Dict[str, Any]:
        """Determine parameters for a tool call based on the user message."""
        
        # Find tool schema
        tool_schema = None
        for tool in self.get_available_tools():
            if tool['name'] == tool_name:
                tool_schema = tool
                break
        
        if not tool_schema:
            return {}
        
        # Use Gemini to extract parameters
        param_prompt = f"""Extract parameters for the tool '{tool_name}' from this user message.

User message: {message}
User ID: {user_id or "unknown"}

Tool schema:
{json.dumps(tool_schema, indent=2)}

Respond with only a JSON object containing the parameters:"""

        try:
            response = await self.generate_response(param_prompt)
            parameters = extract_parameters_safely(response, tool_schema)
            
            # Add user_id if required by tool
            if 'user_id' in tool_schema.get('parameters', {}) and user_id:
                parameters['user_id'] = user_id
                
            return parameters
            
        except Exception as e:
            logger.error(f"Parameter extraction failed for {tool_name}: {str(e)}")
            
            # Fallback parameter generation
            fallback_params = {}
            if user_id and 'user_id' in tool_schema.get('parameters', {}):
                fallback_params['user_id'] = user_id
            if 'query' in tool_schema.get('parameters', {}):
                fallback_params['query'] = message
                
            return fallback_params
    
    async def _synthesize_response(self, analysis: Dict[str, Any], step_results: List[Dict[str, Any]], 
                                  original_message: str) -> str:
        """Synthesize final response from workflow results."""
        
        synthesis_prompt = f"""Synthesize a helpful response for the user based on the workflow execution results.

Original user request: {original_message}
Intent: {analysis.get('intent', 'Unknown')}
Expected outcome: {analysis.get('expected_outcome', 'Provide assistance')}

Workflow results:
{json.dumps(step_results, indent=2)}

Create a natural, helpful response that:
1. Directly addresses the user's request
2. Uses the data from the tool results
3. Is conversational and friendly
4. Provides actionable information when possible

Response:"""

        try:
            response = await self.generate_response(synthesis_prompt)
            return response.strip()
            
        except Exception as e:
            logger.error(f"Response synthesis failed: {str(e)}")
            return "I've processed your request, but encountered an issue generating the response. Please try again."
    
    def _categorize_tools_by_domain(self) -> Dict[str, List[str]]:
        """Categorize tools by domain for analysis."""
        domains = {
            "product": ["list_all_products", "get_product_by_id", "search_products", 
                       "get_products_by_category", "semantic_search_products"],
            "cart": ["add_to_cart", "get_cart_contents", "clear_cart"],
            "currency": ["get_supported_currencies", "convert_currency", "get_exchange_rates", "format_money"],
            "reviews": ["create_review", "get_product_reviews", "get_user_reviews", 
                       "update_review", "delete_review", "get_product_review_summary"],
            # "shopping_assistant": ["get_ai_recommendations", "get_style_based_recommendations", 
            #                       "get_room_specific_recommendations", "analyze_room_image", 
            #                       "get_complementary_products"],
            "image": ["analyze_image", "visualize_product"]
        }
        
        return domains 