import tempfile
import os
import subprocess
from unittest.mock import MagicMock
from nexus.loop.engine import Engine
from nexus.llm.base import LLMResponse

def test_engine_successful_loop():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Init git repo in tmpdir
        subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=tmpdir)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmpdir)
        
        # Initial commit so HEAD exists
        with open(os.path.join(tmpdir, "README.md"), "w") as f:
            f.write("# Temp")
        subprocess.run(["git", "add", "."], cwd=tmpdir)
        subprocess.run(["git", "commit", "-m", "initial", "--author=Test <test@example.com>"], cwd=tmpdir)

        # Mock LLM response
        router = MagicMock()
        # Mock decomposition returning 1 ticket
        json_output = """
        [
            {
                "id": "TKT-01",
                "type": "create_file",
                "title": "Create helper",
                "target_file": "helper.py",
                "description": "Create helper Python file",
                "depends_on": []
            }
        ]
        """
        # First call is decomposition, second is worker execution
        router.route_and_generate.side_effect = [
            LLMResponse(text=json_output, model="mock", tokens_used=50, latency_ms=10.0, success=True),
            LLMResponse(text="def add(a, b):\n    return a + b\n", model="mock", tokens_used=10, latency_ms=10.0, success=True)
        ]

        engine = Engine(router, workspace_dir=tmpdir, db_path=":memory:")
        
        # Mock run_tests to pass
        engine.verifier.run_tests = MagicMock(return_value=(True, "Tests passed"))
        
        summary = engine.run("Create a helper module")
        assert "Completed 1/1" in summary
        
        # Confirm file got created and committed
        helper_path = os.path.join(tmpdir, "helper.py")
        assert os.path.exists(helper_path)
