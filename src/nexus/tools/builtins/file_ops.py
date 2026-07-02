import os
from typing import Dict, Any
from nexus.tools.base import BaseTool, ToolResult, PermissionLevel

class FileReadTool(BaseTool):
    @property
    def name(self) -> str:
        return "read_file"

    @property
    def description(self) -> str:
        return "Read the full contents of a file at the given path."

    @property
    def permission_level(self) -> PermissionLevel:
        return PermissionLevel.READ

    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative or absolute path to the file"}
            },
            "required": ["path"]
        }

    def execute(self, path: str) -> ToolResult:
        try:
            if not os.path.exists(path):
                return ToolResult(success=False, output="", error=f"File not found: {path}")
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            return ToolResult(success=True, output=content)
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))

class FileWriteTool(BaseTool):
    @property
    def name(self) -> str:
        return "write_file"

    @property
    def description(self) -> str:
        return "Write content to a file at the given path, overwriting it if it exists."

    @property
    def permission_level(self) -> PermissionLevel:
        return PermissionLevel.WRITE

    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative or absolute path to the file"},
                "content": {"type": "string", "description": "The content to write"}
            },
            "required": ["path", "content"]
        }

    def execute(self, path: str, content: str) -> ToolResult:
        try:
            # Ensure parent directories exist
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return ToolResult(success=True, output=f"Successfully wrote to file: {path}")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))

class ListDirTool(BaseTool):
    @property
    def name(self) -> str:
        return "list_dir"

    @property
    def description(self) -> str:
        return "List all files and subdirectories in a directory."

    @property
    def permission_level(self) -> PermissionLevel:
        return PermissionLevel.READ

    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative or absolute path to the directory (defaults to current directory)"}
            }
        }

    def execute(self, path: str = ".") -> ToolResult:
        try:
            if not os.path.exists(path):
                return ToolResult(success=False, output="", error=f"Directory not found: {path}")
            items = os.listdir(path)
            output_list = []
            for item in items:
                full_path = os.path.join(path, item)
                if os.path.isdir(full_path):
                    output_list.append(f"[DIR]  {item}/")
                else:
                    size = os.path.getsize(full_path)
                    output_list.append(f"[FILE] {item} ({size} bytes)")
            return ToolResult(success=True, output="\n".join(output_list))
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))

class ReplaceTextTool(BaseTool):
    @property
    def name(self) -> str:
        return "replace_text"

    @property
    def description(self) -> str:
        return "Replace a target string with a replacement string in a file."

    @property
    def permission_level(self) -> PermissionLevel:
        return PermissionLevel.WRITE

    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the file"},
                "target": {"type": "string", "description": "The exact string to find and replace"},
                "replacement": {"type": "string", "description": "The string to replace the target with"}
            },
            "required": ["path", "target", "replacement"]
        }

    def execute(self, path: str, target: str, replacement: str) -> ToolResult:
        try:
            if not os.path.exists(path):
                return ToolResult(success=False, output="", error=f"File not found: {path}")
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            
            if target not in content:
                return ToolResult(success=False, output="", error=f"Target string not found in file: {path}")
                
            new_content = content.replace(target, replacement)
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_content)
                
            return ToolResult(success=True, output=f"Successfully replaced text in file: {path}")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
