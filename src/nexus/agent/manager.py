import json
from typing import List
from nexus.tickets.models import Ticket, TicketType, TicketStatus
from nexus.tickets.queue import TicketQueue
from nexus.tickets.templates import validate_ticket
from nexus.project.guide import ProjectGuide
from nexus.llm.router import ModelRouter

DECOMPOSE_PROMPT_TEMPLATE = """You are the Project Manager. Your job is to decompose the following user feature request into a sequence of small, self-contained development tickets.
Each ticket must be 1 Story Point (completability: <= 1 function or test, context <= 500 tokens).

PROJECT GUIDE:
{project_guide}

FEATURE REQUEST:
{feature_description}

You must output a JSON list of ticket objects. Each ticket object must have exactly these keys:
- "id": A unique identifier (e.g. "TKT-001", "TKT-002")
- "type": One of: "create_file", "write_function"
- "title": A short title (e.g. "Write function create_user")
- "target_file": The file path to modify or create (e.g. "src/models/user.py")
- "function_signature": The python function signature (e.g. "def create_user(username: str) -> None:")
- "parameters": The parameters (e.g. "username: str")
- "return_type": The return type description (e.g. "None")
- "dependencies": The Python module import statements (e.g. "import math" or "from src.models.user import User")
- "description": A 1-2 sentence description of what the function/file should do
- "depends_on": A list of IDs of other tickets this ticket depends on (e.g. ["TKT-001"])

EXAMPLE FEATURE REQUEST:
Create a circle area calculator: 1. Calculate area. 2. CLI wrapper.

EXAMPLE OUTPUT:
[
  {{
    "id": "TKT-001",
    "type": "create_file",
    "title": "Write function calculate_area",
    "target_file": "src/area.py",
    "function_signature": "def calculate_area(radius: float) -> float:",
    "parameters": "radius: float",
    "return_type": "float",
    "dependencies": "import math",
    "description": "Calculate the area of a circle given its radius using math.pi.",
    "depends_on": []
  }},
  {{
    "id": "TKT-002",
    "type": "create_file",
    "title": "Write function run_cli",
    "target_file": "src/cli.py",
    "function_signature": "def run_cli() -> None:",
    "parameters": "",
    "return_type": "None",
    "dependencies": "import sys, from src.area import calculate_area",
    "description": "Read radius from args, call calculate_area, and print result.",
    "depends_on": ["TKT-001"]
  }}
]

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
        
        # Use dummy ticket for routing decomposition
        route_ticket = Ticket(id="DECOMP-000", type=TicketType.CREATE_FILE, title="Decompose Feature", status=TicketStatus.IN_PROGRESS, target_file="DECOMP")
        response = self.router.route_and_generate(prompt, route_ticket, max_tokens=1000)
        
        if not response.success:
            raise RuntimeError(f"Manager decomposition failed: {response.error}")
            
        def _to_str(val) -> str:
            if isinstance(val, list):
                return ", ".join(str(item) for item in val)
            return str(val) if val is not None else ""

        ticket_dicts = self.parse_tickets(response.text)
        created_tickets = []
        
        for d in ticket_dicts:
            t = Ticket(
                id=_to_str(d.get("id", "")),
                type=TicketType(d.get("type", "create_file")),
                title=_to_str(d.get("title", "")),
                status=TicketStatus.BACKLOG,
                target_file=_to_str(d.get("target_file", "")),
                function_signature=_to_str(d.get("function_signature", "")),
                parameters=_to_str(d.get("parameters", "")),
                return_type=_to_str(d.get("return_type", "")),
                dependencies=_to_str(d.get("dependencies", "")),
                related_interfaces=self.guide.get_section("Interface Registry")[:500],
                description=_to_str(d.get("description", "")),
                depends_on=d.get("depends_on", []),
                epic="Epic"
            )
            
            valid, err = validate_ticket(t)
            if not valid:
                raise ValueError(f"Manager generated invalid ticket {t.id}: {err}")
                
            self.queue.add_ticket(t)
            created_tickets.append(t)
            
        return created_tickets
