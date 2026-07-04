import os
import re
from nexus.tickets.models import Ticket, TicketType, TicketStatus
from nexus.tickets.templates import (
    WRITE_FUNCTION_PROMPT,
    WRITE_TEST_PROMPT,
    FIX_BUG_PROMPT
)
from nexus.llm.router import ModelRouter

class Worker:
    def __init__(self, router: ModelRouter, workspace_dir: str):
        self.router = router
        self.workspace_dir = workspace_dir

    def extract_code(self, llm_text: str) -> str:
        """
        Cleans LLM response to extract pure python code.
        Strips markdown code block wrappers (```python or ```) and leading/trailing spaces.
        """
        cleaned = llm_text.strip()
        # Look for ```python ... ```
        match = re.search(r"```python\s*(.*?)\s*```", cleaned, re.DOTALL)
        if match:
            cleaned = match.group(1).strip()
        else:
            # Look for ``` ... ```
            match = re.search(r"```\s*(.*?)\s*```", cleaned, re.DOTALL)
            if match:
                cleaned = match.group(1).strip()
            
        # Strip leftover ticket ID markers (e.g. lines starting with TKT- or # TKT-)
        lines = []
        for line in cleaned.splitlines():
            stripped = line.strip()
            if re.match(r"^#?\s*TKT-\d+(?:\s|:|$)", stripped, re.IGNORECASE):
                continue
            lines.append(line)
        cleaned = "\n".join(lines).strip()
            
        return cleaned

    def execute_ticket(self, ticket: Ticket) -> bool:
        """
        Generates code for the ticket and writes it to the target file.
        Returns True if successful, False on failure.
        """
        full_path = os.path.join(self.workspace_dir, ticket.target_file)
        
        # Fallback: if CREATE_FILE has a function signature, treat it as WRITE_FUNCTION
        ticket_type = ticket.type
        if ticket_type == TicketType.CREATE_FILE and ticket.function_signature:
            ticket_type = TicketType.WRITE_FUNCTION

        # Determine prompt based on ticket type
        if ticket_type == TicketType.WRITE_FUNCTION:
            prompt = WRITE_FUNCTION_PROMPT.format(
                function_signature=ticket.function_signature,
                parameters=ticket.parameters,
                return_type=ticket.return_type,
                dependencies=ticket.dependencies,
                description=ticket.description,
                related_interfaces=ticket.related_interfaces
            )
            if os.path.exists(full_path):
                with open(full_path, "r", encoding="utf-8") as f:
                    existing_content = f.read()
                if existing_content.strip():
                    prompt += f"\n\nEXISTING FILE CONTENT (your function must be compatible with this code):\n```python\n{existing_content}\n```"
        elif ticket_type == TicketType.WRITE_TEST:
            prompt = WRITE_TEST_PROMPT.format(
                function_signature=ticket.function_signature,
                description=ticket.description,
                return_type=ticket.return_type,
                target_file=ticket.dependencies
            )
        elif ticket_type == TicketType.FIX_BUG:
            prompt = FIX_BUG_PROMPT.format(
                function_signature=ticket.function_signature,
                error_log=ticket.error_log,
                description=ticket.description
            )
            if os.path.exists(full_path):
                with open(full_path, "r", encoding="utf-8") as f:
                    existing_content = f.read()
                if existing_content.strip():
                    prompt += f"\n\nEXISTING FILE CONTENT (your fix must be compatible with this code):\n```python\n{existing_content}\n```"
        else:
            # For CREATE_FILE or others, use a simple generic prompt with critical rules
            prompt = (
                f"Create file {ticket.target_file}. Description: {ticket.description}.\n"
                "CRITICAL RULES:\n"
                "- Use ONLY the Python standard library and Flask. Do NOT import or use SQLAlchemy, Django, or other third-party ORMs/libraries.\n"
                "- Output ONLY pure, executable Python code. No markdown, no explanations."
            )

        response = self.router.route_and_generate(prompt, ticket)
        if not response.success:
            ticket.error_log = response.error
            return False

        ticket.llm_output = response.text
        code = self.extract_code(response.text)
        
        # Apply auto-fix imports
        code = self._auto_fix_imports(code)
        
        # Write code to file
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        if ticket_type == TicketType.WRITE_FUNCTION:
            if os.path.exists(full_path):
                with open(full_path, "r", encoding="utf-8") as f:
                    existing_content = f.read()
                code = self._deduplicate_code(existing_content, code)

            # If function ticket, write signature + body or prepend dependencies if file empty
            func_name_match = re.search(r"def\s+(\w+)\s*\(", ticket.function_signature)
            has_signature = False
            if func_name_match:
                func_name = func_name_match.group(1)
                if re.search(r"\bdef\s+" + re.escape(func_name) + r"\b", code):
                    has_signature = True

            with open(full_path, "a" if os.path.exists(full_path) else "w", encoding="utf-8") as f:
                # Add imports if creating new file
                if f.tell() == 0 and ticket.dependencies:
                    # Sanitize to ensure it's not a ticket ID hallucinated by the model
                    deps = ticket.dependencies.strip()
                    parts = re.split(r"[,;\n]", deps)
                    valid_deps = []
                    for part in parts:
                        part = part.strip()
                        if not part:
                            continue
                        if re.match(r"^TKT-\d+", part, re.IGNORECASE):
                            continue
                        if part.startswith("import ") or part.startswith("from "):
                            valid_deps.append(part)
                        else:
                            # Try to prefix with import
                            valid_deps.append(f"import {part}")
                    if valid_deps:
                        f.write("\n".join(valid_deps) + "\n\n")
                
                if has_signature:
                    f.write(f"\n{code}\n")
                else:
                    # Write the function signature and the body
                    sig_with_colon = ticket.function_signature.strip()
                    if not sig_with_colon.endswith(":"):
                        sig_with_colon += ":"
                    f.write(f"\n{sig_with_colon}\n")
                    # Indent the body lines if needed, or assume model returns indented body
                    indented_code = ""
                    for line in code.splitlines():
                        if line.strip() and not line.startswith("    "):
                            indented_code += "    " + line + "\n"
                        else:
                            indented_code += line + "\n"
                    f.write(indented_code + "\n")
        elif ticket_type == TicketType.FIX_BUG:
            # Modify/replace the function in the existing file rather than wiping the whole file
            if os.path.exists(full_path):
                with open(full_path, "r", encoding="utf-8") as f:
                    existing_code = f.read()
                updated_code = self._replace_function_in_code(existing_code, ticket.function_signature, code)
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(updated_code)
            else:
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(code + "\n")
        else:
            # Direct overwrite for CREATE_FILE, WRITE_TEST
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(code + "\n")
                
        return True

    def _replace_function_in_code(self, existing_code: str, sig: str, new_function_body: str) -> str:
        """
        Replaces a function's body in the existing file using the signature name.
        """
        match = re.search(r"def\s+(\w+)\s*\(", sig)
        if not match:
            return existing_code + "\n" + new_function_body
            
        func_name = match.group(1)
        lines = existing_code.splitlines()
        
        start_idx = -1
        end_idx = -1
        def_indent = 0
        
        for i, line in enumerate(lines):
            if re.search(r"\bdef\s+" + re.escape(func_name) + r"\b", line):
                start_idx = i
                def_indent = len(line) - len(line.lstrip())
                break
                
        if start_idx == -1:
            return existing_code + "\n" + new_function_body

        for j in range(start_idx + 1, len(lines)):
            line = lines[j]
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            indent = len(line) - len(line.lstrip())
            if indent <= def_indent:
                end_idx = j
                break
        else:
            end_idx = len(lines)
            
        formatted_body = ""
        for line in new_function_body.splitlines():
            if line.strip() and not line.startswith("    "):
                formatted_body += "    " + line + "\n"
            else:
                formatted_body += line + "\n"
                
        # Check if new_function_body already contains def func_name
        if re.search(r"\bdef\s+" + re.escape(func_name) + r"\b", new_function_body):
            new_func_block = new_function_body
        else:
            sig_with_colon = sig.strip()
            if not sig_with_colon.endswith(":"):
                sig_with_colon += ":"
            new_func_block = f"{sig_with_colon}\n{formatted_body}"
        
        before = lines[:start_idx]
        after = lines[end_idx:]
        
        return "\n".join(before) + "\n" + new_func_block.strip() + "\n" + "\n".join(after)

    def _auto_fix_imports(self, code: str) -> str:
        """Add missing imports for common patterns the model forgets."""
        needed_imports = []
        
        # Check if typing elements are used but not imported
        if any(t in code for t in ["List[", "Dict[", "Tuple[", "Optional[", "Union["]):
            needed_imports.append("from typing import List, Dict, Tuple, Optional, Union")
            
        # Check if datetime is used but not imported
        if "datetime." in code or "datetime(" in code:
            needed_imports.append("from datetime import datetime")
            
        # Check if sqlite3 is used but not imported
        if "sqlite3." in code:
            needed_imports.append("import sqlite3")

        # Check if Flask / session is used but not imported
        if any(f in code for f in ["Flask(", "render_template(", "redirect(", "url_for(", "request.", "session["]):
            flask_funcs = [func for func in ["Flask", "render_template", "redirect", "url_for", "request", "session", "g", "jsonify"] if func in code]
            if flask_funcs:
                needed_imports.append(f"from flask import {', '.join(flask_funcs)}")

        # Check if project model classes are used but not imported (common in views/timeline)
        if re.search(r"\bUser\b", code) and "from src.models.user" not in code and "import User" not in code:
            needed_imports.append("from src.models.user import User")
        if re.search(r"\bTweet\b", code) and "from src.models.tweet" not in code and "import Tweet" not in code:
            needed_imports.append("from src.models.tweet import Tweet")
            
        # Only add imports that aren't already present in code
        new_imports = []
        for imp in needed_imports:
            if imp.startswith("import "):
                module = imp.split()[1]
                if not re.search(r"\bimport\s+" + re.escape(module) + r"\b", code):
                    new_imports.append(imp)
            elif imp.startswith("from "):
                module = imp.split()[1]
                if not re.search(r"\bfrom\s+" + re.escape(module) + r"\s+import\b", code) and not re.search(r"\bimport\s+" + re.escape(module) + r"\b", code):
                    new_imports.append(imp)
                    
        if new_imports:
            return "\n".join(new_imports) + "\n\n" + code
        return code

    def _deduplicate_code(self, existing_content: str, new_code: str) -> str:
        """Remove from new_code any imports or class defs that already exist in existing_content."""
        import ast
        try:
            existing_tree = ast.parse(existing_content)
            new_tree = ast.parse(new_code)
        except Exception:
            return new_code  # Can't parse, just return as-is
        
        # Collect existing imports, classes, functions
        existing_imports = set()
        existing_classes = set()
        existing_functions = set()
        for node in ast.walk(existing_tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    existing_imports.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    for alias in node.names:
                        existing_imports.add(f"{node.module}.{alias.name}")
            elif isinstance(node, ast.ClassDef):
                existing_classes.add(node.name)
            elif isinstance(node, ast.FunctionDef):
                existing_functions.add(node.name)
        
        lines = new_code.splitlines()
        skip_lines = set()
        
        for node in new_tree.body:
            should_skip = False
            if isinstance(node, ast.Import):
                if all(alias.name in existing_imports for alias in node.names):
                    should_skip = True
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    if all(f"{node.module}.{alias.name}" in existing_imports for alias in node.names):
                        should_skip = True
            elif isinstance(node, ast.ClassDef):
                if node.name in existing_classes:
                    should_skip = True
            elif isinstance(node, ast.FunctionDef):
                if node.name in existing_functions:
                    should_skip = True
                    
            if should_skip:
                end_line = getattr(node, "end_lineno", node.lineno) or node.lineno
                for r in range(node.lineno, end_line + 1):
                    skip_lines.add(r)
        
        filtered = []
        for i, line in enumerate(lines, 1):
            if i not in skip_lines:
                filtered.append(line)
        return "\n".join(filtered)

