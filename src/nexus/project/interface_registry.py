import re
from nexus.project.guide import ProjectGuide

class InterfaceRegistry:
    def __init__(self, guide: ProjectGuide):
        self.guide = guide
        self.registry = self._parse_registry()

    def _parse_registry(self) -> dict[str, list[dict]]:
        """
        Parses the Interface Registry section of PROJECT_GUIDE.md.
        Returns a mapping from file path -> list of signature dicts:
        {"file_path": [{"signature": "...", "description": "..."}]}
        """
        content = self.guide.get_section("Interface Registry")
        registry = {}
        current_file = None
        
        for line in content.splitlines():
            line_str = line.strip()
            if line_str.startswith("### "):
                current_file = line_str[4:].strip()
                registry[current_file] = []
            elif line_str.startswith("- ") and current_file:
                # Format: - `signature` — description
                match = re.match(r"-\s+`([^`]+)`\s*(?:—\s*(.*))?", line_str)
                if match:
                    sig = match.group(1).strip()
                    desc = match.group(2).strip() if match.group(2) else ""
                    registry[current_file].append({"signature": sig, "description": desc})
        return registry

    def add_signature(self, file_path: str, signature: str, description: str):
        if file_path not in self.registry:
            self.registry[file_path] = []
        
        # Remove if exists already
        self.registry[file_path] = [item for item in self.registry[file_path] if item["signature"] != signature]
        self.registry[file_path].append({"signature": signature, "description": description})

    def get_related_interfaces(self, current_file: str) -> str:
        """
        Returns all registered signatures EXCEPT for the current file.
        Format:
        ### file_path
        - `signature` - description
        """
        lines = []
        for file_path, items in self.registry.items():
            if file_path == current_file:
                continue
            if items:
                mod_path = file_path.replace("\\", "/").replace(".py", "").replace("/", ".")
                lines.append(f"### {file_path} (Import path: {mod_path})")
                for item in items:
                    lines.append(f"- `{item['signature']}` — {item['description']}")
        return "\n".join(lines)

    def to_markdown(self) -> str:
        lines = ["## Interface Registry"]
        for file_path, items in sorted(self.registry.items()):
            if items:
                lines.append(f"\n### {file_path}")
                for item in items:
                    lines.append(f"- `{item['signature']}` — {item['description']}")
        return "\n".join(lines)

    def save(self):
        markdown = self.to_markdown()
        self.guide.update_section("Interface Registry", markdown)
