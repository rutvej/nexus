import json
import pytest
from unittest.mock import MagicMock
from nexus.tickets.models import Ticket, TicketType, TicketStatus
from nexus.tickets.queue import TicketQueue
from nexus.project.guide import ProjectGuide
from nexus.llm.base import LLMResponse
from nexus.llm.router import ModelRouter
from nexus.agent.manager import Manager

def test_parse_tickets_markdown_json():
    router = MagicMock(spec=ModelRouter)
    queue = MagicMock(spec=TicketQueue)
    guide = MagicMock(spec=ProjectGuide)
    manager = Manager(router, queue, guide)
    
    raw_response = """
    Some pre-text
    ```json
    [
        {"id": "T1", "type": "create_file", "title": "Create user", "target_file": "user.py", "description": "Create user file"}
    ]
    ```
    Some post-text
    """
    
    parsed = manager.parse_tickets(raw_response)
    assert len(parsed) == 1
    assert parsed[0]["id"] == "T1"
    assert parsed[0]["target_file"] == "user.py"

def test_decompose_feature_success():
    router = MagicMock(spec=ModelRouter)
    json_data = [
        {
            "id": "T1",
            "type": "create_file",
            "title": "Create main.py",
            "target_file": "main.py",
            "description": "Create main file",
            "depends_on": []
        }
    ]
    router.route_and_generate.return_value = LLMResponse(
        text=json.dumps(json_data),
        model="mock",
        tokens_used=10,
        latency_ms=1.0,
        success=True
    )
    
    queue = MagicMock(spec=TicketQueue)
    guide = MagicMock(spec=ProjectGuide)
    guide.read.return_value = "Mock Guide"
    
    manager = Manager(router, queue, guide)
    tickets = manager.decompose_feature("Create main.py file")
    
    assert len(tickets) == 1
    assert tickets[0].id == "T1"
    assert tickets[0].type == TicketType.CREATE_FILE
    
    queue.add_ticket.assert_called_once_with(tickets[0])
