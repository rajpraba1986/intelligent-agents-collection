import asyncio
import logging
import argparse
from typing import Dict, Any
from agent.agent_core import AgentCore  # Fixed import path
from mcp import MCPClient
from config.settings import settings
from web_server import ChatbotWebServer

# Setup logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AgenticAIMCP:
    def __init__(self):
        self.agent = AgentCore()
        self.mcp_client = MCPClient(settings.mcp_server_host, settings.mcp_server_port)
        self.running = False
        
    async def start(self):
        """Start the agentic AI application"""
        try:
            logger.info("Starting Agentic AI MCP Application...")
            
            # Initialize agent
            logger.info("Agent initialized with tools:")
            for tool in self.agent.tools:
                logger.info(f"  - {tool.name}: {tool.description}")
                
            # Setup MCP handlers
            self.setup_mcp_handlers()
            
            # Try to connect to MCP server (optional)
            try:
                await self.mcp_client.connect()
                logger.info("Connected to MCP server")
            except Exception as e:
                logger.warning(f"Could not connect to MCP server: {e}")
                logger.info("Running in standalone mode...")
                
            self.running = True
            logger.info("Application started successfully!")
            
            # Start interactive session
            await self.interactive_session()
            
        except Exception as e:
            logger.error(f"Error starting application: {e}")
            raise
            
    def setup_mcp_handlers(self):
        """Setup MCP protocol handlers"""
        async def handle_chat(params: Dict[str, Any]) -> Dict[str, Any]:
            """Handle chat messages via MCP"""
            message = params.get("message", "")
            result = await self.agent.process_message(message)
            return result
            
        async def handle_memory_summary(params: Dict[str, Any]) -> Dict[str, Any]:
            """Handle memory summary requests"""
            return self.agent.get_memory_summary()
            
        async def handle_clear_memory(params: Dict[str, Any]) -> Dict[str, Any]:
            """Handle memory clearing requests"""
            self.agent.clear_memory()
            return {"status": "Memory cleared successfully"}
            
        # Register MCP handlers
        self.mcp_client.protocol.register_handler("chat", handle_chat)
        self.mcp_client.protocol.register_handler("memory_summary", handle_memory_summary)
        self.mcp_client.protocol.register_handler("clear_memory", handle_clear_memory)
        
    async def interactive_session(self):
        """Run interactive chat session"""
        print("\n" + "="*60)
        print("🤖 Agentic AI Assistant with MCP Protocol")
        print("="*60)
        print("Available tools: Web Search, YouTube, Weather, Location")
        print("Type 'quit', 'exit', or 'bye' to end the session")
        print("Type 'memory' to see conversation summary")
        print("Type 'clear' to clear conversation history")
        print("="*60 + "\n")
        
        while self.running:
            try:
                # Get user input
                user_input = input("You: ").strip()
                
                if not user_input:
                    continue
                    
                # Handle special commands
                if user_input.lower() in ['quit', 'exit', 'bye']:
                    break
                elif user_input.lower() == 'memory':
                    summary = self.agent.get_memory_summary()
                    print(f"\n📊 Memory Summary:")
                    print(f"Total conversations: {summary['total_conversations']}")
                    print(f"Recent topics: {summary['recent_topics']}")
                    print(f"Session data: {summary['session_data_keys']}")
                    print()
                    continue
                elif user_input.lower() == 'clear':
                    self.agent.clear_memory()
                    print("🗑️ Conversation history cleared!\n")
                    continue
                    
                # Process message with agent
                print("🤖 Assistant: ", end="", flush=True)
                result = await self.agent.process_message(user_input)
                
                if result["status"] == "success":
                    print(result["response"])
                    
                    # Show tool usage if any
                    if result["tool_calls"]:
                        print(f"\n🔧 Tools used: {', '.join([call['tool'] for call in result['tool_calls']])}")
                        
                else:
                    print(f"❌ Error: {result['response']}")
                    
                print()  # Empty line for readability
                
            except KeyboardInterrupt:
                print("\n\nGoodbye! 👋")
                break
            except Exception as e:
                logger.error(f"Error in interactive session: {e}")
                print(f"❌ An error occurred: {e}\n")
                
    async def stop(self):
        """Stop the application"""
        self.running = False
        if self.mcp_client:
            await self.mcp_client.disconnect()
        logger.info("Application stopped")
    
    async def start_web_server(self, host: str = "localhost", port: int = 8000):
        """Start the web-based chatbot interface"""
        web_server = ChatbotWebServer()
        await web_server.start_server(host, port)

async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Agentic AI MCP Application")
    parser.add_argument("--mode", choices=["cli", "web"], default="cli", 
                       help="Run mode: cli for terminal interface, web for web interface")
    parser.add_argument("--host", default="localhost", 
                       help="Host for web server (default: localhost)")
    parser.add_argument("--port", type=int, default=8000, 
                       help="Port for web server (default: 8000)")
    
    args = parser.parse_args()
    
    if args.mode == "web":
        # Start web server
        web_server = ChatbotWebServer()
        print(f"\n🌐 Starting web interface at http://{args.host}:{args.port}")
        print("Open this URL in your browser to use the chatbot!")
        print("Press Ctrl+C to stop the server\n")
        
        try:
            await web_server.start_server(args.host, args.port)
        except KeyboardInterrupt:
            print("\nShutting down web server...")
    else:
        # Start CLI mode
        app = AgenticAIMCP()
        
        try:
            await app.start()
        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            await app.stop()

if __name__ == "__main__":
    asyncio.run(main())