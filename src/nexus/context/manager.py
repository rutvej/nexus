from typing import List, Dict, Any
from nexus.memory.manager import MemoryManager
from nexus.rag.search import RAGSearch

class ContextManager:
    def __init__(self, memory_manager: MemoryManager, rag_search: RAGSearch, max_tokens: int = 4000):
        self.memory_manager = memory_manager
        self.rag_search = rag_search
        self.max_tokens = max_tokens

    def estimate_tokens(self, text: str) -> int:
        """Estimate tokens using a standard 4-characters-per-token rule."""
        return len(text) // 4

    def assemble_context(self, current_goal: str, query: str = None) -> str:
        """Assemble a budget-constrained context for the model prompt."""
        context_parts = []
        
        # 1. Project Memory
        project_mem = self.memory_manager.get_project_summary()
        context_parts.append(project_mem)
        
        # 2. RAG Search results
        if query:
            rag_results = self.rag_search.search(query, limit=2)
            if rag_results:
                context_parts.append("\nRelevant Code Context:")
                for r in rag_results:
                    context_parts.append(f"--- File: {r['path']} ---")
                    context_parts.append(r["preview"])
                    
        # 3. Conversation History
        history = self.memory_manager.get_conversation_history()
        if history:
            context_parts.append("\nRecent Conversation History:")
            for msg in history:
                context_parts.append(f"{msg['role'].upper()}: {msg['content']}")

        # Combine
        full_context = "\n".join(context_parts)
        
        # Budget Check & Truncation
        estimated = self.estimate_tokens(full_context)
        if estimated > self.max_tokens:
            # If too long, truncate from the middle (keep project memory and latest history)
            # In a production system we would do smart truncation, here we do a simple slice
            chars_limit = self.max_tokens * 4
            full_context = full_context[-chars_limit:]
            
        return full_context
