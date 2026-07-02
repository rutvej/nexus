import tempfile
from unittest.mock import MagicMock
from nexus.tickets.queue import TicketQueue
from nexus.project.guide import ProjectGuide
from nexus.agent.manager import Manager
from nexus.llm.base import LLMResponse
from nexus.tickets.models import TicketType

def test_manager_decomposition():
    with tempfile.TemporaryDirectory() as tmpdir:
        router = MagicMock()
        # Mock LLM returning valid JSON tickets
        json_output = """
        [
            {
                "id": "TKT-01",
                "type": "create_file",
                "title": "Create model",
                "target_file": "src/model.py",
                "dependencies": "sqlite3",
                "description": "Initialize database connection",
                "depends_on": []
            }
        ]
        """
        router.route_and_generate.return_value = LLMResponse(
            text=json_output,
            model="mock",
            tokens_used=50,
            latency_ms=10.0,
            success=True
        )
        
        queue = TicketQueue(":memory:")
        guide = ProjectGuide(tmpdir)
        
        manager = Manager(router, queue, guide)
        tickets = manager.decompose_feature("Build simple database module")
        
        assert len(tickets) == 1
        assert tickets[0].id == "TKT-01"
        assert tickets[0].type == TicketType.CREATE_FILE
        assert tickets[0].target_file == "src/model.py"
        
        # Verify it was added to queue
        queued = queue.list_all()
        assert len(queued) == 1
        assert queued[0].id == "TKT-01"
