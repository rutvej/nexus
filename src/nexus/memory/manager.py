import os
import json
from typing import List, Dict, Any, Optional

class MemoryManager:
    def __init__(self, memory_dir: str = ".nexus"):
        self.memory_dir = memory_dir
        os.makedirs(self.memory_dir, exist_ok=True)
        
        self.conversation_path = os.path.join(self.memory_dir, "conversation.json")
        self.project_path = os.path.join(self.memory_dir, "project_memory.json")
        
        self.conversation: List[Dict[str, str]] = []
        self.project_data: Dict[str, Any] = {}
        
        self.load()

    def load(self):
        # Load conversation
        if os.path.exists(self.conversation_path):
            try:
                with open(self.conversation_path, "r", encoding="utf-8") as f:
                    self.conversation = json.load(f)
            except Exception:
                self.conversation = []
                
        # Load project memory
        if os.path.exists(self.project_path):
            try:
                with open(self.project_path, "r", encoding="utf-8") as f:
                    self.project_data = json.load(f)
            except Exception:
                self.project_data = {}

    def save(self):
        # Save conversation
        with open(self.conversation_path, "w", encoding="utf-8") as f:
            json.dump(self.conversation, f, indent=2)
            
        # Save project memory
        with open(self.project_path, "w", encoding="utf-8") as f:
            json.dump(self.project_data, f, indent=2)

    def add_message(self, role: str, content: str):
        self.conversation.append({"role": role, "content": content})
        # Keep last 10 messages to fit small context windows
        if len(self.conversation) > 10:
            self.conversation = self.conversation[-10:]
        self.save()

    def get_conversation_history(self) -> List[Dict[str, str]]:
        return self.conversation

    def clear_conversation(self):
        self.conversation = []
        self.save()

    def record_project_fact(self, key: str, value: Any):
        self.project_data[key] = value
        self.save()

    def get_project_fact(self, key: str, default: Any = None) -> Any:
        return self.project_data.get(key, default)

    def get_project_summary(self) -> str:
        if not self.project_data:
            return "No project-specific memory recorded."
        summary = ["Project Memory:"]
        for k, v in self.project_data.items():
            summary.append(f"  - {k}: {v}")
        return "\n".join(summary)
