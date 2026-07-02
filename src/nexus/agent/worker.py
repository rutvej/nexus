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
            with open(full_path, "a" if os.path.exists(full_path) else "w", encoding="utf-8") as f:
                # Add imports if creating new file
                if f.tell() == 0 and ticket.dependencies:
                    f.write(ticket.dependencies + "\n\n")
                # Write the function signature and the body
                f.write(f"\n{ticket.function_signature}:\n")
                # Indent the body lines if needed, or assume model returns indented body
                # Standard templates specify: "Write ONLY the function body"
                # So if it is only the body, we must indent it under the signature.
                # If the body is already indented/starts with spaces, append directly.
                # Let's do simple indentation block:
                indented_code = ""
                for line in code.splitlines():
                    if line.strip() and not line.startswith("    "):
                        indented_code += "    " + line + "\n"
                    else:
                        indented_code += line + "\n"
                f.write(indented_code + "\n")
        else:
            # Direct overwrite for CREATE_FILE, WRITE_TEST, FIX_BUG
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(code + "\n")
                
        return True
