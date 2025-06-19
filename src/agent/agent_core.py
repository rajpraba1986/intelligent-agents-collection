import asyncio
from typing import List, Dict, Any, Optional
from langchain_anthropic import ChatAnthropic
from langchain.schema import SystemMessage, HumanMessage, AIMessage
from langchain.tools import BaseTool
import json
import re

from tools import DuckDuckGoTool, YouTubeTool, WeatherTool, LocationTool
from tools.location_tool import DistanceCalculatorTool
from .memory_manager import MemoryManager
from config.settings import settings
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
            model="claude-3-5-sonnet-20241022",
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
                DuckDuckGoTool(),
                YouTubeTool()
            ]
            
            self.formatted_tools = []
            for tool in self.tools:
                formatted_tool = {
                    "type": "custom",
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
        self.anthropic_tools = []
        for tool in self.tools:
            tool_def = {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.args_schema.model_json_schema() if hasattr(tool.args_schema, 'model_json_schema') else tool.args_schema.schema()
            }
            self.anthropic_tools.append(tool_def)

        self.agent_executor = self
        
    def _format_response(self, response: str) -> str:
        """Format response for better readability"""
        formatted = response
        formatted = re.sub(r'(🎯|⏰|🎨|👶|💡|🎫|🚗|❗)\s*\*\*(.*?)\*\*', r'\1 **\2**\n', formatted)
        formatted = re.sub(r'^(-\s)', r'\n\1', formatted, flags=re.MULTILINE)
        formatted = re.sub(r'(\n\n)([🎯⏰🎨👶💡🎫🚗❗])', r'\1\n\2', formatted)
        formatted = re.sub(r'\n{4,}', '\n\n\n', formatted)
        return formatted.strip()

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

    async def process_message(self, user_message: str) -> Dict[str, Any]:
        """Process user message with advanced reasoning approach"""
        try:
            logger.info(f"Processing message: {user_message}")
            
            relevant_context = self.memory_manager.search_history(user_message, max_results=3)
            
            context_parts = []
            if relevant_context:
                context_parts.append("Previous relevant conversations:")
                for i, turn in enumerate(relevant_context, 1):
                    context_parts.append(f"{i}. User: {turn.user_message}")
                    context_parts.append(f"   Assistant: {turn.agent_response[:200]}...")
                    if turn.tool_calls:
                        tools_used = [call.get('tool', 'unknown') for call in turn.tool_calls]
                        context_parts.append(f"   Tools used: {', '.join(tools_used)}")
                    context_parts.append("")
            
            recent_history = self.memory_manager.get_recent_history(5)
            if recent_history:
                context_parts.append("Recent conversation history:")
                for i, turn in enumerate(recent_history[-3:], 1):
                    context_parts.append(f"{i}. User: {turn.user_message}")
                    context_parts.append(f"   Assistant: {turn.agent_response[:150]}...")
                    context_parts.append("")
            
            is_referring_to_previous = any(phrase in user_message.lower() for phrase in [
                'previous', 'earlier', 'before', 'last time', 'you mentioned', 'you said', 
                'from our conversation', 'we talked about', 'you recommended', 'the recommendation',
                'that video', 'those videos', 'the links', 'what you found'
            ])
            
            # ENHANCED REASONING: Analyze user intent and determine required tools
            intent_analysis = self._analyze_user_intent(user_message)
            logger.info(f"🧠 Intent analysis: {intent_analysis}")
            
            tool_calls = []
            final_response = ""
            
            # Execute reasoning-based approach with proper tool calling
            if intent_analysis['requires_multiple_tools']:
                final_response = await self._handle_complex_query(user_message, intent_analysis, relevant_context, is_referring_to_previous, tool_calls)
            elif intent_analysis['primary_intent'] == 'video_search':
                final_response = await self._handle_video_request(user_message, relevant_context, is_referring_to_previous, tool_calls)
            elif intent_analysis['primary_intent'] == 'weather_only':
                final_response = await self._handle_weather_request(user_message, intent_analysis, tool_calls)
            elif intent_analysis['primary_intent'] == 'search':
                final_response = await self._handle_search_request(user_message, relevant_context, is_referring_to_previous, tool_calls)
            else:
                # Use LLM for general queries instead of fallback
                final_response = await self._handle_general_query(user_message, relevant_context, context_parts, tool_calls)

            final_response = str(final_response)
            
            logger.info(f"🔧 Tool calls made: {len(tool_calls)}")
            logger.info(f"🧠 Context used: {len(relevant_context)} relevant conversations found")
            
            self.memory_manager.add_conversation_turn(
                user_message=user_message,
                agent_response=final_response,
                tool_calls=tool_calls,
                metadata={"context_used": len(relevant_context) > 0, "intent": intent_analysis}
            )
            
            return {
                "response": final_response,
                "tool_calls": tool_calls,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            error_response = f"I apologize, but I encountered an error while processing your request: {str(e)}"
            
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

    def _analyze_user_intent(self, user_message: str) -> Dict[str, Any]:
        """Analyze user message to determine intent and required tools"""
        message_lower = user_message.lower()
        
        intent = {
            'primary_intent': 'general',
            'requires_multiple_tools': False,
            'tools_needed': [],
            'location': None,
            'is_travel_planning': False,
            'is_weather_dependent': False,
            'is_family_activity': False,
            'mentions_kids': False,
            'age_groups': []
        }
        
        # Detect location mentions
        singapore_patterns = [
            r'singapore', r'sg\b', r'in singapore', r'singapore weekend', r'singapore trip'
        ]
        for pattern in singapore_patterns:
            if re.search(pattern, message_lower):
                intent['location'] = 'Singapore'
                break
        
        # Detect travel planning
        travel_keywords = ['plan', 'trip', 'weekend', 'visit', 'itinerary', 'travel', 'vacation', 'holiday']
        if any(keyword in message_lower for keyword in travel_keywords):
            intent['is_travel_planning'] = True
        
        # Detect weather dependency
        weather_keywords = ['weather', 'forecast', 'based on weather', 'whether forecast', 'climate']
        if any(keyword in message_lower for keyword in weather_keywords):
            intent['is_weather_dependent'] = True
            intent['tools_needed'].append('weather')
        
        # Detect family/kids context
        family_keywords = ['kids', 'children', 'family', 'child', 'toddler', 'son', 'daughter']
        if any(keyword in message_lower for keyword in family_keywords):
            intent['is_family_activity'] = True
            intent['mentions_kids'] = True
        
        # Extract age groups
        age_patterns = [
            r'aged? (\d+)', r'(\d+) years? old', r'(\d+)-year-old', r'kids aged (\d+)', 
            r'children aged (\d+)', r'(\d+) & (\d+)', r'(\d+) and (\d+)'
        ]
        for pattern in age_patterns:
            matches = re.findall(pattern, message_lower)
            for match in matches:
                if isinstance(match, tuple):
                    intent['age_groups'].extend([int(age) for age in match if age.isdigit()])
                else:
                    intent['age_groups'].append(int(match))
        
        # Detect video requests
        video_keywords = ['video', 'youtube', 'show me video', 'find video', 'watch']
        if any(keyword in message_lower for keyword in video_keywords):
            intent['primary_intent'] = 'video_search'
            intent['tools_needed'].append('youtube')
        
        # Detect search requests
        search_keywords = ['search', 'find information', 'tell me about', 'what is', 'research']
        if any(keyword in message_lower for keyword in search_keywords):
            if intent['primary_intent'] == 'general':
                intent['primary_intent'] = 'search'
                intent['tools_needed'].append('search')
        
        # Determine if multiple tools are needed for complex travel planning
        if (intent['is_travel_planning'] and 
            intent['location'] and 
            intent['is_family_activity'] and 
            intent['is_weather_dependent']):
            
            intent['requires_multiple_tools'] = True
            intent['primary_intent'] = 'travel_planning_with_weather'
            
            # Add all needed tools
            if 'weather' not in intent['tools_needed']:
                intent['tools_needed'].append('weather')
            if 'search' not in intent['tools_needed']:
                intent['tools_needed'].append('search')
        
        # Check for weather-only requests
        elif (any(keyword in message_lower for keyword in weather_keywords) and 
              not intent['is_travel_planning']):
            intent['primary_intent'] = 'weather_only'
            if 'weather' not in intent['tools_needed']:
                intent['tools_needed'].append('weather')
        
        return intent

    async def _handle_weather_request(self, user_message: str, intent: Dict, tool_calls: List) -> str:
        """Handle weather-only requests"""
        try:
            # Extract location from intent or user message
            location = intent.get('location') or self._extract_location_from_message(user_message)
            
            if not location:
                return "I can help you with weather information! Please specify a location (e.g., 'weather in Singapore')."
            
            logger.info(f"🌤️ Getting weather for: {location}")
            
            # Execute the weather tool
            weather_result = await self.execute_tool("get_weather", {"location": location})
            
            tool_calls.append({
                "tool": "get_weather",
                "input": {"location": location},
                "result": str(weather_result)[:500] + "..." if len(str(weather_result)) > 500 else str(weather_result)
            })
            
            # Check if the weather tool returned a valid result
            if "Error" in weather_result or not weather_result.strip():
                logger.error(f"Weather tool failed or returned an empty response: {weather_result}")
                return f"I apologize, but I couldn't retrieve the weather information for {location}. Please try again later."
            
            return f"🌤️ **Weather Information for {location}:**\n\n{weather_result}"
            
        except Exception as e:
            logger.error(f"Error handling weather request: {e}")
            return f"I apologize, but I encountered an error while getting weather information: {str(e)}"

    def _extract_location_from_message(self, message: str) -> Optional[str]:
        """Extract location from user message"""
        # Simple location extraction - can be enhanced with NLP
        common_locations = ['singapore', 'new york', 'london', 'paris', 'tokyo', 'sydney']
        message_lower = message.lower()
        
        for location in common_locations:
            if location in message_lower:
                return location.title()
        
        # Look for patterns like "in [location]" or "weather in [location]"
        location_patterns = [
            r'in ([a-zA-Z\s]+?)(?:\s|$|,|\?|!)',
            r'weather (?:for|in) ([a-zA-Z\s]+?)(?:\s|$|,|\?|!)',
            r'forecast (?:for|in) ([a-zA-Z\s]+?)(?:\s|$|,|\?|!)'
        ]
        
        for pattern in location_patterns:
            match = re.search(pattern, message_lower)
            if match:
                return match.group(1).strip().title()
        
        return None

    async def _handle_search_request(self, user_message: str, relevant_context: List, is_referring_to_previous: bool, tool_calls: List) -> str:
        """Handle general search requests using DuckDuckGo"""
        try:
            logger.info("🔍 Handling search request")
            
            # Extract search terms from the user message
            search_query = self._extract_search_terms(user_message)
            
            if not search_query:
                return "I can help you search for information! Please provide more details about what you're looking for."
            
            # Execute the DuckDuckGo search tool
            search_result = await self.execute_tool("duckduckgo_search", {"query": search_query, "max_results": 5})
            
            tool_calls.append({
                "tool": "duckduckgo_search",
                "input": {"query": search_query, "max_results": 5},
                "result": str(search_result)[:500] + "..." if len(str(search_result)) > 500 else str(search_result)
            })
            
            return f"🔍 **Search Results for: {search_query}**\n\n{search_result}"
            
        except Exception as e:
            logger.error(f"Error handling search request: {e}")
            return f"I apologize, but I encountered an error while searching: {str(e)}"

    def _extract_search_terms(self, message: str) -> str:
        """Extract search terms from general search queries"""
        # Remove common search-related words
        search_words = ['search for', 'find information about', 'tell me about', 'what is', 'research']
        search_terms = message.lower()
        
        for phrase in search_words:
            search_terms = search_terms.replace(phrase, '')
        
        return search_terms.strip() or message

    async def _handle_general_query(self, user_message: str, relevant_context: List, context_parts: List[str], tool_calls: List) -> str:
        """Handle general queries using LLM with optional tool calling"""
        try:
            logger.info("🧠 Handling general query with LLM")
            
            # Create system message with context
            system_content = """You are a helpful AI assistant. You have access to several tools that you can use to provide better responses:

1. Weather Tool: Get current weather information for any location
2. Search Tool: Search the web for current information
3. YouTube Tool: Find relevant videos
4. Location Tool: Get location information and distances

When responding:
- Use tools when they would provide valuable, current information
- Provide detailed, helpful responses
- Format responses clearly with headings and bullet points when appropriate
- Be conversational and engaging

Available tools:
- get_weather: Get weather information for a location
- duckduckgo_search: Search the web for information
- youtube_search: Find YouTube videos
- get_location: Get location information

If the user's query would benefit from current information (weather, news, specific facts), consider using the appropriate tools."""

            if context_parts:
                system_content += f"\n\nContext from previous conversations:\n{chr(10).join(context_parts)}"

            # Prepare messages for Anthropic
            messages = [
                SystemMessage(content=system_content),
                HumanMessage(content=user_message)
            ]

            # First, get LLM response to determine if tools should be used
            response = await self.llm.ainvoke(messages)
            response_text = self.extract_content_from_response(response)

            # Check if the response suggests using tools or if the query clearly needs tools
            needs_tools = self._should_use_tools_for_query(user_message, response_text)
            
            if needs_tools:
                logger.info("🔧 Query would benefit from tool usage")
                return await self._enhance_response_with_tools(user_message, response_text, tool_calls)
            else:
                logger.info("✅ General response provided without tools")
                return response_text

        except Exception as e:
            logger.error(f"Error in general query handling: {e}")
            return await self._generate_intelligent_fallback_response(user_message, {})

    def _should_use_tools_for_query(self, user_message: str, llm_response: str) -> bool:
        """Determine if the query would benefit from tool usage"""
        message_lower = user_message.lower()
        
        # Check for explicit tool needs
        weather_indicators = ['weather', 'forecast', 'temperature', 'climate', 'rain', 'sunny']
        search_indicators = ['current', 'latest', 'recent', 'today', 'news', 'information about']
        video_indicators = ['video', 'youtube', 'watch', 'show me']
        
        if any(indicator in message_lower for indicator in weather_indicators):
            return True
        if any(indicator in message_lower for indicator in search_indicators):
            return True
        if any(indicator in message_lower for indicator in video_indicators):
            return True
            
        # Check if LLM response indicates uncertainty about current info
        uncertainty_phrases = [
            "i don't have current", "i don't have recent", "i cannot provide current",
            "i don't have access to", "i cannot access", "as of my last update"
        ]
        
        if any(phrase in llm_response.lower() for phrase in uncertainty_phrases):
            return True
            
        return False

    async def _enhance_response_with_tools(self, user_message: str, base_response: str, tool_calls: List) -> str:
        """Enhance LLM response with relevant tool information"""
        try:
            enhanced_parts = [base_response]
            
            # Determine which tools to use based on query
            if any(word in user_message.lower() for word in ['weather', 'forecast', 'temperature']):
                location = self._extract_location_from_message(user_message) or 'Singapore'
                try:
                    weather_result = await self.execute_tool("get_weather", {"location": location})
                    tool_calls.append({
                        "tool": "get_weather",
                        "input": {"location": location},
                        "result": str(weather_result)[:500] + "..." if len(str(weather_result)) > 500 else str(weather_result)
                    })
                    enhanced_parts.append(f"\n\n🌤️ **Current Weather for {location}:**\n{weather_result}")
                except Exception as e:
                    logger.error(f"Weather tool error: {e}")
            
            if any(word in user_message.lower() for word in ['search', 'find', 'information', 'current', 'latest']):
                search_query = self._extract_search_terms(user_message)
                if search_query and len(search_query) > 3:
                    try:
                        search_result = await self.execute_tool("duckduckgo_search", {"query": search_query, "max_results": 3})
                        tool_calls.append({
                            "tool": "duckduckgo_search",
                            "input": {"query": search_query, "max_results": 3},
                            "result": str(search_result)[:500] + "..." if len(str(search_result)) > 500 else str(search_result)
                        })
                        enhanced_parts.append(f"\n\n🔍 **Current Information:**\n{search_result}")
                    except Exception as e:
                        logger.error(f"Search tool error: {e}")
            
            if any(word in user_message.lower() for word in ['video', 'youtube', 'watch']):
                video_query = self._extract_video_search_terms(user_message)
                if video_query and len(video_query) > 3:
                    try:
                        video_result = await self.execute_tool("youtube_search", {"query": video_query, "max_results": 3})
                        tool_calls.append({
                            "tool": "youtube_search",
                            "input": {"query": video_query, "max_results": 3},
                            "result": str(video_result)[:500] + "..." if len(str(video_result)) > 500 else str(video_result)
                        })
                        enhanced_parts.append(f"\n\n🎬 **Related Videos:**\n{video_result}")
                    except Exception as e:
                        logger.error(f"Video tool error: {e}")
            
            return "\n\n".join(enhanced_parts)
            
        except Exception as e:
            logger.error(f"Error enhancing response with tools: {e}")
            return base_response

    async def _handle_complex_query(self, user_message: str, intent: Dict, relevant_context: List, is_referring_to_previous: bool, tool_calls: List) -> str:
        """Handle complex queries that require multiple tools and reasoning"""
        logger.info("🧠 Handling complex multi-tool query")
        
        location = intent.get('location', 'Singapore')
        age_groups = intent.get('age_groups', [])
        
        # Collect tool results
        tool_results = {}
        
        # Step 1: Get weather information for the location
        try:
            logger.info(f"Step 1: Getting weather for {location}")
            weather_result = await self.execute_tool("get_weather", {"location": location})
            
            tool_calls.append({
                "tool": "get_weather",
                "input": {"location": location},
                "result": str(weather_result)[:500] + "..." if len(str(weather_result)) > 500 else str(weather_result)
            })
            
            tool_results['weather'] = weather_result
            logger.info("✅ Weather information retrieved successfully")
            
        except Exception as e:
            logger.error(f"❌ Error getting weather: {e}")
            tool_results['weather'] = f"Weather information temporarily unavailable for {location}"
        
        # Step 2: Search for family activities
        try:
            age_range = f"{min(age_groups)}-{max(age_groups)}" if age_groups else "family"
            search_query = f"{location} family activities kids aged {age_range} weekend attractions playgrounds"
            
            logger.info(f"Step 2: Searching for activities with query: {search_query}")
            search_result = await self.execute_tool("duckduckgo_search", {"query": search_query, "max_results": 5})
            
            tool_calls.append({
                "tool": "duckduckgo_search",
                "input": {"query": search_query, "max_results": 5},
                "result": str(search_result)[:500] + "..." if len(str(search_result)) > 500 else str(search_result)
            })
            
            tool_results['activities'] = search_result
            logger.info("✅ Activity information retrieved successfully")
            
        except Exception as e:
            logger.error(f"❌ Error searching for activities: {e}")
            tool_results['activities'] = "Activity search temporarily unavailable"
        
        # Step 3: Use LLM to synthesize comprehensive response
        try:
            synthesis_prompt = f"""Based on the following information, create a comprehensive travel plan for {location} with children aged {age_groups if age_groups else 'various ages'}:

Weather Information:
{tool_results.get('weather', 'No weather data available')}

Activity Information:
{tool_results.get('activities', 'No activity data available')}

User Request: {user_message}

Please provide a detailed, well-structured response that includes:
1. Weather-based recommendations
2. Age-appropriate activities
3. Suggested schedule
4. Practical tips
5. Backup plans

Format the response with clear headings, bullet points, and emojis for better readability."""

            messages = [
                SystemMessage(content="You are a helpful travel planning assistant. Create detailed, practical travel plans based on the provided information."),
                HumanMessage(content=synthesis_prompt)
            ]
            
            response = await self.llm.ainvoke(messages)
            synthesized_response = self.extract_content_from_response(response)
            
            logger.info("✅ Travel plan synthesized successfully")
            return synthesized_response
            
        except Exception as e:
            logger.error(f"❌ Error synthesizing travel plan: {e}")
            return self._generate_fallback_travel_response(location, age_groups, tool_results.get('weather', ''), tool_results.get('activities', ''))