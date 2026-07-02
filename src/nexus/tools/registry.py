from typing import Dict, List, Optional
from nexus.tools.base import BaseTool

class ToolRegistry:
    def __init__(self):
        self.tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        if tool.name in self.tools:
            raise ValueError(f"Tool with name '{tool.name}' is already registered.")
        self.tools[tool.name] = tool

    def get(self, name: str) -> Optional[BaseTool]:
        return self.tools.get(name)

    def list_all(self) -> List[BaseTool]:
        return list(self.tools.values())

    def get_tool_descriptions(self) -> str:
        """Format all tool descriptions for model context."""
        desc_list = []
        for tool in self.tools.values():
            desc_list.append(f"- `{tool.name}`: {tool.description}")
        return "\n".join(desc_list)
