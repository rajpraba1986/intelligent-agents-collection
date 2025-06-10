import asyncio
from typing import List, Dict, Any, Optional
from langchain_anthropic import ChatAnthropic
from langchain.schema import SystemMessage, HumanMessage, AIMessage
from langchain.tools import BaseTool
import json

from ..tools import DuckDuckGoTool, YouTubeTool, WeatherTool, LocationTool
from ..tools.location_tool import DistanceCalculatorTool
from .memory_manager import MemoryManager
from ..config.settings import settings
import logging

logger = logging.getLogger(__name__)

class AgentCore:
    def __init__(self):
        self.memory_manager = MemoryManager()
        self.llm = None
        self.agent_executor = None
        self.tools = []
        self.setup_llm()
        self.setup_tools()
        self.setup_agent()
        
    def setup_llm(self):
        """Initialize Anthropic LLM"""
        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment variables")
            
        self.llm = ChatAnthropic(
            model="claude-3-5-sonnet-20241022",  # Updated to current model name
            api_key=settings.anthropic_api_key,
            temperature=0.7,
            max_tokens=4000
        )
        
    def setup_tools(self):
        """Setup available tools"""
        try:
            self.tools = [
                WeatherTool(),
                LocationTool(),
                DistanceCalculatorTool(),
                DuckDuckGoTool(),  # Add DuckDuckGo tool
                YouTubeTool()      # Add YouTube tool
            ]
            
            # Convert tools to the format expected by the API
            self.formatted_tools = []
            for tool in self.tools:
                formatted_tool = {
                    "type": "custom",  # Ensure this is 'custom' not 'function'
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.args_schema.model_json_schema() if hasattr(tool.args_schema, 'model_json_schema') else tool.args_schema.schema()
                }
                self.formatted_tools.append(formatted_tool)
                
            logger.info(f"Loaded {len(self.tools)} tools successfully")
            
        except Exception as e:
            logger.error(f"Error setting up tools: {str(e)}")
            self.tools = []
            self.formatted_tools = []

    def setup_agent(self):
        """Setup the agent with tools and memory"""
        system_prompt = """You are a helpful AI assistant with access to various tools for web search, YouTube, weather, and location services.

You have access to conversation history and can remember previous interactions. Use this context to provide more personalized and coherent responses.

Available tools:
- get_weather: Get weather information for locations
- location_search: Search for location information and coordinates
- calculate_distance: Calculate distance between two locations
- duckduckgo_search: Search the web for current information
- youtube_search: Find YouTube videos on any topic

Guidelines:
1. Always be helpful, accurate, and informative
2. Use tools when needed to provide current and accurate information
3. Reference previous conversation context when relevant
4. Be conversational and engaging
5. If you're unsure about something, use the search tools to find accurate information
6. When users ask for videos, use the youtube_search tool to find relevant content

Remember: You can access conversation history to maintain context across the session."""

        # Convert tools to Anthropic format
        self.anthropic_tools = []
        for tool in self.tools:
            tool_def = {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.args_schema.model_json_schema() if hasattr(tool.args_schema, 'model_json_schema') else tool.args_schema.schema()
            }
            self.anthropic_tools.append(tool_def)

        # Create a simple executor that handles Anthropic tool calls
        self.agent_executor = self
        
    async def execute_tool(self, tool_name: str, tool_input: dict) -> str:
        """Execute a specific tool by name"""
        for tool in self.tools:
            if tool.name == tool_name:
                try:
                    if hasattr(tool, '_arun'):
                        return await tool._arun(**tool_input)
                    else:
                        return tool._run(**tool_input)
                except Exception as e:
                    return f"Error executing {tool_name}: {str(e)}"
        return f"Tool {tool_name} not found"

    def extract_content_from_response(self, response) -> str:
        """Extract text content from Anthropic response"""
        if hasattr(response, 'content'):
            content = response.content
            if isinstance(content, str):
                return content
            elif isinstance(content, list):
                # Extract text from content blocks
                text_parts = []
                for item in content:
                    if isinstance(item, dict) and 'text' in item:
                        text_parts.append(item['text'])
                    elif hasattr(item, 'text'):
                        text_parts.append(item.text)
                    elif isinstance(item, str):
                        text_parts.append(item)
                return ''.join(text_parts)
            else:
                return str(content)
        return str(response)

    async def analyze_user_intent(self, user_message: str) -> Dict[str, Any]:
        """Analyze user intent and plan the approach"""
        analysis_prompt = f"""
Analyze this user request and determine the best approach:

User Message: "{user_message}"

Available tools:
- youtube_search: Find YouTube videos
- duckduckgo_search: Search web information
- get_weather: Get weather information
- location_search: Find location details
- calculate_distance: Calculate distances

Please analyze:
1. What is the user asking for?
2. What information do we need to gather?
3. Which tools should be used and in what order?
4. What additional context would be helpful?

Respond in JSON format:
{{
    "intent": "description of what user wants",
    "required_info": ["list", "of", "information", "needed"],
    "tool_plan": [
        {{"tool": "tool_name", "purpose": "why use this tool", "params": {{"key": "value"}}}}
    ],
    "reasoning": "step-by-step thinking process"
}}
"""

        try:
            analysis_response = await self.llm.ainvoke([
                {"role": "system", "content": "You are an expert at analyzing user requests and planning tool usage. Always respond with valid JSON."},
                {"role": "user", "content": analysis_prompt}
            ])
            
            analysis_text = self.extract_content_from_response(analysis_response)
            
            # Extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', analysis_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                # Fallback analysis
                return {
                    "intent": "General inquiry",
                    "required_info": ["basic information"],
                    "tool_plan": [],
                    "reasoning": "Could not parse detailed analysis"
                }
                
        except Exception as e:
            logger.error(f"Error in intent analysis: {e}")
            return {
                "intent": "General inquiry",
                "required_info": ["basic information"],
                "tool_plan": [],
                "reasoning": f"Analysis error: {str(e)}"
            }

    async def execute_reasoning_approach(self, user_message: str, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tools based on reasoning analysis"""
        tool_calls = []
        reasoning_steps = []
        
        reasoning_steps.append(f"🧠 **Analysis**: {analysis['intent']}")
        reasoning_steps.append(f"🎯 **Reasoning**: {analysis['reasoning']}")
        
        # Execute planned tools
        tool_results = {}
        for tool_plan in analysis.get('tool_plan', []):
            tool_name = tool_plan.get('tool')
            purpose = tool_plan.get('purpose', '')
            params = tool_plan.get('params', {})
            
            if tool_name:
                reasoning_steps.append(f"🔧 **Using {tool_name}**: {purpose}")
                
                try:
                    result = await self.execute_tool(tool_name, params)
                    tool_results[tool_name] = result
                    
                    tool_calls.append({
                        "tool": tool_name,
                        "input": params,
                        "purpose": purpose,
                        "result": result[:300] + "..." if len(str(result)) > 300 else str(result)
                    })
                    
                    reasoning_steps.append(f"✅ **{tool_name} completed**: Found relevant information")
                    
                except Exception as e:
                    reasoning_steps.append(f"❌ **{tool_name} failed**: {str(e)}")
        
        return {
            "tool_calls": tool_calls,
            "tool_results": tool_results,
            "reasoning_steps": reasoning_steps
        }

    async def synthesize_response(self, user_message: str, analysis: Dict[str, Any], execution_results: Dict[str, Any]) -> str:
        """Synthesize final response based on analysis and tool results"""
        
        synthesis_prompt = f"""
User asked: "{user_message}"

Analysis performed:
Intent: {analysis['intent']}
Reasoning: {analysis['reasoning']}

Information gathered:
{json.dumps(execution_results['tool_results'], indent=2)}

Reasoning steps taken:
{chr(10).join(execution_results['reasoning_steps'])}

Please provide a comprehensive, helpful response that:
1. Directly addresses the user's question
2. Incorporates all relevant information found
3. Shows your reasoning process
4. Provides actionable recommendations
5. Includes sources/links when available

Format your response in a clear, engaging way with appropriate emojis and formatting.
"""

        try:
            response = await self.llm.ainvoke([
                {"role": "system", "content": "You are a helpful assistant that provides comprehensive, well-reasoned responses based on gathered information."},
                {"role": "user", "content": synthesis_prompt}
            ])
            
            return self.extract_content_from_response(response)
            
        except Exception as e:
            logger.error(f"Error in response synthesis: {e}")
            return f"I gathered some information but had trouble synthesizing the response: {str(e)}"

    async def process_message(self, user_message: str) -> Dict[str, Any]:
        """Process user message with reasoning approach"""
        try:
            # Get conversation context
            chat_history = self.get_chat_history()
            
            # Search for relevant context if needed
            relevant_context = self.memory_manager.search_history(user_message, max_results=2)
            
            # Add relevant context to the message if found
            enhanced_message = user_message
            if relevant_context:
                context_summary = "\n".join([
                    f"Previous relevant context: {turn.user_message} -> {turn.agent_response[:100]}..."
                    for turn in relevant_context
                ])
                enhanced_message = f"{user_message}\n\nRelevant previous context:\n{context_summary}"
            
            # Step 1: Analyze user intent and plan approach
            logger.info("🧠 Analyzing user intent...")
            analysis = await self.analyze_user_intent(enhanced_message)
            
            # Step 2: Check for forced tool usage (for specific keywords)
            tool_calls = []
            final_response = ""
            
            # Force YouTube search for video-related queries
            if any(word in user_message.lower() for word in ['video', 'youtube', 'watch', 'show me video', 'find video']):
                logger.info("🎥 Detected video request, using reasoning approach for YouTube search")
                
                # Enhanced video search with reasoning
                search_query = user_message
                for phrase in ['can you', 'show me', 'find', 'search for', 'youtube', 'video']:
                    search_query = search_query.replace(phrase, '').strip()
                
                if not search_query:
                    search_query = "Singapore travel guide"
                
                reasoning_steps = [
                    f"🧠 **Detected**: Video content request",
                    f"🔍 **Search Strategy**: Looking for '{search_query}' on YouTube",
                    f"🎯 **Goal**: Find relevant video content for user's needs"
                ]
                
                youtube_result = await self.execute_tool("youtube_search", {"query": search_query, "max_results": 5})
                
                tool_calls.append({
                    "tool": "youtube_search",
                    "input": {"query": search_query, "max_results": 5},
                    "result": youtube_result[:500] + "..." if len(str(youtube_result)) > 500 else str(youtube_result)
                })
                
                reasoning_steps.append("✅ **Found**: YouTube videos matching your request")
                
                response_prompt = f"""
User asked: {user_message}

Reasoning process:
{chr(10).join(reasoning_steps)}

YouTube search results:
{youtube_result}

Please provide a helpful response that includes the video recommendations with explanations of why each video might be useful for the user's specific request.
"""
                
                response = await self.llm.ainvoke([
                    {"role": "system", "content": "You are a helpful assistant. Provide a natural, reasoned response that incorporates the search results and shows your thinking process."},
                    {"role": "user", "content": response_prompt}
                ])
                
                final_response = self.extract_content_from_response(response)
                
            # Enhanced weather-based location recommendations
            elif any(word in user_message.lower() for word in ['place', 'visit', 'weekend', 'outdoor', 'activity']) and any(word in user_message.lower() for word in ['weather', 'based on weather']):
                logger.info("🌤️ Detected weather-based activity request, using comprehensive reasoning")
                
                # Multi-step reasoning approach
                execution_results = await self.execute_reasoning_approach(user_message, {
                    "intent": "Find outdoor places to visit based on weather conditions",
                    "tool_plan": [
                        {"tool": "get_weather", "purpose": "Check current weather conditions", "params": {"location": "Singapore"}},
                        {"tool": "duckduckgo_search", "purpose": "Find weather-appropriate activities", "params": {"query": "Singapore outdoor activities weekend weather", "max_results": 5}},
                        {"tool": "location_search", "purpose": "Get details about recommended locations", "params": {"query": "Singapore outdoor attractions"}}
                    ],
                    "reasoning": "Need weather info first, then find activities suitable for those conditions, then get location details"
                })
                
                tool_calls = execution_results["tool_calls"]
                final_response = await self.synthesize_response(user_message, analysis, execution_results)
                
            else:
                # Step 3: Execute reasoning-based approach for other queries
                logger.info("🎯 Using comprehensive reasoning approach")
                
                execution_results = await self.execute_reasoning_approach(enhanced_message, analysis)
                tool_calls = execution_results["tool_calls"]
                
                # Step 4: Synthesize final response
                if tool_calls:
                    final_response = await self.synthesize_response(user_message, analysis, execution_results)
                else:
                    # Fallback to regular response if no tools were used
                    response = await self.llm.ainvoke([
                        {"role": "system", "content": "You are a helpful assistant. Provide a thoughtful, well-reasoned response."},
                        {"role": "user", "content": f"Please provide a helpful response to: {enhanced_message}"}
                    ])
                    final_response = self.extract_content_from_response(response)
            
            # Ensure final_response is a string
            if not isinstance(final_response, str):
                final_response = str(final_response)
            
            # Debug logging
            logger.info(f"🔧 Tool calls made: {len(tool_calls)}")
            for call in tool_calls:
                logger.info(f"Tool: {call['tool']}, Purpose: {call.get('purpose', 'N/A')}")
            
            # Save to memory with reasoning metadata
            self.memory_manager.add_conversation_turn(
                user_message=user_message,
                agent_response=final_response,
                tool_calls=tool_calls,
                metadata={"analysis": analysis, "reasoning_approach": True}
            )
            
            return {
                "response": final_response,
                "tool_calls": tool_calls,
                "analysis": analysis,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            error_response = f"I apologize, but I encountered an error while processing your request: {str(e)}"
            
            # Still save the interaction to memory
            self.memory_manager.add_conversation_turn(
                user_message=user_message,
                agent_response=error_response,
                metadata={"error": str(e)}
            )
            
            return {
                "response": error_response,
                "tool_calls": [],
                "status": "error",
                "error": str(e)
            }

    def get_chat_history(self, num_turns: int = 5) -> List:
        """Get formatted chat history for the agent"""
        recent_history = self.memory_manager.get_recent_history(num_turns)
        chat_history = []
        
        for turn in recent_history:
            chat_history.extend([
                HumanMessage(content=turn.user_message),
                AIMessage(content=turn.agent_response)
            ])
            
        return chat_history
        
    def get_memory_summary(self) -> Dict[str, Any]:
        """Get comprehensive memory summary including persistence info"""
        return self.memory_manager.get_memory_stats()
        
    def export_memory(self, export_path: str = None) -> str:
        """Export memory to a specific file"""
        if export_path:
            import shutil
            shutil.copy2(self.memory_manager.persistence_file, export_path)
            return f"Memory exported to {export_path}"
        else:
            return f"Memory is automatically saved to {self.memory_manager.persistence_file}"
    
    def import_memory(self, import_path: str) -> str:
        """Import memory from a file"""
        try:
            import shutil
            shutil.copy2(import_path, self.memory_manager.persistence_file)
            
            # Reload memory
            self.memory_manager.load_from_file()
            
            return f"Memory imported from {import_path}. Loaded {len(self.memory_manager.conversation_history)} conversations."
            
        except Exception as e:
            return f"Error importing memory: {str(e)}"
    
    def get_conversation_by_topic(self, topic: str, limit: int = 10) -> List[Dict]:
        """Search conversations by topic"""
        matching_conversations = []
        
        for turn in self.memory_manager.conversation_history:
            if topic.lower() in turn.user_message.lower() or topic.lower() in turn.agent_response.lower():
                matching_conversations.append({
                    "timestamp": turn.timestamp.isoformat(),
                    "user_message": turn.user_message,
                    "agent_response": turn.agent_response[:200] + "..." if len(turn.agent_response) > 200 else turn.agent_response,
                    "tool_calls": len(turn.tool_calls) if turn.tool_calls else 0
                })
                
                if len(matching_conversations) >= limit:
                    break
        
        return matching_conversations

    def clear_memory(self):
        """Clear conversation memory"""
        self.memory_manager.clear_history()
        
    def set_session_data(self, key: str, value: Any):
        """Store data in session memory"""
        self.memory_manager.set_session_data(key, value)
        
    def get_session_data(self, key: str, default: Any = None):
        """Get data from session memory"""
        return self.memory_manager.get_session_data(key, default)