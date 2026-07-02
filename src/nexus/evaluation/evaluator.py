import py_compile
import os
import subprocess
from typing import List, Dict, Any
from nexus.models.router import ModelRouter
from nexus.models.backends.ollama import DEFAULT_OLLAMA_URL, CUSTOM_OLLAMA_URL

class EvaluationEngine:
    def __init__(self, db_path: str = "/home/rutvej/nexus_eval/nexus_eval.db"):
        self.db_path = db_path

    def evaluate_code(self, file_path: str) -> Dict[str, Any]:
        """Run syntax and basic compile checks on a Python file."""
        result = {
            "syntax_correct": False,
            "compile_success": False,
            "error": None
        }
        
        if not os.path.exists(file_path):
            result["error"] = f"File not found: {file_path}"
            return result
            
        if not file_path.endswith(".py"):
            # Non-python files are assumed correct if they exist
            result["syntax_correct"] = True
            result["compile_success"] = True
            return result
            
        try:
            py_compile.compile(file_path, doraise=True)
            result["syntax_correct"] = True
            result["compile_success"] = True
        except py_compile.PyCompileError as e:
            result["error"] = str(e)
            
        return result

    def run_project_tests(self) -> Dict[str, Any]:
        """Run the project's test suite if pytest is configured."""
        result = {
            "test_success": False,
            "output": "",
            "error": None
        }
        
        # Check if pytest is available and there are tests
        if os.path.exists("tests") or os.path.exists("test_app.py"):
            try:
                res = subprocess.run(
                    ["pytest", "-v"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=30
                )
                result["test_success"] = res.returncode == 0
                result["output"] = res.stdout
                if res.returncode != 0:
                    result["error"] = res.stderr
            except FileNotFoundError:
                # pytest not installed, try running python -m unittest
                try:
                    res = subprocess.run(
                        ["python3", "-m", "unittest", "discover"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        timeout=30
                    )
                    result["test_success"] = res.returncode == 0
                    result["output"] = res.stdout
                    if res.returncode != 0:
                        result["error"] = res.stderr
                except Exception as e:
                    result["error"] = f"Could not run tests: {e}"
        else:
            # No tests configured, default to success
            result["test_success"] = True
            
        return result

    def process_feedback(self, model_name: str, task_type: str, success: bool, latency_ms: float, tokens_gen: int):
        """Update model scores in the SQLite database (EMA update)."""
        # We import the update_model_score function here to avoid circular imports
        from nexus.benchmark.database import update_model_score
        try:
            update_model_score(model_name, task_type, success, latency_ms, tokens_gen)
        except Exception as e:
            print(f"Warning: Failed to update model score in database: {e}")
