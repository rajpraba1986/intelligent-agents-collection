# 📚 API Reference - Conversational AI with Tools

## Agent Core API

### `AgentCore`

The main conversational AI agent class that orchestrates all operations and manages tool interactions.

#### Methods

##### `async process_message(user_message: str) -> Dict[str, Any]`
Process a user message and return a response with metadata.

**Parameters:**
- `user_message` (str): The user's input message

**Returns:**
```python
{
    "response": str,           # Agent's response
    "tool_calls": List[Dict],  # Tools used
    "analysis": Dict,          # Intent analysis
    "status": str             # "success" or "error"
}
```

##### `get_memory_summary() -> Dict[str, Any]`
Get comprehensive memory statistics.

**Returns:**
```python
{
    "total_conversations": int,
    "memory_file_exists": bool,
    "file_size_kb": float,
    "oldest_conversation": str,
    "newest_conversation": str,
    "recent_topics": List[str]
}
```

##### `export_memory(export_path: str = None) -> str`
Export conversation memory to a file.

##### `import_memory(import_path: str) -> str`
Import conversation memory from a file.

## Tool APIs

### `WeatherTool`

#### Input Schema
```python
class WeatherInput(BaseModel):
    location: str = Field(description="City name or location")
    units: str = Field(default="metric", description="Temperature units")
```

#### Example Usage
```python
weather_tool = WeatherTool()
result = weather_tool._run(location="Singapore", units="metric")
```

### `YouTubeTool`

#### Input Schema
```python
class YouTubeSearchInput(BaseModel):
    query: str = Field(description="Search query for YouTube videos")
    max_results: int = Field(default=5, description="Maximum results")
```

### `LocationTool`

#### Input Schema
```python
class LocationInput(BaseModel):
    query: str = Field(description="Location query to search for")
```

### `DuckDuckGoTool`

#### Input Schema
```python
class DuckDuckGoSearchInput(BaseModel):
    query: str = Field(description="Search query")
    max_results: int = Field(default=5, description="Maximum results")
```

## Memory Manager API

### `MemoryManager`

#### Methods

##### `add_conversation_turn(...)`
Add a new conversation to memory.

**Parameters:**
- `user_message` (str): User's message
- `agent_response` (str): Agent's response
- `tool_calls` (List[Dict], optional): Tools used
- `metadata` (Dict, optional): Additional metadata

##### `get_recent_history(num_turns: int = 5) -> List[ConversationTurn]`
Get recent conversation history.

##### `search_history(query: str, max_results: int = 3) -> List[ConversationTurn]`
Search conversation history for relevant context.

##### `clear_history()`
Clear all conversation history.

## Error Handling

### Exception Types

#### `ValueError`
Raised when API keys are missing or invalid.

#### `ConnectionError`
Raised when external API calls fail.

#### `ToolExecutionError`
Custom exception for tool-specific errors.

### Error Response Format
```python
{
    "response": str,      # Error message
    "tool_calls": [],     # Empty for errors
    "status": "error",    # Always "error"
    "error": str         # Detailed error information
}
```

## Configuration API

### `Settings`

Configuration class using Pydantic.

```python
class Settings(BaseSettings):
    anthropic_api_key: str
    openweather_api_key: Optional[str] = None
    
    class Config:
        env_file = ".env"
```

## Usage Examples

### Basic Conversational AI Usage
```python
from src.agent.agent_core import AgentCore

# Initialize the conversational AI agent
agent = AgentCore()
response = await agent.process_message("What's the weather in Tokyo?")
print(response["response"])

# Expected response structure:
{
    "response": "**Weather for Tokyo, JP**\n\n🌡️ **Temperature:** 15°C (feels like 12°C)\n🌤️ **Condition:** Clear - clear sky\n💧 **Humidity:** 45%\n🌬️ **Wind:** 2.1 m/s\n🔽 **Pressure:** 1023 hPa\n👁️ **Visibility:** 10000 meters",
    "tool_calls": [
        {
            "tool": "get_weather",
            "input": {"location": "Tokyo", "units": "metric"},
            "result": "Weather data retrieved successfully"
        }
    ],
    "analysis": {
        "intent": "Get weather information for Tokyo",
        "reasoning": "User wants current weather conditions",
        "tool_plan": [...]
    },
    "status": "success"
}
```

### Advanced Conversation Management
```python
# Check conversation memory stats
stats = agent.get_memory_summary()
print(f"Total conversations: {stats['total_conversations']}")

# Example output:
{
    "total_conversations": 25,
    "memory_file_exists": True,
    "file_size_kb": 45.2,
    "oldest_conversation": "2024-01-10T09:15:30",
    "newest_conversation": "2024-01-10T15:42:18",
    "recent_topics": [
        "What's the weather in Tokyo?",
        "Show me videos about Singapore attractions",
        "Find information about Sentosa Island",
        "Suggest outdoor places to visit this weekend...",
        "What's the distance between Marina Bay Sands..."
    ]
}

# Export conversation history
export_result = agent.export_memory("conversation_backup.json")
print(export_result)
# Output: "Memory exported to conversation_backup.json"

# Search past conversations
results = agent.get_conversation_by_topic("weather", limit=5)
for result in results:
    print(f"User: {result['user_message']}")
    print(f"AI: {result['agent_response'][:100]}...")
    print(f"Tools used: {result['tool_calls']}")
    print("---")

# Example search results:
[
    {
        "timestamp": "2024-01-10T14:30:15",
        "user_message": "What's the weather like in Singapore?", 
        "agent_response": "**Weather for Singapore, SG**\n\n🌡️ **Temperature:** 28°C...",
        "tool_calls": 1
    },
    {
        "timestamp": "2024-01-10T15:20:42",
        "user_message": "How's the weather there right now?",
        "agent_response": "Based on our previous conversation about Singapore attractions...",
        "tool_calls": 1  
    }
]
```

### Direct Tool Usage in Conversations
```python
from src.tools.weather_tool import WeatherTool

weather_tool = WeatherTool()
result = await weather_tool._arun(location="Singapore")
print(result)
```

### Multi-turn Conversations
```python
# Example of multi-turn conversation handling
conversation_turns = [
    "What's the weather in Singapore?",
    "How about tomorrow?",  # Context maintained
    "Show me videos about Singapore weather"  # Tool switching
]

responses = []
for turn in conversation_turns:
    response = await agent.process_message(turn)
    responses.append(response)
    print(f"User: {turn}")
    print(f"AI: {response['response']}")
    print(f"Tools used: {[call['tool'] for call in response['tool_calls']]}")
    print("---")

# Expected output:
# User: What's the weather in Singapore?
# AI: **Weather for Singapore, SG**... [weather information]
# Tools used: ['get_weather']
# ---
# User: How about tomorrow?
# AI: I currently only have access to current weather data for Singapore...
# Tools used: ['get_weather'] 
# ---
# User: Show me videos about Singapore weather
# AI: Here are some YouTube videos about Singapore weather...
# Tools used: ['youtube_search']
```

### Tool Response Examples

#### Weather Tool Response
```python
weather_tool = WeatherTool()
result = await weather_tool._arun(location="Singapore", units="metric")

# Expected result:
"""
**Weather for Singapore, SG**

🌡️ **Temperature:** 28°C (feels like 32°C)
🌤️ **Condition:** Partly Cloudy - scattered clouds
💧 **Humidity:** 78%
🌬️ **Wind:** 3.2 m/s
🔽 **Pressure:** 1012 hPa
👁️ **Visibility:** 10000 meters
"""
```

#### YouTube Tool Response
```python
youtube_tool = YouTubeTool()
result = await youtube_tool._arun(query="Singapore travel guide", max_results=3)

# Expected result:
"""
1. **Singapore Travel Guide - Top 10 Must-Visit Places**
   Channel: Travel with Sam
   Duration: 12:45
   Views: 2.3M views
   URL: https://youtube.com/watch?v=abc123
   Description: Complete guide covering Marina Bay Sands, Gardens by the Bay, and more

2. **Singapore Food Tour - Best Local Dishes**
   Channel: Food Adventure
   Duration: 15:20
   Views: 1.1M views
   URL: https://youtube.com/watch?v=def456
   Description: Explore Singapore's incredible food scene from hawker centers to fine dining

3. **Singapore in 4K - Amazing Drone Footage**
   Channel: 4K World
   Duration: 8:32
   Views: 856K views
   URL: https://youtube.com/watch?v=ghi789
   Description: Stunning aerial views of Singapore's modern skyline and attractions
"""
```

#### Location Tool Response
```python
location_tool = LocationTool()
result = await location_tool._arun(query="Marina Bay Sands Singapore")

# Expected result:
"""
**1. Marina Bay Sands, 10 Bayfront Avenue, Singapore 018956**
📍 **Coordinates:** 1.283921, 103.860707
🏢 **Type:** Hotel
🌍 **Country:** Singapore
🏙️ **City:** Singapore
📮 **Postal Code:** 018956
"""
```

#### DuckDuckGo Search Response
```python
search_tool = DuckDuckGoTool()
result = await search_tool._arun(query="Singapore smart city initiatives 2024", max_results=3)

# Expected result:
"""
1. **Singapore Launches Smart Nation 2.0 Initiative**
   URL: https://example.com/smart-nation-2024
   Summary: Singapore unveils next phase of smart city development focusing on AI, IoT, and sustainable urban planning.

2. **Digital Government Services Expansion in Singapore**
   URL: https://example.com/digital-services-2024  
   Summary: New digital platforms and services launched to enhance citizen experience and government efficiency.

3. **Singapore's AI Ethics Framework Gains Global Recognition**
   URL: https://example.com/ai-ethics-framework
   Summary: Singapore's approach to responsible AI development becomes model for other smart cities worldwide.
"""
```

### Error Handling Examples

#### API Key Missing
```python
# When ANTHROPIC_API_KEY is not set
try:
    agent = AgentCore()
except ValueError as e:
    print(f"Configuration Error: {e}")
    # Output: "Configuration Error: ANTHROPIC_API_KEY is required. Please set it in your .env file."
```

#### Tool Execution Error
```python
response = await agent.process_message("What's the weather in InvalidCity123?")

# Response with error handling:
{
    "response": "I tried to get weather information for InvalidCity123, but the location was not found. Please check the city name and try again with a valid location.",
    "tool_calls": [
        {
            "tool": "get_weather",
            "input": {"location": "InvalidCity123", "units": "metric"},
            "result": "Location 'InvalidCity123' not found."
        }
    ],
    "status": "success"  # Still success as the agent handled the error gracefully
}
```

#### Network Connection Error
```python
# When internet connection is unavailable
response = await agent.process_message("Search for latest news")

# Response structure:
{
    "response": "I encountered a connection error while trying to search for information. Please check your internet connection and try again.",
    "tool_calls": [
        {
            "tool": "duckduckgo_search", 
            "input": {"query": "latest news", "max_results": 5},
            "result": "Error performing search: Connection timeout"
        }
    ],
    "status": "success"  # Graceful error handling
}
```
