from typing import List, Dict, Any
from nexus.rag.indexer import RepositoryIndexer

class RAGSearch:
    def __init__(self, indexer: RepositoryIndexer):
        self.indexer = indexer

    def search(self, query: str, limit: int = 3) -> List[Dict[str, Any]]:
        """Search the indexed repository for files or symbols matching the query."""
        results = []
        query_lower = query.lower()
        
        # 1. Search in file names
        for f in self.indexer.files:
            if query_lower in f.lower():
                results.append({
                    "type": "file",
                    "path": f,
                    "score": 0.9,
                    "preview": f"File: {f}"
                })

        # 2. Search in symbol names (classes/functions)
        for path, symbols in self.indexer.symbols.items():
            for s in symbols:
                if query_lower in s.name.lower():
                    results.append({
                        "type": "symbol",
                        "path": path,
                        "name": s.name,
                        "symbol_type": s.symbol_type,
                        "score": 0.85,
                        "preview": f"{s.symbol_type} {s.name} in {path} (lines {s.start_line}-{s.end_line}):\n{s.code[:300]}..."
                    })
                elif query_lower in s.code.lower():
                    # Content match
                    results.append({
                        "type": "content",
                        "path": path,
                        "name": s.name,
                        "symbol_type": s.symbol_type,
                        "score": 0.6,
                        "preview": f"Match in {s.name} ({path}, lines {s.start_line}-{s.end_line}):\n... {query} ..."
                    })

        # Sort by score descending
        results = sorted(results, key=lambda x: x["score"], reverse=True)
        return results[:limit]
