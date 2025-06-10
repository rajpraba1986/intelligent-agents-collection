#!/usr/bin/env python3
"""
Conversational AI Memory Check Utility
Run this to check the current state of conversational agent memory
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.agent.memory_manager import MemoryManager
import json

def main():
    print("🧠 Conversational AI Memory Status Check")
    print("=" * 50)
    
    memory_manager = MemoryManager()
    stats = memory_manager.get_memory_stats()
    
    print(f"📊 Total Conversations: {stats['total_conversations']}")
    print(f"💾 Memory File Exists: {stats['memory_file_exists']}")
    
    if stats['memory_file_exists']:
        print(f"📁 File Size: {stats['file_size_kb']} KB")
        
    if stats['total_conversations'] > 0:
        print(f"⏰ Oldest Conversation: {stats['oldest_conversation']}")
        print(f"🕐 Newest Conversation: {stats['newest_conversation']}")
        print(f"🗂️ Session Data Keys: {stats['session_data_keys']}")
        
        print("\n📝 Recent Conversation Topics:")
        for i, topic in enumerate(stats['recent_topics'], 1):
            print(f"   {i}. {topic}")
    else:
        print("📭 No conversations found in memory")
    
    print("\n🔧 Conversation Memory File Location:")
    print(f"   {memory_manager.persistence_file.absolute()}")
    
    print("\n💡 Conversational AI Status: Ready for interactions!")

if __name__ == "__main__":
    main()
