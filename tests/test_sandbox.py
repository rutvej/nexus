import tempfile
import sys
import time
from nexus.sandbox.runner import SandboxRunner

def test_sandbox_runner_success():
    with tempfile.TemporaryDirectory() as tmpdir:
        runner = SandboxRunner(tmpdir)
        code, out, err = runner.run_command([sys.executable, "-c", "print('hello')"])
        assert code == 0
        assert "hello" in out

def test_sandbox_runner_timeout():
    with tempfile.TemporaryDirectory() as tmpdir:
        runner = SandboxRunner(tmpdir)
        # Sleep for 10 seconds, but set timeout to 1 second
        code, out, err = runner.run_command([sys.executable, "-c", "import time; time.sleep(10)"], timeout=1)
        assert code == -1
        assert "TimeoutExpired" in err
