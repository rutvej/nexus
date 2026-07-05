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
    assert w.extract_code("TKT-004\nprint(4)") == "print(4)"
    assert w.extract_code("# TKT-004: Write something\nprint(5)") == "print(5)"
    assert w.extract_code("```python\nTKT-003: dummy\ndef get_timeline():\n    return []\n```") == "def get_timeline():\n    return []"
    assert w.extract_code("```python\nprint(6)") == "print(6)"
    assert w.extract_code("```\nprint(7)") == "print(7)"

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

        # Now test that hallucinated ticket ID dependencies are stripped
        t_hallucinated = Ticket(
            id="T-2",
            type=TicketType.WRITE_FUNCTION,
            title="Write add 2",
            status=TicketStatus.BACKLOG,
            target_file="math_lib_2.py",
            function_signature="def add2(a, b)",
            dependencies="TKT-001",
            description="Add two values 2"
        )
        ok = w.execute_ticket(t_hallucinated)
        assert ok is True
        file_path_2 = os.path.join(tmpdir, "math_lib_2.py")
        with open(file_path_2, "r") as f:
            content_2 = f.read()
        assert "TKT-001" not in content_2
        assert "def add2(a, b):" in content_2

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


def test_worker_auto_fix_imports():
    w = Worker(MagicMock(), "")
    
    # List typing elements
    code_with_list = "def get_items() -> List[str]:\n    return []"
    fixed_list = w._auto_fix_imports(code_with_list)
    assert "from typing import List" in fixed_list
    
    # Datetime elements
    code_with_dt = "def get_now():\n    return datetime.now()"
    fixed_dt = w._auto_fix_imports(code_with_dt)
    assert "from datetime import datetime" in fixed_dt
    
    # Existing imports should not be duplicated
    code_with_existing = "import sqlite3\ndef query():\n    db = sqlite3.connect()"
    fixed_existing = w._auto_fix_imports(code_with_existing)
    # Check that import sqlite3 only appears once (no additions)
    assert fixed_existing.count("import sqlite3") == 1


def test_worker_deduplicate_code():
    w = Worker(MagicMock(), "")
    
    existing = "import sqlite3\n\nclass User:\n    pass"
    new_code = "import sqlite3\nfrom typing import List\nclass User:\n    pass\ndef get_users() -> List[User]:\n    return []"
    
    deduped = w._deduplicate_code(existing, new_code)
    # import sqlite3 and class User should be removed because they exist
    # from typing import List and def get_users should remain
    assert "import sqlite3" not in deduped
    assert "class User" not in deduped
    assert "from typing import List" in deduped
    assert "def get_users" in deduped


