import json
import re
from typing import List
from nexus.tickets.models import Ticket, TicketType, TicketStatus
from nexus.tickets.queue import TicketQueue
from nexus.tickets.templates import validate_ticket
from nexus.project.guide import ProjectGuide
from nexus.llm.router import ModelRouter

DECOMPOSE_PROMPT_TEMPLATE = """You are the Project Manager. Your job is to decompose the following user feature request into a sequence of small, self-contained development tickets.
Each ticket must be 1 Story Point (completability: <= 1 function or test, context <= 500 tokens).
Important: Always write a test ticket immediately after a write_function or create_file ticket to verify it.

PROJECT GUIDE:
{project_guide}

FEATURE REQUEST:
{feature_description}

You must output a JSON list of ticket objects. Each ticket object must have exactly these keys:
- "id": A unique identifier (e.g. "TWIT-001", "TWIT-002")
- "type": One of: "create_file", "write_function", "write_test", "run_tests", "fix_bug", "integration_test"
- "title": A short title (e.g. "Write function create_user")
- "target_file": The file path to modify or create (e.g. "src/models/user.py")
- "function_signature": The python function signature, if type is "write_function" (otherwise empty)
- "parameters": The parameters, if type is "write_function" (otherwise empty)
- "return_type": The return type description, if type is "write_function" (otherwise empty)
- "dependencies": The standard library modules to import/depend on
- "description": A 1-2 sentence description of what the function/file should do
- "depends_on": A list of IDs of other tickets this ticket depends on (e.g. ["TWIT-001"])

Output ONLY the raw JSON list, starting with [ and ending with ]. Do not wrap it in markdown. Do not write any explanations outside the JSON.
"""

class Manager:
    def __init__(self, router: ModelRouter, queue: TicketQueue, guide: ProjectGuide):
        self.router = router
        self.queue = queue
        self.guide = guide

    def parse_tickets(self, text: str) -> List[dict]:
        """Cleans markdown wrappers and parses JSON list of tickets."""
        cleaned = text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
        
        # In case there's leading/trailing non-json garbage
        start_idx = cleaned.find('[')
        end_idx = cleaned.rfind(']')
        if start_idx != -1 and end_idx != -1:
            cleaned = cleaned[start_idx:end_idx + 1]
            
        return json.loads(cleaned)

    def decompose_feature(self, feature_description: str) -> List[Ticket]:
        """
        Decomposes a high-level feature request into tickets using the LLM,
        validates them, and inserts them into the queue.
        """
        project_guide_content = self.guide.read()
        prompt = DECOMPOSE_PROMPT_TEMPLATE.format(
            project_guide=project_guide_content,
            feature_description=feature_description
        )
        
        # Use dummy/empty ticket for routing decomposition
        route_ticket = Ticket(id="DECOMP-000", type=TicketType.CREATE_FILE, title="Decompose Feature")
        response = self.router.route_and_generate(prompt, route_ticket, max_tokens=1000)
        
        if not response.success:
            raise RuntimeError(f"Manager decomposition failed: {response.error}")
            
        ticket_dicts = self.parse_tickets(response.text)
        created_tickets = []
        
        for d in ticket_dicts:
            t = Ticket(
                id=d.get("id", ""),
                type=TicketType(d.get("type", "create_file")),
                title=d.get("title", ""),
                status=TicketStatus.BACKLOG,
                target_file=d.get("target_file", ""),
                function_signature=d.get("function_signature", ""),
                parameters=d.get("parameters", ""),
                return_type=d.get("return_type", ""),
                dependencies=d.get("dependencies", ""),
                related_interfaces="",
                description=d.get("description", ""),
                depends_on=d.get("depends_on", []),
                epic="Epic"
            )
            
            valid, err = validate_ticket(t)
            if not valid:
                raise ValueError(f"Manager generated invalid ticket {t.id}: {err}")
                
            self.queue.add_ticket(t)
            created_tickets.append(t)
            
        return created_tickets
