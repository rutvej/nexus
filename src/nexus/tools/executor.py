import os
import time
from typing import Dict, Any, Tuple
from nexus.tools.base import BaseTool, ToolResult, PermissionLevel
from nexus.tools.registry import ToolRegistry
from nexus.config.config import Config
from rich.console import Console

class ToolExecutor:
    def __init__(self, registry: ToolRegistry, config: Config):
        self.registry = registry
        self.config = config
        self.console = Console()
        self.session_approved_patterns = set() # To store "allow always" for this session

    def _check_path_restriction(self, path: str) -> bool:
        """Check if the path is within the allowed directories."""
        if not path:
            return True
            
        abs_path = os.path.abspath(path)
        project_root = os.getcwd()
        
        # Check if it starts with project root
        # (This is a simple path sandbox)
        if not abs_path.startswith(project_root):
            return False
            
        # Check against denied paths
        denied_paths = self.config.get("permissions.denied_paths", [])
        for dp in denied_paths:
            if dp in abs_path:
                return False
                
        return True

    def _requires_user_approval(self, tool: BaseTool, args: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Check if the tool execution requires user approval.
        Returns (requires_approval, reason).
        """
        profile = self.config.get("agent.permission_profile", "balanced")
        perm = tool.permission_level
        
        # Check path restrictions for file tools
        if "path" in args:
            if not self._check_path_restriction(args["path"]):
                return True, "Access to path outside project root is restricted."

        # Check if already approved in this session
        session_key = f"{tool.name}:{str(args)}"
        if session_key in self.session_approved_patterns:
            return False, "Session approved."

        if profile == "conservative":
            if perm in (PermissionLevel.WRITE, PermissionLevel.EXECUTE):
                return True, f"Permission level {perm.value.upper()} requires approval in CONSERVATIVE profile."
            elif perm == PermissionLevel.DANGEROUS:
                return True, "DANGEROUS operations are restricted."
        elif profile == "balanced":
            if perm in (PermissionLevel.EXECUTE, PermissionLevel.DANGEROUS):
                return True, f"Permission level {perm.value.upper()} requires approval in BALANCED profile."
        elif profile == "permissive":
            if perm == PermissionLevel.DANGEROUS:
                return True, "DANGEROUS operations require approval in PERMISSIVE profile."
                
        return False, ""

    def execute(self, tool_name: str, args: Dict[str, Any]) -> ToolResult:
        tool = self.registry.get(tool_name)
        if not tool:
            return ToolResult(success=False, output="", error=f"Tool '{tool_name}' not found.")

        # Check path restrictions first
        if "path" in args:
            if not self._check_path_restriction(args["path"]):
                return ToolResult(
                    success=False, 
                    output="", 
                    error=f"Permission Denied: Access to path '{args['path']}' is restricted."
                )

        # Check permissions and request user approval if needed
        req_approval, reason = self._requires_user_approval(tool, args)
        if req_approval:
            self.console.print(f"\n[bold yellow]🔧 Tool Approval Required[/bold yellow]")
            self.console.print(f"Tool: [bold]{tool.name}[/bold]")
            self.console.print(f"Arguments: {args}")
            self.console.print(f"Reason: {reason}")
            
            choice = input("Allow execution? [y] Yes (once) | [a] Yes (always this session) | [n] No: ").strip().lower()
            if choice == "y":
                pass
            elif choice == "a":
                session_key = f"{tool.name}:{str(args)}"
                self.session_approved_patterns.add(session_key)
            else:
                return ToolResult(success=False, output="", error="Permission denied by user.")

        # Execute
        start_time = time.time()
        try:
            result = tool.execute(**args)
            result.duration_ms = (time.time() - start_time) * 1000
            return result
        except Exception as e:
            return ToolResult(
                success=False, 
                output="", 
                error=f"Tool execution failed: {str(e)}",
                duration_ms=(time.time() - start_time) * 1000
            )
