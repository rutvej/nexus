import ast
import os
import sys
from typing import Tuple, Dict, Any
from nexus.sandbox.runner import SandboxRunner
from nexus import config

class Verifier:
    def __init__(self, workspace_dir: str = None):
        self.workspace_dir = workspace_dir or str(config.WORKSPACE_DIR)
        self.runner = SandboxRunner(self.workspace_dir)

    def verify_syntax(self, file_path: str) -> Tuple[bool, str]:
        """
        Runs ast.parse on the file to check for syntax correctness.
        """
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

    def verify_importable(self, file_path: str) -> Tuple[bool, str]:
        """
        Attempts to import the file as a module within the workspace to verify it has no runtime import errors.
        """
        if not file_path.endswith(".py"):
            return True, ""
            
        module_path = file_path.replace("\\", "/").replace(".py", "").replace("/", ".")
        cmd = [sys.executable, "-c", f"import sys; sys.path.insert(0, '{self.workspace_dir}'); import {module_path}"]
        code, out, err = self.runner.run_command(cmd, timeout=10)
        if code != 0:
            return False, f"ImportError or execution error during module import:\n{out}\n{err}"
        return True, ""

    def auto_format(self, file_path: str) -> bool:
        """
        Runs black on the file to auto-format it.
        """
        full_path = os.path.join(self.workspace_dir, file_path)
        cmd = [sys.executable, "-m", "black", full_path]
        code, out, err = self.runner.run_command(cmd, timeout=10)
        return code == 0

    def check_formatting(self, file_path: str) -> bool:
        """
        Runs black --check on the file.
        """
        full_path = os.path.join(self.workspace_dir, file_path)
        cmd = [sys.executable, "-m", "black", "--check", full_path]
        code, out, err = self.runner.run_command(cmd, timeout=10)
        return code == 0

    def run_tests(self, test_file: str) -> Tuple[bool, str]:
        """
        Runs pytest on the specified test file (or tests directory).
        Allows pytest code 0 (all passed), 5 (no tests collected),
        or 4 (path not found if test_file is "tests").
        """
        cmd = [sys.executable, "-m", "pytest", "-x", test_file]
        code, out, err = self.runner.run_command(cmd, timeout=config.TIMEOUT_TESTS)
        success = (code == 0 or code == 5 or (code == 4 and test_file == "tests"))
        output = out + "\n" + err
        return success, output
