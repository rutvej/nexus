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
            return match.group(1).strip()
        
        # Look for ``` ... ```
        match = re.search(r"```\s*(.*?)\s*```", cleaned, re.DOTALL)
        if match:
            return match.group(1).strip()
            
        return cleaned

    def execute_ticket(self, ticket: Ticket) -> bool:
        """
        Generates code for the ticket and writes it to the target file.
        Returns True if successful, False on failure.
        """
        # Determine prompt based on ticket type
        if ticket.type == TicketType.WRITE_FUNCTION:
            prompt = WRITE_FUNCTION_PROMPT.format(
                function_signature=ticket.function_signature,
                parameters=ticket.parameters,
                return_type=ticket.return_type,
                dependencies=ticket.dependencies,
                description=ticket.description,
                related_interfaces=ticket.related_interfaces
            )
        elif ticket.type == TicketType.WRITE_TEST:
            prompt = WRITE_TEST_PROMPT.format(
                function_signature=ticket.function_signature,
                description=ticket.description,
                return_type=ticket.return_type,
                target_file=ticket.target_file
            )
        elif ticket.type == TicketType.FIX_BUG:
            prompt = FIX_BUG_PROMPT.format(
                function_signature=ticket.function_signature,
                error_log=ticket.error_log,
                description=ticket.description
            )
        else:
            # For CREATE_FILE or others, use a simple generic prompt
            prompt = f"Create file {ticket.target_file}. Description: {ticket.description}. Output ONLY pure Python code."

        response = self.router.route_and_generate(prompt, ticket)
        if not response.success:
            ticket.error_log = response.error
            return False

        ticket.llm_output = response.text
        code = self.extract_code(response.text)
        
        # Write code to file
        full_path = os.path.join(self.workspace_dir, ticket.target_file)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        if ticket.type == TicketType.WRITE_FUNCTION:
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
                    f.write(ticket.dependencies + "\n\n")
                
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
        elif ticket.type == TicketType.FIX_BUG:
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
