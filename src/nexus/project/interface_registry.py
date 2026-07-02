import re
from typing import Dict, List, Tuple
from nexus.project.guide import ProjectGuide

class InterfaceRegistry:
    def __init__(self, guide: ProjectGuide):
        self.guide = guide

    def _parse_registry(self) -> Dict[str, List[Tuple[str, str]]]:
        """
        Parses the ## Interface Registry section of the PROJECT_GUIDE.md.
        Returns a dict mapping file_path -> list of (signature, doc).
        """
        content = self.guide.read()
        lines = content.splitlines()
        
        # Find the start of the Interface Registry
        start_idx = -1
        for idx, line in enumerate(lines):
            if line.strip() == "## Interface Registry":
                start_idx = idx
                break
                
        if start_idx == -1:
            return {}

        # Determine level of the heading
        level = 2 # '## Interface Registry' is level 2

        # Extract all lines under ## Interface Registry until next heading of same or higher level
        registry_lines = []
        for idx in range(start_idx + 1, len(lines)):
            line = lines[idx]
            if line.startswith('#'):
                line_level = len(line) - len(line.lstrip('#'))
                if line_level <= level:
                    break
            registry_lines.append(line)

        registry: Dict[str, List[Tuple[str, str]]] = {}
        current_file = None

        for line in registry_lines:
            line_str = line.strip()
            if not line_str:
                continue
            
            # Match file header e.g. "### src/models/user.py"
            if line_str.startswith("### "):
                current_file = line_str[4:].strip()
                registry[current_file] = []
            elif line_str.startswith("- ") and current_file:
                # Parse list item e.g. "- `create_user(...)` — Returns ..."
                # Regex to match: - `signature` — description OR - `signature` - description
                match = re.match(r"^-\s+`([^`]+)`\s+[—\-]\s+(.*)$", line_str)
                if match:
                    sig, doc = match.groups()
                    registry[current_file].append((sig.strip(), doc.strip()))
                else:
                    # Fallback if separator is different
                    match_fallback = re.match(r"^-\s+`([^`]+)`(.*)$", line_str)
                    if match_fallback:
                        sig, rest = match_fallback.groups()
                        doc = rest.strip().lstrip('—-').strip()
                        registry[current_file].append((sig.strip(), doc))

        return registry

    def register_interface(self, file_path: str, function_signature: str, description: str):
        """Registers or updates a function signature for a specific file path."""
        registry = self._parse_registry()
        
        if file_path not in registry:
            registry[file_path] = []

        # Check if function signature already exists (by function name)
        func_name = function_signature.split('(')[0].replace('def ', '').strip()
        
        updated = False
        for idx, (sig, doc) in enumerate(registry[file_path]):
            existing_name = sig.split('(')[0].replace('def ', '').strip()
            if existing_name == func_name:
                registry[file_path][idx] = (function_signature, description)
                updated = True
                break
                
        if not updated:
            registry[file_path].append((function_signature, description))

        # Re-format to markdown
        md_lines = []
        for path, funcs in sorted(registry.items()):
            if not funcs:
                continue
            md_lines.append(f"### {path}")
            for sig, doc in funcs:
                md_lines.append(f"- `{sig}` — {doc}")
            md_lines.append("") # empty line between files

        section_content = "\n" + "\n".join(md_lines)
        self.guide.update_section("## Interface Registry", section_content)

    def get_interfaces_for_file(self, file_path: str) -> List[Tuple[str, str]]:
        """Returns list of (signature, doc) for a given file."""
        registry = self._parse_registry()
        return registry.get(file_path, [])
