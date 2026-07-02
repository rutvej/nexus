import subprocess
from typing import Dict, Any
from nexus.tools.base import BaseTool, ToolResult, PermissionLevel

class TerminalExecTool(BaseTool):
    @property
    def name(self) -> str:
        return "terminal_exec"

    @property
    def description(self) -> str:
        return "Execute a shell command in the project directory."

    @property
    def permission_level(self) -> PermissionLevel:
        return PermissionLevel.EXECUTE

    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "The shell command to run"}
            },
            "required": ["command"]
        }

    def execute(self, command: str) -> ToolResult:
        try:
            # Run command with a timeout to prevent hanging
            res = subprocess.run(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=60
            )
            
            success = res.returncode == 0
            output = res.stdout
            error = res.stderr if res.stderr else None
            
            metadata = {
                "returncode": res.returncode
            }
            
            if not success and not error:
                error = f"Command failed with exit code {res.returncode}"
                
            return ToolResult(
                success=success,
                output=output,
                error=error,
                metadata=metadata
            )
        except subprocess.TimeoutExpired:
            return ToolResult(success=False, output="", error="Command timed out after 60 seconds.")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
