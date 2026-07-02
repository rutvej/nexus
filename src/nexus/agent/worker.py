import os
import re
import ast
from nexus import config
from nexus.tickets.models import Ticket, TicketType
from nexus.tickets.templates import render_ticket_prompt
from nexus.llm.router import ModelRouter

class Worker:
    def __init__(self, router: ModelRouter, workspace_dir: str = None):
        self.router = router
        self.workspace_dir = Path(workspace_dir or config.WORKSPACE_DIR)

    def extract_code(self, text: str) -> str:
        """Extracts Python code from Markdown code blocks if present."""
        # Check for ```python ... ```
        match = re.search(r"```python\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        # Check for generic ``` ... ```
        match = re.search(r"```\s*(.*?)\s*```", text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return text.strip()

    def _replace_function_in_code(self, source: str, func_name: str, new_body: str) -> str:
        """Parses AST and replaces the function func_name's body/definition, or appends it."""
        try:
            tree = ast.parse(source)
            start_line, end_line = -1, -1
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == func_name:
                    start_line = node.lineno
                    end_line = getattr(node, "end_lineno", -1)
                    break
            
            if start_line != -1 and end_line != -1:
                lines = source.splitlines()
                # AST line numbers are 1-indexed. Replace the slice
                # We replace from start_line - 1 to end_line
                before = lines[:start_line - 1]
                after = lines[end_line:]
                middle = new_body.splitlines()
                return "\n".join(before + middle + after) + "\n"
        except Exception:
            pass
        
        # Fallback to append if parsing fails or function not found
        return source.rstrip() + "\n\n" + new_body + "\n"

    def execute_ticket(self, ticket: Ticket) -> str:
        """
        Renders the prompt, gets completion from router, parses code,
        and applies changes to the target file.
        Returns the parsed code.
        """
        prompt = render_ticket_prompt(ticket)
        response = self.router.route_and_generate(prompt, ticket)
        
        if not response.success:
            raise RuntimeError(f"LLM generation failed: {response.error}")
            
        ticket.llm_output = response.text
        code = self.extract_code(response.text)
        
        if not ticket.target_file:
            return code
            
        full_path = self.workspace_dir / ticket.target_file
        # Ensure directory exists
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        if ticket.type == TicketType.WRITE_FUNCTION:
            # Extract function name from signature
            # e.g., "def create_user(username: str) -> dict" -> "create_user"
            match = re.match(r"def\s+(\w+)", ticket.function_signature)
            func_name = match.group(1) if match else None
            
            if full_path.exists() and func_name:
                with open(full_path, "r", encoding="utf-8") as f:
                    existing_content = f.read()
                new_content = self._replace_function_in_code(existing_content, func_name, code)
            else:
                new_content = code + "\n"
                
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(new_content)
                
        else:
            # Overwrite or create file for other types (CREATE_FILE, WRITE_TEST, FIX_BUG)
            # For FIX_BUG, the worker usually rewrites the whole file or provides the updated file.
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(code + "\n")
                
        return code
from pathlib import Path
