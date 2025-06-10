import json
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel
from pathlib import Path

class ConversationTurn(BaseModel):
    timestamp: datetime
    user_message: str
    agent_response: str
    tool_calls: List[Dict[str, Any]] = []
    metadata: Dict[str, Any] = {}

class MemoryManager:
    def __init__(self, memory_file: str = "conversation_memory.json"):
        self.memory_file = memory_file
        self.conversation_history: List[ConversationTurn] = []
        self.session_memory: Dict[str, Any] = {}
        self.persistence_file = Path(memory_file)
        self.load_from_file()
        
    def add_conversation_turn(
        self, 
        user_message: str, 
        agent_response: str, 
        tool_calls: List[Dict[str, Any]] = None,
        metadata: Dict[str, Any] = None
    ):
        """Add a new conversation turn to memory"""
        turn = ConversationTurn(
            timestamp=datetime.now(),
            user_message=user_message,
            agent_response=agent_response,
            tool_calls=tool_calls or [],
            metadata=metadata or {}
        )
        
        self.conversation_history.append(turn)
        self.save_to_file()
        
    def get_recent_history(self, num_turns: int = 5) -> List[ConversationTurn]:
        """Get recent conversation history"""
        return self.conversation_history[-num_turns:] if self.conversation_history else []
        
    def get_context_for_llm(self, num_turns: int = 5) -> str:
        """Format recent conversation history for LLM context"""
        recent_history = self.get_recent_history(num_turns)
        
        if not recent_history:
            return "No previous conversation history."
            
        context_parts = ["Previous conversation context:"]
        
        for i, turn in enumerate(recent_history, 1):
            context_parts.append(f"\nTurn {i}:")
            context_parts.append(f"User: {turn.user_message}")
            context_parts.append(f"Assistant: {turn.agent_response}")
            
            if turn.tool_calls:
                context_parts.append("Tools used:")
                for tool_call in turn.tool_calls:
                    context_parts.append(f"  - {tool_call.get('tool', 'Unknown')}: {tool_call.get('result', 'No result')}")
                    
        return "\n".join(context_parts)
        
    def set_session_data(self, key: str, value: Any):
        """Store data in session memory"""
        self.session_memory[key] = value
        self.save_to_file()
        
    def get_session_data(self, key: str, default: Any = None) -> Any:
        """Retrieve data from session memory"""
        return self.session_memory.get(key, default)
        
    def search_history(self, query: str, max_results: int = 3) -> List[ConversationTurn]:
        """Search conversation history for relevant context"""
        query_lower = query.lower()
        relevant_turns = []
        
        for turn in self.conversation_history:
            if (query_lower in turn.user_message.lower() or 
                query_lower in turn.agent_response.lower()):
                relevant_turns.append(turn)
                
        return relevant_turns[-max_results:] if relevant_turns else []
        
    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history = []
        self.save_to_file()
        
    def save_to_file(self):
        """Save conversation history to file"""
        try:
            # Prepare data for serialization
            data = {
                'conversation_history': [
                    {
                        'user_message': turn.user_message,
                        'agent_response': turn.agent_response,
                        'timestamp': turn.timestamp.isoformat(),
                        'tool_calls': turn.tool_calls,
                        'metadata': turn.metadata
                    }
                    for turn in self.conversation_history
                ],
                'session_memory': self.session_memory,
                'last_updated': datetime.now().isoformat()
            }
            
            # Save to file
            with open(self.persistence_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"Error saving memory to file: {e}")
    
    def load_from_file(self):
        """Load conversation history from file"""
        try:
            if self.persistence_file.exists():
                with open(self.persistence_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                # Reconstruct conversation history
                for item in data.get('conversation_history', []):
                    turn = ConversationTurn(
                        user_message=item['user_message'],
                        agent_response=item['agent_response'],
                        timestamp=datetime.fromisoformat(item['timestamp']),
                        tool_calls=item.get('tool_calls', []),
                        metadata=item.get('metadata', {})
                    )
                    self.conversation_history.append(turn)
                
                # Load session memory
                self.session_memory = data.get('session_memory', {})
                
        except Exception as e:
            print(f"Error loading memory from file: {e}")
            # Initialize empty if loading fails
            self.conversation_history = []
            self.session_memory = {}
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get detailed memory statistics"""
        if not self.conversation_history:
            return {
                "total_conversations": 0,
                "memory_file_exists": self.persistence_file.exists(),
                "file_size": 0,
                "oldest_conversation": None,
                "newest_conversation": None
            }
        
        file_size = self.persistence_file.stat().st_size if self.persistence_file.exists() else 0
        
        return {
            "total_conversations": len(self.conversation_history),
            "memory_file_exists": self.persistence_file.exists(),
            "file_size_kb": round(file_size / 1024, 2),
            "oldest_conversation": self.conversation_history[0].timestamp.isoformat(),
            "newest_conversation": self.conversation_history[-1].timestamp.isoformat(),
            "session_data_keys": list(self.session_memory.keys()),
            "recent_topics": [
                turn.user_message[:50] + "..." if len(turn.user_message) > 50 else turn.user_message
                for turn in self.get_recent_history(5)
            ]
        }