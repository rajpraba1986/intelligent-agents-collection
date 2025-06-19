from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import json
import asyncio
import logging
from pathlib import Path
from agent.agent_core import AgentCore

logger = logging.getLogger(__name__)

class ChatbotWebServer:
    def __init__(self):
        self.app = FastAPI(title="Agentic AI Chatbot", version="1.0.0")
        self.agent = AgentCore()
        self.active_connections = []
        self.setup_routes()
        
    def setup_routes(self):
        """Setup FastAPI routes"""
        
        # Serve static files
        static_path = Path(__file__).parent / "static"
        static_path.mkdir(exist_ok=True)
        self.app.mount("/static", StaticFiles(directory=str(static_path)), name="static")
        
        @self.app.get("/", response_class=HTMLResponse)
        async def get_chat_interface():
            """Serve the main chat interface"""
            return self.get_chat_html()
            
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket endpoint for real-time chat"""
            try:
                await websocket.accept()
                self.active_connections.append(websocket)
                logger.info(f"Client connected. Total connections: {len(self.active_connections)}")
                
                # Send initial connection confirmation
                await websocket.send_text(json.dumps({
                    "type": "connection",
                    "data": {"status": "connected", "message": "WebSocket connected successfully"}
                }))
                
                while True:
                    try:
                        # Receive message from client
                        data = await websocket.receive_text()
                        logger.info(f"Received message: {data}")
                        message_data = json.loads(data)
                        
                        if message_data["type"] == "chat":
                            # Process chat message
                            logger.info(f"Processing chat message: {message_data['message']}")
                            try:
                                result = await self.agent.process_message(message_data["message"])
                                logger.info(f"Agent response: {result}")
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
                            
                        elif message_data["type"] == "memory":
                            # Get memory summary
                            try:
                                summary = self.agent.get_memory_summary()
                                await websocket.send_text(json.dumps({
                                    "type": "memory",
                                    "data": summary
                                }))
                            except Exception as e:
                                logger.error(f"Error getting memory: {e}")
                                await websocket.send_text(json.dumps({
                                    "type": "error",
                                    "data": {"error": f"Memory error: {str(e)}"}
                                }))
                            
                        elif message_data["type"] == "clear":
                            # Clear memory
                            try:
                                self.agent.clear_memory()
                                await websocket.send_text(json.dumps({
                                    "type": "clear",
                                    "data": {"status": "Memory cleared successfully"}
                                }))
                            except Exception as e:
                                logger.error(f"Error clearing memory: {e}")
                                await websocket.send_text(json.dumps({
                                    "type": "error",
                                    "data": {"error": f"Clear error: {str(e)}"}
                                }))
                            
                        elif message_data["type"] == "ping":
                            # Handle ping for connection testing
                            await websocket.send_text(json.dumps({
                                "type": "pong",
                                "data": {"status": "alive"}
                            }))
                            
                    except json.JSONDecodeError as e:
                        logger.error(f"JSON decode error: {e}")
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "data": {"error": "Invalid message format"}
                        }))
                    except Exception as e:
                        logger.error(f"Error processing message: {e}")
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "data": {"error": str(e)}
                        }))
                        
            except WebSocketDisconnect:
                if websocket in self.active_connections:
                    self.active_connections.remove(websocket)
                logger.info(f"Client disconnected. Remaining connections: {len(self.active_connections)}")
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                if websocket in self.active_connections:
                    self.active_connections.remove(websocket)

    def get_chat_html(self) -> str:
        """Generate the chat interface HTML"""
        html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Agentic AI Chatbot</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        
        .chat-container {
            width: 900px;
            height: 600px;
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        
        .chat-header {
            background: #4a5568;
            color: white;
            padding: 20px;
            text-align: center;
            font-size: 18px;
            font-weight: 600;
        }
        
        .chat-messages {
            flex: 1;
            padding: 20px;
            overflow-y: auto;
            background: #f7fafc;
        }
        
        .message {
            margin-bottom: 15px;
            display: flex;
            align-items: flex-start;
        }
        
        .message.user {
            justify-content: flex-end;
        }
        
        .message-content {
            max-width: 70%;
            padding: 12px 16px;
            border-radius: 18px;
            font-size: 14px;
            line-height: 1.6;
            white-space: pre-wrap;
            word-wrap: break-word;
        }
        
        .message.user .message-content {
            background: #667eea;
            color: white;
            border-bottom-right-radius: 4px;
        }
        
        .message.bot .message-content {
            background: white;
            color: #2d3748;
            border: 1px solid #e2e8f0;
            border-bottom-left-radius: 4px;
        }

        .message-avatar {
            width: 32px;
            height: 32px;
            border-radius: 50%;
            margin: 0 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 16px;
            flex-shrink: 0;
        }
        
        .message.user .message-avatar {
            background: #667eea;
            color: white;
        }
        
        .message.bot .message-avatar {
            background: #48bb78;
            color: white;
        }
        
        .message.bot .message-content h3 {
            color: #2d3748;
            font-size: 16px;
            font-weight: 600;
            margin: 8px 0 6px 0;
        }
        
        .message.bot .message-content h4 {
            color: #4a5568;
            font-size: 14px;
            font-weight: 600;
            margin: 12px 0 4px 0;
        }
        
        .message.bot .message-content ul {
            margin: 8px 0;
            padding-left: 20px;
        }
        
        .message.bot .message-content li {
            margin: 4px 0;
            line-height: 1.5;
        }
        
        .message.bot .message-content p {
            margin: 8px 0;
            line-height: 1.6;
        }
        
        .tool-info {
            font-size: 12px;
            color: #718096;
            margin-top: 5px;
            font-style: italic;
        }
        
        .chat-input-container {
            padding: 20px;
            background: white;
            border-top: 1px solid #e2e8f0;
            display: flex;
            gap: 10px;
        }
        
        .chat-input {
            flex: 1;
            padding: 12px 16px;
            border: 1px solid #e2e8f0;
            border-radius: 25px;
            font-size: 14px;
            outline: none;
            transition: border-color 0.2s;
        }
        
        .chat-input:focus {
            border-color: #667eea;
        }
        
        .chat-button {
            padding: 12px 20px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 25px;
            font-size: 14px;
            cursor: pointer;
            transition: background 0.2s;
        }
        
        .chat-button:hover {
            background: #5a67d8;
        }
        
        .chat-button:disabled {
            background: #a0aec0;
            cursor: not-allowed;
        }
        
        .status-bar {
            padding: 8px 20px;
            background: #edf2f7;
            border-top: 1px solid #e2e8f0;
            font-size: 12px;
            color: #718096;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .status-indicator {
            display: flex;
            align-items: center;
            gap: 5px;
        }
        
        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #48bb78;
        }
        
        .controls {
            display: flex;
            gap: 10px;
        }
        
        .control-btn {
            padding: 4px 8px;
            background: #e2e8f0;
            border: none;
            border-radius: 4px;
            font-size: 10px;
            cursor: pointer;
            transition: background 0.2s;
        }
        
        .control-btn:hover {
            background: #cbd5e0;
        }
        
        .typing-indicator {
            display: none;
            padding: 12px 16px;
            font-style: italic;
            color: #718096;
            font-size: 14px;
        }
        
        @keyframes typing {
            0%, 60%, 100% { opacity: 0; }
            30% { opacity: 1; }
        }
        
        .typing-dots::after {
            content: '...';
            animation: typing 1.4s infinite;
        }
    </style>
</head>
<body>
    <div class="chat-container">
        <div class="chat-header">
            🤖 Agentic AI Assistant
        </div>
        
        <div class="chat-messages" id="chatMessages">
            <div class="message bot">
                <div class="message-avatar">🤖</div>
                <div class="message-content">
                    Hello! I'm your AI assistant with access to web search, YouTube, weather, and location tools. How can I help you today?
                </div>
            </div>
        </div>
        
        <div class="typing-indicator" id="typingIndicator">
            <div class="message bot">
                <div class="message-avatar">🤖</div>
                <div class="message-content">
                    Assistant is typing<span class="typing-dots"></span>
                </div>
            </div>
        </div>
        
        <div class="chat-input-container">
            <input type="text" class="chat-input" id="chatInput" placeholder="Type your message here..." autocomplete="off">
            <button class="chat-button" id="sendButton">Send</button>
        </div>
        
        <div class="status-bar">
            <div class="status-indicator">
                <div class="status-dot" id="statusDot"></div>
                <span id="statusText">Connecting...</span>
            </div>
            <div class="controls">
                <button class="control-btn" id="memoryBtn">Memory</button>
                <button class="control-btn" id="clearBtn">Clear</button>
            </div>
        </div>
    </div>

    <script>
        class ChatbotClient {
            constructor() {
                this.ws = null;
                this.reconnectAttempts = 0;
                this.maxReconnectAttempts = 5;
                
                this.chatMessages = document.getElementById('chatMessages');
                this.chatInput = document.getElementById('chatInput');
                this.sendButton = document.getElementById('sendButton');
                this.typingIndicator = document.getElementById('typingIndicator');
                this.statusDot = document.getElementById('statusDot');
                this.statusText = document.getElementById('statusText');
                this.memoryBtn = document.getElementById('memoryBtn');
                this.clearBtn = document.getElementById('clearBtn');
                
                this.initWebSocket();
                this.setupEventListeners();
            }
            
            initWebSocket() {
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                const wsUrl = protocol + '//' + window.location.host + '/ws';
                
                console.log('Connecting to WebSocket:', wsUrl);
                this.updateStatus('Connecting...', false);
                
                this.ws = new WebSocket(wsUrl);
                
                this.ws.onopen = () => {
                    console.log('WebSocket connected');
                    this.reconnectAttempts = 0;
                    this.updateStatus('Connected', true);
                };
                
                this.ws.onmessage = (event) => {
                    console.log('Received message:', event.data);
                    try {
                        const data = JSON.parse(event.data);
                        this.handleMessage(data);
                    } catch (error) {
                        console.error('Error parsing message:', error);
                    }
                };
                
                this.ws.onclose = (event) => {
                    console.log('WebSocket closed:', event.code, event.reason);
                    this.updateStatus('Disconnected', false);
                    
                    if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
                        this.scheduleReconnect();
                    }
                };
                
                this.ws.onerror = (error) => {
                    console.error('WebSocket error:', error);
                    this.updateStatus('Connection Error', false);
                };
            }
            
            scheduleReconnect() {
                this.reconnectAttempts++;
                const delay = 1000 * Math.pow(2, this.reconnectAttempts - 1);
                
                console.log('Scheduling reconnect attempt', this.reconnectAttempts, 'in', delay, 'ms');
                this.updateStatus('Reconnecting... (' + this.reconnectAttempts + '/' + this.maxReconnectAttempts + ')', false);
                
                setTimeout(() => {
                    this.initWebSocket();
                }, delay);
            }
            
            setupEventListeners() {
                this.sendButton.onclick = (e) => {
                    e.preventDefault();
                    this.sendMessage();
                };
                
                this.chatInput.onkeypress = (e) => {
                    if (e.key === 'Enter') {
                        e.preventDefault();
                        this.sendMessage();
                    }
                };
                
                this.memoryBtn.onclick = (e) => {
                    e.preventDefault();
                    this.getMemory();
                };
                
                this.clearBtn.onclick = (e) => {
                    e.preventDefault();
                    this.clearMemory();
                };
                
                setTimeout(() => {
                    this.chatInput.focus();
                }, 100);
            }
            
            sendMessage() {
                const message = this.chatInput.value.trim();
                
                if (!message || !this.ws || this.ws.readyState !== WebSocket.OPEN) {
                    return;
                }
                
                this.addMessage('user', message);
                this.chatInput.value = '';
                this.showTyping(true);
                
                this.ws.send(JSON.stringify({
                    type: 'chat',
                    message: message
                }));
            }
            
            getMemory() {
                if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;
                
                this.ws.send(JSON.stringify({ type: 'memory' }));
            }
            
            clearMemory() {
                if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;
                
                this.ws.send(JSON.stringify({ type: 'clear' }));
            }
            
            handleMessage(data) {
                this.showTyping(false);
                
                switch (data.type) {
                    case 'connection':
                        console.log('Connection confirmed');
                        break;
                    case 'response':
                        this.handleChatResponse(data.data);
                        break;
                    case 'memory':
                        this.handleMemoryResponse(data.data);
                        break;
                    case 'clear':
                        this.addMessage('bot', '🗑️ Conversation history cleared!');
                        break;
                    case 'error':
                        this.addMessage('bot', '❌ Error: ' + data.data.error);
                        break;
                }
            }
            
            handleChatResponse(result) {
                if (result.status === 'success') {
                    let content = this.formatResponse(result.response);
                    
                    if (result.tool_calls && result.tool_calls.length > 0) {
                        const tools = result.tool_calls.map(call => call.tool).join(', ');
                        content += '<div class="tool-info">🔧 Tools used: ' + tools + '</div>';
                    }
                    
                    this.addMessage('bot', content);
                } else {
                    this.addMessage('bot', '❌ Error: ' + result.response);
                }
            }
            
            formatResponse(text) {
                let formatted = text;
                
                // Format headers with emojis
                formatted = formatted.replace(/🎯\\s*\\*\\*(.*?)\\*\\*/g, '<h3>🎯 $1</h3>');
                formatted = formatted.replace(/⏰\\s*\\*\\*(.*?)\\*\\*/g, '<h3>⏰ $1</h3>');
                formatted = formatted.replace(/🎨\\s*\\*\\*(.*?)\\*\\*/g, '<h3>🎨 $1</h3>');
                formatted = formatted.replace(/👶\\s*\\*\\*(.*?)\\*\\*/g, '<h3>👶 $1</h3>');
                formatted = formatted.replace(/💡\\s*\\*\\*(.*?)\\*\\*/g, '<h3>💡 $1</h3>');
                formatted = formatted.replace(/🎫\\s*\\*\\*(.*?)\\*\\*/g, '<h3>🎫 $1</h3>');
                formatted = formatted.replace(/🚗\\s*\\*\\*(.*?)\\*\\*/g, '<h3>🚗 $1</h3>');
                formatted = formatted.replace(/❗\\s*\\*\\*(.*?)\\*\\*/g, '<h3>❗ $1</h3>');
                
                // Format bold text
                formatted = formatted.replace(/\\*\\*(.*?)\\*\\*/g, '<h4>$1</h4>');
                
                // Format lists
                formatted = formatted.replace(/^-\\s(.+)$/gm, '<li>$1</li>');
                formatted = formatted.replace(/^(\\d+)\\.\\s(.+)$/gm, '<li>$1. $2</li>');
                formatted = formatted.replace(/((?:<li>.*<\\/li>\\s*)+)/g, '<ul>$1</ul>');
                
                // Format paragraphs
                formatted = formatted.split('\\n\\n').map(function(paragraph) {
                    if (paragraph.trim() && 
                        !paragraph.includes('<h3>') && 
                        !paragraph.includes('<h4>') && 
                        !paragraph.includes('<ul>')) {
                        return '<p>' + paragraph.trim() + '</p>';
                    }
                    return paragraph;
                }).join('\\n\\n');
                
                return formatted;
            }
            
            handleMemoryResponse(summary) {
                const content = '<h3>📊 Memory Summary</h3>' +
                    '<ul>' +
                    '<li><strong>Total conversations:</strong> ' + summary.total_conversations + '</li>' +
                    '<li><strong>Recent topics:</strong> ' + (summary.recent_topics.join(', ') || 'None') + '</li>' +
                    '<li><strong>Session data:</strong> ' + (summary.session_data_keys.join(', ') || 'None') + '</li>' +
                    '</ul>';
                this.addMessage('bot', content);
            }
            
            addMessage(sender, content) {
                const messageDiv = document.createElement('div');
                messageDiv.className = 'message ' + sender;
                
                const avatar = sender === 'user' ? '👤' : '🤖';
                
                messageDiv.innerHTML = 
                    '<div class="message-avatar">' + avatar + '</div>' +
                    '<div class="message-content">' + content + '</div>';
                
                this.chatMessages.appendChild(messageDiv);
                this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
            }
            
            showTyping(show) {
                this.typingIndicator.style.display = show ? 'block' : 'none';
                if (show) {
                    this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
                }
            }
            
            updateStatus(text, connected) {
                this.statusText.textContent = text;
                this.statusDot.style.background = connected ? '#48bb78' : '#f56565';
                this.sendButton.disabled = !connected;
                this.memoryBtn.disabled = !connected;
                this.clearBtn.disabled = !connected;
                this.chatInput.disabled = !connected;
                this.chatInput.placeholder = connected ? "Type your message here..." : "Connecting...";
            }
        }
        
        document.addEventListener('DOMContentLoaded', function() {
            try {
                new ChatbotClient();
            } catch (error) {
                console.error('Error initializing chatbot:', error);
            }
        });
    </script>
</body>
</html>"""
        return html_content

    async def start_server(self, host: str = "localhost", port: int = 8000):
        """Start the web server"""
        import uvicorn
        
        logger.info(f"Starting web server at http://{host}:{port}")
        logger.info("Agent initialized with tools:")
        for tool in self.agent.tools:
            logger.info(f"  - {tool.name}: {tool.description}")
            
        config = uvicorn.Config(
            self.app, 
            host=host, 
            port=port,
            log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()
