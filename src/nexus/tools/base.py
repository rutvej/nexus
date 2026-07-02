from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional, Dict

class PermissionLevel(Enum):
    READ = "read"           # Safe: read files, search, list dirs
    WRITE = "write"         # Modifying: write files, create, delete
    EXECUTE = "execute"     # Running: terminal commands, python exec
    DANGEROUS = "dangerous" # Risky: delete dirs, git push, format disk

@dataclass
class ToolResult:
    success: bool
    output: str                          # Primary output (stdout, file content, etc.)
    error: Optional[str] = None          # Error message if failed
    metadata: Optional[Dict[str, Any]] = None      # Additional data
    duration_ms: float = 0               # Execution time

class BaseTool(ABC):
    """Base class for all Nexus tools."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique tool name (snake_case)."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description for model context."""
        pass
    
    @property
    @abstractmethod
    def permission_level(self) -> PermissionLevel:
        """Permission level required to execute this tool."""
        pass
    
    @abstractmethod
    def input_schema(self) -> Dict[str, Any]:
        """JSON Schema describing the tool's input parameters."""
        pass
    
    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with validated parameters."""
        pass
    
    @property
    def category(self) -> str:
        """Tool category for grouping (file, search, exec, git, RAG)."""
        return "general"
