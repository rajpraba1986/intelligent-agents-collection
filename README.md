# Agentic AI MCP - Intelligent Multi-Tool Chatbot

A sophisticated AI assistant with Model Context Protocol (MCP) support, featuring web search, YouTube search, weather information, and location services. Available in both command-line and web interfaces.

## 🚀 Features

- **Multi-Tool Integration**: Web search, YouTube, weather, and location services
- **Conversation Memory**: Persistent conversation history and context awareness
- **Dual Interface**: Command-line and modern web interface
- **Real-time Communication**: WebSocket-based chat with typing indicators
- **Tool Usage Transparency**: See which tools are used for each response
- **Formatted Responses**: Clean, structured output with proper formatting

## 📋 Prerequisites

- **Python 3.8+**
- **Anthropic API Key** (for Claude AI)
- **Internet Connection** (for tool functionality)

## 🛠️ Installation

### 1. Clone/Download the Project
```bash
# If using git
git clone <repository-url>
cd agentic-ai-mcp

# Or download and extract the ZIP file to:
# /Users/prabakaranrajendran/Downloads/Agentic AI MCP/agentic-ai-mcp
```

### 2. Create Virtual Environment (Recommended)
```bash
python -m venv agentic-ai-env
source agentic-ai-env/bin/activate  # On macOS/Linux
# agentic-ai-env\Scripts\activate     # On Windows
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Environment Setup
Create a `.env` file in the project root:
```bash
touch .env
```

Add your API keys to `.env`:
```env
# Required
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Optional (for enhanced functionality)
OPENWEATHER_API_KEY=your_weather_api_key_here
```

## 🚀 Running the Application

### Web Interface (Recommended)
```bash
python src/main.py --mode web
```

Then open your browser to: **http://localhost:8000**

### Command Line Interface
```bash
python src/main.py --mode cli
```

### Custom Host/Port
```bash
python src/main.py --mode web --host 0.0.0.0 --port 8080
```

## 🌐 Web Interface Testing Guide

### Accessing the Interface
1. **Start the server**:
   ```bash
   python src/main.py --mode web
   ```

2. **Open your browser** to `http://localhost:8000`

3. **Verify connection**: You should see "Connected" status in the bottom status bar

### Interface Components

#### Main Chat Area
- **Header**: Shows "🤖 Agentic AI Assistant"
- **Messages Area**: Displays conversation with user and bot messages
- **Input Field**: Type your messages here
- **Send Button**: Click or press Enter to send messages

#### Status Bar
- **Connection Status**: Green dot = Connected, Red dot = Disconnected
- **Memory Button**: View conversation history summary
- **Clear Button**: Clear conversation memory

#### Visual Indicators
- **Typing Indicator**: Shows "Assistant is typing..." when processing
- **Tool Usage**: Displays which tools were used (e.g., "🔧 Tools used: youtube_search")
- **Message Avatars**: 👤 for user, 🤖 for assistant

## 🔧 Web Server Architecture

### FastAPI Framework Integration

The web server is built on **FastAPI**, a modern, high-performance web framework that provides:

- **Asynchronous Support**: Non-blocking I/O for handling multiple concurrent connections
- **WebSocket Support**: Real-time bidirectional communication
- **Automatic API Documentation**: Built-in OpenAPI/Swagger documentation
- **Type Safety**: Full Python type hints support

### Server Components

#### 1. ChatbotWebServer Class
```python
# Located in: src/web_server.py
class ChatbotWebServer:
    def __init__(self):
        self.app = FastAPI(title="Agentic AI Chatbot", version="1.0.0")
        self.agent = AgentCore()  # Direct integration with AI agent
        self.active_connections = []  # WebSocket connection management
```

**Key Features:**
- **Single Agent Instance**: One `AgentCore` instance serves all connected clients
- **Connection Management**: Tracks active WebSocket connections
- **Route Setup**: Configures HTTP and WebSocket endpoints

#### 2. Agent Integration Layer

The web server seamlessly integrates with the AI agent through:

```python
# Agent initialization in web server
self.agent = AgentCore()

# Direct method calls for processing
result = await self.agent.process_message(user_message)
summary = self.agent.get_memory_summary()
self.agent.clear_memory()
```

**Integration Benefits:**
- **Shared Memory**: All users share the same conversation context
- **Tool Access**: Full access to all agent tools (search, weather, YouTube, location)
- **Consistent Responses**: Same AI behavior across CLI and web interfaces

### WebSocket Communication Protocol

#### Message Types

The web server uses a structured JSON protocol for client-server communication:

```javascript
// Client to Server Messages
{
    "type": "chat",           // Send user message
    "message": "Hello AI"
}

{
    "type": "memory",         // Request memory summary
}

{
    "type": "clear",          // Clear conversation history
}

{
    "type": "ping",           // Connection health check
}
```

```javascript
// Server to Client Responses
{
    "type": "response",       // AI response
    "data": {
        "status": "success",
        "response": "AI response text",
        "tool_calls": [...]
    }
}

{
    "type": "memory",         // Memory summary
    "data": {
        "total_conversations": 5,
        "recent_topics": ["weather", "videos"],
        "session_data_keys": ["user_preferences"]
    }
}

{
    "type": "connection",     // Connection status
    "data": {
        "status": "connected",
        "message": "WebSocket connected successfully"
    }
}
```

#### Connection Lifecycle

1. **Connection Establishment**
   ```python
   await websocket.accept()
   self.active_connections.append(websocket)
   
   # Send confirmation
   await websocket.send_text(json.dumps({
       "type": "connection",
       "data": {"status": "connected"}
   }))
   ```

2. **Message Processing Loop**
   ```python
   while True:
       data = await websocket.receive_text()
       message_data = json.loads(data)
       
       # Route to appropriate handler
       if message_data["type"] == "chat":
           result = await self.agent.process_message(message_data["message"])
           await websocket.send_text(json.dumps({
               "type": "response",
               "data": result
           }))
   ```

3. **Error Handling & Cleanup**
   ```python
   except WebSocketDisconnect:
       self.active_connections.remove(websocket)
       logger.info("Client disconnected")
   ```

### Client-Side Architecture

#### JavaScript Chatbot Client

The frontend uses a dedicated `ChatbotClient` class that manages:

```javascript
class ChatbotClient {
    constructor() {
        this.ws = null;                    // WebSocket connection
        this.reconnectAttempts = 0;        // Auto-reconnection logic
        this.maxReconnectAttempts = 5;     // Connection resilience
        
        // UI element references
        this.chatMessages = document.getElementById('chatMessages');
        this.chatInput = document.getElementById('chatInput');
        this.sendButton = document.getElementById('sendButton');
        this.typingIndicator = document.getElementById('typingIndicator');
    }
}
```

#### Real-Time Features

1. **Automatic Reconnection**
   ```javascript
   scheduleReconnect() {
       this.reconnectAttempts++;
       const delay = 1000 * Math.pow(2, this.reconnectAttempts - 1);
       
       setTimeout(() => {
           this.initWebSocket();
       }, delay);
   }
   ```

2. **Typing Indicators**
   ```javascript
   showTyping(show) {
       this.typingIndicator.style.display = show ? 'block' : 'none';
       if (show) {
           this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
       }
   }
   ```

3. **Response Formatting**
   ```javascript
   formatResponse(text) {
       // Convert markdown-style formatting to HTML
       formatted = formatted.replace(/🎯\s*\*\*(.*?)\*\*/g, '<h3>🎯 $1</h3>');
       formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<h4>$1</h4>');
       formatted = formatted.replace(/^-\s(.+)$/gm, '<li>$1</li>');
       // ... additional formatting rules
   }
   ```

### Seamless User Experience Design

#### 1. Visual Feedback System

- **Connection Status**: Real-time connection indicator with color coding
- **Typing Animation**: Shows when AI is processing requests
- **Tool Usage Display**: Transparent indication of which tools were used
- **Message Avatars**: Clear visual distinction between user and AI messages

#### 2. Error Handling & Recovery

```python
# Server-side error handling
try:
    result = await self.agent.process_message(message_data["message"])
    await websocket.send_text(json.dumps({
        "type": "response",
        "data": result
    }))
except Exception as e:
    logger.error(f"Error processing chat message: {e}")
    await websocket.send_text(json.dumps({
        "type": "response",
        "data": {
            "status": "error",
            "response": f"I apologize, but I encountered an error: {str(e)}",
            "tool_calls": []
        }
    }))
```

```javascript
// Client-side error recovery
this.ws.onerror = (error) => {
    console.error('WebSocket error:', error);
    this.updateStatus('Connection Error', false);
    this.scheduleReconnect();  // Automatic recovery
};
```

#### 3. Responsive Design Elements

- **Adaptive Layout**: Container adjusts to different screen sizes
- **Touch-Friendly**: Optimized for mobile interaction
- **Keyboard Shortcuts**: Enter key for message sending
- **Focus Management**: Automatic input field focus

### Performance Optimizations

#### 1. Asynchronous Processing

```python
# Non-blocking message processing
async def websocket_endpoint(websocket: WebSocket):
    # Multiple clients can be served simultaneously
    while True:
        data = await websocket.receive_text()
        # Each message processed asynchronously
        result = await self.agent.process_message(message)
```

#### 2. Connection Management

```python
# Efficient connection tracking
self.active_connections = []

# Clean up disconnected clients
except WebSocketDisconnect:
    if websocket in self.active_connections:
        self.active_connections.remove(websocket)
```

#### 3. Memory Efficiency

- **Shared Agent Instance**: Single `AgentCore` for all connections
- **Persistent Memory**: Conversation history maintained across sessions
- **Tool Reuse**: Cached tool instances for faster execution

### Integration with Agent Tools

#### Tool Execution Flow

1. **User Input Processing**
   ```python
   # Web server receives message
   message_data = json.loads(data)
   
   # Route to agent
   result = await self.agent.process_message(message_data["message"])
   ```

2. **Agent Tool Orchestration**
   ```python
   # Agent analyzes intent and selects tools
   if any(word in user_message.lower() for word in ['video', 'youtube']):
       youtube_result = await self.execute_tool("youtube_search", params)
   elif any(word in user_message.lower() for word in ['weather']):
       weather_result = await self.execute_tool("get_weather", params)
   ```

3. **Response Assembly**
   ```python
   # Agent formats comprehensive response
   return {
       "response": final_response,
       "tool_calls": tool_calls,
       "status": "success"
   }
   ```

4. **Client Display**
   ```javascript
   // Client receives and formats response
   handleChatResponse(result) {
       let content = this.formatResponse(result.response);
       
       if (result.tool_calls && result.tool_calls.length > 0) {
           const tools = result.tool_calls.map(call => call.tool).join(', ');
           content += '<div class="tool-info">🔧 Tools used: ' + tools + '</div>';
       }
       
       this.addMessage('bot', content);
   }
   ```

### Security & Reliability

#### 1. Input Validation

```python
# Server-side validation
try:
    message_data = json.loads(data)
    if message_data["type"] == "chat":
        # Process valid chat message
except json.JSONDecodeError as e:
    await websocket.send_text(json.dumps({
        "type": "error",
        "data": {"error": "Invalid message format"}
    }))
```

#### 2. Connection Security

- **Origin Validation**: WebSocket connections validated
- **Rate Limiting**: Built-in FastAPI rate limiting support
- **Error Isolation**: Individual connection errors don't affect others

#### 3. Data Persistence

```python
# Automatic memory persistence
self.memory_manager.add_conversation_turn(
    user_message=user_message,
    agent_response=final_response,
    tool_calls=tool_calls,
    metadata={"reasoning_approach": True}
)
```

### Development & Testing Benefits

#### 1. Live Development

```bash
# Hot reload during development
uvicorn src.web_server:app --reload --port 8000
```

#### 2. API Documentation

- **Automatic OpenAPI docs**: Available at `http://localhost:8000/docs`
- **WebSocket testing**: Built-in testing interface
- **Request/Response schemas**: Automatically generated

#### 3. Logging & Monitoring

```python
# Comprehensive logging
logger.info(f"Client connected. Total connections: {len(self.active_connections)}")
logger.info(f"Processing chat message: {message_data['message']}")
logger.info(f"Agent response: {result}")
```

This architecture ensures a seamless, responsive, and reliable chatbot experience while maintaining full integration with the sophisticated AI agent capabilities.

## 💬 CLI Interface Testing Guide

### Basic Commands
```bash
# Start CLI mode
python src/main.py --mode cli

# In the CLI:
You: hello                    # Basic conversation
You: memory                   # View memory summary
You: clear                    # Clear conversation history
You: quit                     # Exit application
```

### CLI-Specific Features
- **Rich Formatting**: Colored output and emoji indicators
- **Tool Usage Display**: Shows which tools were used
- **Interactive Commands**: Special commands for memory management

## 🔧 Available Tools

### 1. Web Search (DuckDuckGo)
- **Purpose**: Search the web for current information
- **Usage**: Ask questions requiring up-to-date information
- **Example**: "What's the latest news about AI?"

### 2. YouTube Search
- **Purpose**: Find relevant YouTube videos
- **Usage**: Request videos on any topic
- **Example**: "Find videos about cooking pasta"

### 3. Weather Information
- **Purpose**: Get current weather conditions
- **Usage**: Ask about weather in any location
- **Example**: "What's the weather in Tokyo?"

### 4. Location Services
- **Purpose**: Find location information and coordinates
- **Usage**: Ask about places, addresses, or landmarks
- **Example**: "Where is Central Park?"

### 5. Distance Calculator
- **Purpose**: Calculate distances between locations
- **Usage**: Ask for distances between two places
- **Example**: "Distance from New York to Los Angeles"

## 📊 Testing Checklist

### Functional Testing
- [ ] Server starts without errors
- [ ] Web interface loads correctly
- [ ] WebSocket connection establishes
- [ ] Send button responds to clicks
- [ ] Enter key sends messages
- [ ] All tools execute successfully
- [ ] Memory functions work
- [ ] Clear function works
- [ ] Typing indicators appear
- [ ] Tool usage is displayed

### Cross-Browser Testing
- [ ] Chrome/Edge compatibility
- [ ] Firefox compatibility
- [ ] Safari compatibility (macOS)
- [ ] Mobile browser compatibility

### Error Handling
- [ ] Network disconnection recovery
- [ ] Invalid API key handling
- [ ] Tool execution errors
- [ ] Malformed user input
- [ ] Server restart recovery

## 🔍 Advanced Testing

### Load Testing
```bash
# Test multiple concurrent connections
# Open multiple browser tabs to the same URL
```

### API Key Testing
```bash
# Test with invalid API key
echo "ANTHROPIC_API_KEY=invalid_key" > .env
python src/main.py --mode web
# Should show appropriate error messages
```

### Network Testing
```bash
# Test with no internet connection
# Disable WiFi and test tool functionality
# Should gracefully handle connection errors
```

## 📝 Example Test Conversations

### Comprehensive Test Flow
```
1. "Hello" → Welcome message
2. "Find videos about machine learning" → YouTube results
3. "What's the weather in London?" → Weather information
4. "Tell me about quantum computing" → Web search results
5. Click "Memory" → View conversation summary
6. Click "Clear" → Clear conversation
7. "Where is Big Ben?" → Location information
```

### Expected Response Format

#### Basic Query Example
```
User Message: "Find videos about Python"

Bot Response:
🎥 Here are some great Python programming videos I found:

**Recommended Videos:**
- Python for Beginners - Complete Course
- Advanced Python Programming Techniques
- Python Data Science Tutorial

🔧 Tools used: youtube_search
```

#### Realistic Complex Query Example
```
User Message: "I have 2 kids aged 2 and 8, suggest outdoor activities for weekend in Singapore based on weather"

Bot Response:
Based on the research and considering the ages of your children (2 and 8), here's a well-planned outdoor activity recommendation for your family weekend in Singapore:

🎯 **Recommended Activity: Jacob Ballas Children's Garden at Singapore Botanic Gardens**

Why this location is perfect for your family:
- Safe and controlled environment suitable for both age groups
- Mix of activities for different developmental stages
- Shaded areas to protect from Singapore's heat
- Educational and fun elements combined

⏰ **Suggested Timeline:**
- Best timing: Morning (8:30 AM - 11:30 AM) to avoid peak heat
- Recommended duration: 2-3 hours

🎨 **Activities by Age Group:**

For your 2-year-old:
- Sensory play area with water features
- Safe toddler playground
- Mini garden exhibits
- Sand play area

For your 8-year-old:
- Treehouse exploration
- Suspension bridge adventure
- Interactive educational stations
- Nature discovery trails

👶 **Safety & Comfort Tips:**
1. Bring:
   - Sunscreen and hats
   - Change of clothes (water play area)
   - Snacks and water
   - Mosquito repellent
2. Wear comfortable walking shoes
3. Pack wet wipes and hand sanitizer

💡 **Alternative Options:**
If weather doesn't cooperate:
1. West Coast Park (has covered playground areas)
2. Pasir Ris Park (multiple play zones under shade)

🎫 **Practical Information:**
- Admission: Free
- Opening hours: 8 AM to 7 PM (closed on Mondays)
- Address: 481 Bukit Timah Road

🚗 **Getting There:**
- By MRT: Botanic Gardens MRT (Circle Line/Downtown Line)
- By Bus: Several bus services available (SBS 48, 66, 67, 151, 153, 154, 156, 170)
- By Car: Parking available at Visitor Centre

Source: Information compiled from honeykidsasia.com and littledayout.com

❗ **Pro Tips:**
1. Visit early morning to avoid crowds and heat
2. Pack a light picnic to enjoy in designated areas
3. Check weather forecast day before
4. Plan rest breaks between activities

Would you like more specific details about any of these aspects or information about alternative locations? 🤔

🔧 Tools used: get_weather, duckduckgo_search, location_search
```

### Additional Test Examples

#### Weather Query
```
User: "What's the weather like in Tokyo today?"

Expected Response:
🌤️ **Current Weather in Tokyo:**
- Temperature: 22°C (72°F)
- Conditions: Partly cloudy
- Humidity: 65%
- Wind: 8 km/h from the east

Perfect weather for outdoor activities! Consider visiting parks or outdoor attractions.

🔧 Tools used: get_weather
```

#### Location Query
```
User: "Where is the Tokyo Tower?"

Expected Response:
📍 **Tokyo Tower Location:**
- Address: 4 Chome-2-8 Shibakoen, Minato City, Tokyo, Japan
- Coordinates: 35.6586° N, 139.7454° E
- Height: 333 meters (1,092 feet)
- Nearest Station: Kamiyacho Station (5-minute walk)

Built in 1958, Tokyo Tower serves as a communications tower and tourist attraction, offering panoramic views of the city.

🔧 Tools used: location_search
```

## 🐛 Common Issues and Solutions

### Installation Issues
```bash
# If pip install fails
pip install --upgrade pip
pip install -r requirements.txt

# If Python version issues
python --version  # Should be 3.8+
```

### Runtime Issues
```bash
# If ANTHROPIC_API_KEY not found
echo "ANTHROPIC_API_KEY=your_key_here" >> .env

# If port already in use
python src/main.py --mode web --port 8001
```

## 📈 Performance Monitoring

### Server Logs
- Monitor terminal output for errors
- Check tool execution times
- Verify WebSocket connections

### Browser Performance
- Check Network tab in developer tools
- Monitor WebSocket messages
- Verify JavaScript console for errors

## 🔒 Security Considerations

### API Keys
- Never commit `.env` file to version control
- Use environment variables in production
- Rotate API keys regularly

### Network Security
- Use HTTPS in production
- Implement rate limiting for production use
- Validate all user inputs

## 🆘 Support and Debugging

### Debug Mode
```bash
# Enable verbose logging
export LOG_LEVEL=DEBUG
python src/main.py --mode web
```

### Log Files
- Server logs: Terminal output
- Browser logs: Developer Console (F12)
- Memory data: `data/conversation_memory.json`

### Getting Help
1. Check the troubleshooting section
2. Review server logs for errors
3. Test with minimal example inputs
4. Verify all prerequisites are met

## 📄 License

This project is provided as-is for educational and development purposes.

---

**Happy Testing! 🚀**

For additional support or questions, refer to the troubleshooting section or check the server logs for detailed error information.