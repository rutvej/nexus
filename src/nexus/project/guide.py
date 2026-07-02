import os
from pathlib import Path
from nexus import config

DEFAULT_GUIDE_CONTENT = """# Nexus Project Guide

## 1. Technology Stack
- Language: Python 3.12
- Database: SQLite
- Framework: Flask

## 2. Directory Structure
- src/: Core implementation files
- tests/: Unit and integration tests

## 3. Active Schemas
None yet.

## 4. Architectural Conventions
- All database operations must utilize the sqlite3 context manager.
"""

class ProjectGuide:
    def __init__(self, guide_path: str = None):
        if guide_path:
            self.guide_path = Path(guide_path)
        else:
            self.guide_path = config.WORKSPACE_DIR / ".nexus" / "PROJECT_GUIDE.md"
        # Ensure parent directory exists
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

    def update_section(self, heading: str, content: str):
        """
        Updates a section identified by a heading (e.g. '## 3. Active Schemas' or '## Interface Registry').
        If the heading is found, replaces the content under it up to the next heading of same or higher level.
        If the heading is not found, appends it.
        """
        current_guide = self.read()
        lines = current_guide.splitlines()
        
        heading_index = -1
        # Find heading index
        for idx, line in enumerate(lines):
            if line.strip() == heading.strip():
                heading_index = idx
                break
        
        if heading_index == -1:
            # Heading not found, append to the end
            new_guide = current_guide.rstrip() + f"\n\n{heading}\n{content}\n"
            self.write(new_guide)
            return

        # Determine heading level (number of leading #)
        level = len(heading) - len(heading.lstrip('#'))

        # Find the next heading of the same or higher level (i.e. number of '#' <= level)
        next_heading_index = -1
        for idx in range(heading_index + 1, len(lines)):
            line = lines[idx]
            if line.startswith('#'):
                # Check level
                line_level = len(line) - len(line.lstrip('#'))
                if line_level <= level:
                    next_heading_index = idx
                    break

        new_lines = lines[:heading_index + 1]
        # Append the new section content
        new_lines.extend(content.splitlines())
        
        if next_heading_index != -1:
            # Append the remaining lines after the next heading
            new_lines.extend(lines[next_heading_index:])
            
        self.write("\n".join(new_lines) + "\n")
