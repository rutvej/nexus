import os
import tempfile
from unittest.mock import MagicMock
from nexus.tickets.models import Ticket, TicketType, TicketStatus
from nexus.agent.worker import Worker
from nexus.llm.base import LLMResponse

def test_worker_extract_code():
    w = Worker(MagicMock(), "")
    assert w.extract_code("```python\nprint(1)\n```") == "print(1)"
    assert w.extract_code("```\nprint(2)\n```") == "print(2)"
    assert w.extract_code("print(3)") == "print(3)"

def test_worker_execute_ticket():
    with tempfile.TemporaryDirectory() as tmpdir:
        router = MagicMock()
        router.route_and_generate.return_value = LLMResponse(
            text="```python\nreturn a + b\n```",
            model="mock",
            tokens_used=10,
            latency_ms=10.0,
            success=True
        )
        
        w = Worker(router, tmpdir)
        t = Ticket(
            id="T-1",
            type=TicketType.WRITE_FUNCTION,
            title="Write add",
            status=TicketStatus.BACKLOG,
            target_file="math_lib.py",
            function_signature="def add(a, b)",
            dependencies="import sys",
            description="Add two values"
        )
        
        ok = w.execute_ticket(t)
        assert ok is True
        
        # Verify file content
        file_path = os.path.join(tmpdir, "math_lib.py")
        assert os.path.exists(file_path)
        with open(file_path, "r") as f:
            content = f.read()
        assert "import sys" in content
        assert "def add(a, b):" in content
        assert "return a + b" in content

def test_worker_fix_bug():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create an existing file with helper function
        file_path = os.path.join(tmpdir, "math_lib.py")
        existing_content = (
            "import os\n\n"
            "def add(a, b):\n"
            "    return a - b  # Bug!\n\n"
            "def sub(a, b):\n"
            "    return a - b\n"
        )
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(existing_content)

        router = MagicMock()
        router.route_and_generate.return_value = LLMResponse(
            text="return a + b",
            model="mock",
            tokens_used=10,
            latency_ms=10.0,
            success=True
        )

        w = Worker(router, tmpdir)
        t = Ticket(
            id="T-2",
            type=TicketType.FIX_BUG,
            title="Fix add",
            status=TicketStatus.BACKLOG,
            target_file="math_lib.py",
            function_signature="def add(a, b)",
            description="Fix addition bug"
        )

        ok = w.execute_ticket(t)
        assert ok is True

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check that add was replaced with correct implementation
        assert "return a + b" in content
        # Check that sub and import was preserved (not overwritten)
        assert "def sub(a, b):" in content
        assert "import os" in content

