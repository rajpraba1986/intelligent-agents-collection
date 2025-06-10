import asyncio
import json
import websockets
from typing import Dict, Any, Optional
from .protocol import MCPProtocol, MCPMessage
import logging

logger = logging.getLogger(__name__)

class MCPClient:
    def __init__(self, host: str = "localhost", port: int = 8080):
        self.host = host
        self.port = port
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.protocol = MCPProtocol()
        self.running = False
        
    async def connect(self):
        """Connect to MCP server"""
        try:
            uri = f"ws://{self.host}:{self.port}"
            self.websocket = await websockets.connect(uri)
            self.running = True
            logger.info(f"Connected to MCP server at {uri}")
            
            # Start message handling loop
            asyncio.create_task(self._message_loop())
            
        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {e}")
            raise
            
    async def disconnect(self):
        """Disconnect from MCP server"""
        self.running = False
        if self.websocket:
            await self.websocket.close()
            
    async def _message_loop(self):
        """Handle incoming messages from server"""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    mcp_message = MCPMessage(**data)
                    response = await self.protocol.handle_message(mcp_message)
                    
                    if response:
                        await self.websocket.send(response.json())
                        
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info("Connection to MCP server closed")
        except Exception as e:
            logger.error(f"Error in message loop: {e}")
            
    async def send_request(self, method: str, params: Dict[str, Any]) -> Any:
        """Send request to MCP server and wait for response"""
        if not self.websocket:
            raise Exception("Not connected to MCP server")
            
        request = self.protocol.create_request(method, params)
        future = asyncio.Future()
        self.protocol.pending_requests[request.id] = future
        
        await self.websocket.send(request.json())
        
        try:
            result = await asyncio.wait_for(future, timeout=30.0)
            return result
        except asyncio.TimeoutError:
            self.protocol.pending_requests.pop(request.id, None)
            raise Exception("Request timeout")