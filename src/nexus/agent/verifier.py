import ast
import os
import sys
import signal
import subprocess
from typing import Dict, Any, Tuple
from nexus import config

class Verifier:
    def __init__(self, workspace_dir: str = None):
        self.workspace_dir = workspace_dir or str(config.WORKSPACE_DIR)

    def _run_subprocess(self, cmd: list[str], timeout: int = 60) -> Tuple[int, str, str]:
        """Runs a command with unix process group isolation and returns (exit_code, stdout, stderr)."""
        # Under windows, os.setsid is not available, so we fallback gracefully
        preexec = os.setsid if sys.platform != "win32" else None
        
        proc = subprocess.Popen(
            cmd,
            cwd=self.workspace_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=preexec,
            text=True
        )
        
        try:
            stdout, stderr = proc.communicate(timeout=timeout)
            return proc.returncode, stdout, stderr
        except subprocess.TimeoutExpired:
            if sys.platform != "win32":
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                except Exception:
                    pass
            else:
                proc.kill()
            stdout, stderr = proc.communicate()
            return -1, stdout, f"Command timed out after {timeout} seconds."

    def verify_syntax(self, file_path: str) -> Tuple[bool, str]:
        """Parses AST of the file. Returns (True, '') if OK, else (False, error_msg)."""
        full_path = os.path.join(self.workspace_dir, file_path)
        if not os.path.exists(full_path):
            return False, f"File {file_path} does not exist."
        
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
            ast.parse(content)
            return True, ""
        except SyntaxError as e:
            return False, f"SyntaxError in {file_path} at line {e.lineno}, col {e.offset}: {e.msg}\nCode line: {e.text}"
        except Exception as e:
            return False, f"Error parsing {file_path}: {e}"

    def auto_format(self, file_path: str) -> bool:
        """Runs black formatter on the file. Returns True if format check passes/fixes, False on error."""
        full_path = os.path.join(self.workspace_dir, file_path)
        cmd = [sys.executable, "-m", "black", full_path]
        code, out, err = self._run_subprocess(cmd, timeout=10)
        return code == 0

    def check_formatting(self, file_path: str) -> bool:
        """Runs black --check on the file. Returns True if formatted, False if not."""
        full_path = os.path.join(self.workspace_dir, file_path)
        cmd = [sys.executable, "-m", "black", "--check", full_path]
        code, out, err = self._run_subprocess(cmd, timeout=10)
        return code == 0

    def run_tests(self, test_file: str) -> Tuple[bool, str]:
        """Runs pytest on the specified test file. Returns (True, stdout) if tests pass, else (False, stderr/stdout)."""
        # Run pytest with -x (exit on first failure) and --timeout=60
        # If pytest-timeout is not installed, timeout is handled by _run_subprocess anyway
        cmd = [sys.executable, "-m", "pytest", "-x", test_file]
        code, out, err = self._run_subprocess(cmd, timeout=config.TIMEOUT_TESTS)
        success = (code == 0)
        output = out + "\n" + err
        return success, output

    def run_static_analysis(self, file_path: str) -> Dict[str, Any]:
        """
        Optional Mypy and Bandit checks.
        Returns check statuses and gathered errors.
        """
        full_path = os.path.join(self.workspace_dir, file_path)
        results = {
            "mypy_passed": False,
            "bandit_passed": False,
            "errors": []
        }
        
        # 1. Run Mypy (ignore imports missing for simplicity if config doesn't require)
        mypy_cmd = [sys.executable, "-m", "mypy", "--ignore-missing-imports", full_path]
        code, out, err = self._run_subprocess(mypy_cmd, timeout=20)
        results["mypy_passed"] = (code == 0)
        if code != 0:
            results["errors"].append(f"Mypy failure:\n{out}\n{err}")

        # 2. Run Bandit
        bandit_cmd = [sys.executable, "-m", "bandit", "-r", full_path, "-f", "txt"]
        code, out, err = self._run_subprocess(bandit_cmd, timeout=20)
        # Bandit returncode 0 means no issues found
        results["bandit_passed"] = (code == 0)
        if code != 0:
            results["errors"].append(f"Bandit vulnerabilities found:\n{out}\n{err}")
            
        return results
