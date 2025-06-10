import json
import asyncio
import websockets
from typing import Dict, Any, Optional, Callable
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

class MCPMessage(BaseModel):
    type: str
    id: Optional[str] = None
    method: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None

class MCPProtocol:
    def __init__(self):
        self.handlers: Dict[str, Callable] = {}
        self.pending_requests: Dict[str, asyncio.Future] = {}
        
    def register_handler(self, method: str, handler: Callable):
        """Register a handler for a specific MCP method"""
        self.handlers[method] = handler
        
    async def handle_message(self, message: MCPMessage) -> Optional[MCPMessage]:
        """Handle incoming MCP message"""
        if message.type == "request":
            if message.method in self.handlers:
                try:
                    result = await self.handlers[message.method](message.params or {})
                    return MCPMessage(
                        type="response",
                        id=message.id,
                        result=result
                    )
                except Exception as e:
                    logger.error(f"Error handling {message.method}: {e}")
                    return MCPMessage(
                        type="response",
                        id=message.id,
                        error={"code": -1, "message": str(e)}
                    )
            else:
                return MCPMessage(
                    type="response",
                    id=message.id,
                    error={"code": -32601, "message": "Method not found"}
                )
        elif message.type == "response":
            if message.id and message.id in self.pending_requests:
                future = self.pending_requests.pop(message.id)
                if message.error:
                    future.set_exception(Exception(message.error["message"]))
                else:
                    future.set_result(message.result)
                    
        return None
        
    def create_request(self, method: str, params: Dict[str, Any]) -> MCPMessage:
        """Create a new MCP request message"""
        request_id = f"req_{asyncio.get_event_loop().time()}"
        return MCPMessage(
            type="request",
            id=request_id,
            method=method,
            params=params
        )