from unittest.mock import MagicMock
from pathlib import Path
from nexus.tickets.models import Ticket, TicketType
from nexus.llm.base import LLMResponse
from nexus.llm.router import ModelRouter
from nexus.agent.worker import Worker

def test_extract_code_markdown():
    router = MagicMock(spec=ModelRouter)
    worker = Worker(router=router)
    
    text_with_markdown = "Here is your code:\n```python\ndef add(a, b):\n    return a + b\n```\nHope this helps!"
    code = worker.extract_code(text_with_markdown)
    assert code == "def add(a, b):\n    return a + b"

def test_execute_ticket_create_file(tmp_path):
    router = MagicMock(spec=ModelRouter)
    router.route_and_generate.return_value = LLMResponse(
        text="```python\n# new file content\n```",
        model="mock",
        tokens_used=10,
        latency_ms=1.0,
        success=True
    )
    
    worker = Worker(router=router, workspace_dir=str(tmp_path))
    ticket = Ticket(
        id="T1",
        type=TicketType.CREATE_FILE,
        title="Create test file",
        target_file="test.py",
        description="Creates test.py"
    )
    
    code = worker.execute_ticket(ticket)
    assert code == "# new file content"
    
    target = tmp_path / "test.py"
    assert target.exists()
    assert target.read_text().strip() == "# new file content"

def test_execute_ticket_write_function_append(tmp_path):
    router = MagicMock(spec=ModelRouter)
    router.route_and_generate.return_value = LLMResponse(
        text="def add(a, b):\n    return a + b",
        model="mock",
        tokens_used=10,
        latency_ms=1.0,
        success=True
    )
    
    worker = Worker(router=router, workspace_dir=str(tmp_path))
    
    # 1. Existing file
    target = tmp_path / "math.py"
    target.write_text("import os\n")
    
    ticket = Ticket(
        id="T2",
        type=TicketType.WRITE_FUNCTION,
        title="Write add function",
        target_file="math.py",
        function_signature="def add(a, b) -> int",
        description="Adds a and b"
    )
    
    code = worker.execute_ticket(ticket)
    assert "def add" in code
    
    file_content = target.read_text()
    assert "import os" in file_content
    assert "def add(a, b):" in file_content
