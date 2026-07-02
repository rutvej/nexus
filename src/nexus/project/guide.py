import os
from pathlib import Path
from nexus import config

DEFAULT_GUIDE_CONTENT = """# PROJECT GUIDE

## Tech Stack
- Python

## Directory Structure
- src/

## Data Schemas

## Interface Registry
"""

class ProjectGuide:
    def __init__(self, workspace_path: str = None):
        self.workspace_path = Path(workspace_path or config.WORKSPACE_DIR)
        self.guide_path = self.workspace_path / ".nexus" / "PROJECT_GUIDE.md"
        self.guide_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.guide_path.exists():
            self.write(DEFAULT_GUIDE_CONTENT)

    def read(self) -> str:
        if not self.guide_path.exists():
            return ""
        with open(self.guide_path, "r", encoding="utf-8") as f:
            return f.read()

    def write(self, content: str):
        with open(self.guide_path, "w", encoding="utf-8") as f:
            f.write(content)

    def get_section(self, section_name: str) -> str:
        """
        Reads a specific header section (e.g. "## Data Schemas") up to the next heading.
        """
        content = self.read()
        lines = content.splitlines()
        section_lines = []
        in_section = False
        
        for line in lines:
            clean_line = line.strip()
            is_header = (clean_line.startswith("## ") or clean_line.startswith("# ")) and not clean_line.startswith("###")
            if is_header:
                if in_section:
                    break
                if section_name.lower() in clean_line.lower():
                    in_section = True
                    section_lines.append(line)
            elif in_section:
                section_lines.append(line)
                
        return "\n".join(section_lines)

    def update_section(self, section_name: str, new_content: str):
        """
        Replaces the content under section_name with new_content.
        """
        content = self.read()
        lines = content.splitlines()
        new_lines = []
        in_section = False
        replaced = False
        
        for line in lines:
            clean_line = line.strip()
            is_header = (clean_line.startswith("## ") or clean_line.startswith("# ")) and not clean_line.startswith("###")
            if is_header:
                if in_section:
                    in_section = False
                if section_name.lower() in clean_line.lower():
                    in_section = True
                    new_lines.append(new_content.strip())
                    replaced = True
                    continue
            if not in_section:
                new_lines.append(line)
                
        if not replaced:
            # If section wasn't found, append it at the end
            new_lines.append("")
            new_lines.append(new_content.strip())
            
        self.write("\n".join(new_lines) + "\n")
