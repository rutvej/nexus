import subprocess
import time
from pathlib import Path
from nexus import config

class GitOperations:
    def __init__(self, repo_path: str = None):
        self.repo_path = Path(repo_path or config.WORKSPACE_DIR)
        # Configure safe directory to prevent dubious ownership issues inside Docker containers
        try:
            subprocess.run(
                ["git", "config", "--global", "--add", "safe.directory", "*"],
                capture_output=True
            )
        except Exception:
            pass

        # 1. Initialize git if not already present
        if not (self.repo_path / ".git").exists():
            subprocess.run(["git", "init"], cwd=self.repo_path, capture_output=True)

        # 2. Checkout branch
        timestamp = int(time.time())
        try:
            # Check if HEAD exists (contains commits)
            res = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.repo_path, capture_output=True)
            if res.returncode == 0:
                # Checkout new run branch
                subprocess.run(["git", "checkout", "-b", f"nexus/run-{timestamp}"], cwd=self.repo_path, capture_output=True)
            else:
                # Checkout nexus/main
                subprocess.run(["git", "checkout", "-b", "nexus/main"], cwd=self.repo_path, capture_output=True)
        except Exception:
            pass

    def _run_git(self, args: list[str]) -> str:
        res = subprocess.run(
            ["git"] + args,
            cwd=self.repo_path,
            capture_output=True,
            text=True
        )
        if res.returncode != 0:
            raise RuntimeError(f"Git command failed: git {' '.join(args)}\nStdout: {res.stdout}\nStderr: {res.stderr}")
        return res.stdout.strip()

    def get_current_head_hash(self) -> str:
        try:
            return self._run_git(["rev-parse", "HEAD"])
        except Exception:
            return ""

    def create_checkpoint_tag(self) -> str:
        timestamp = int(time.time())
        tag_name = f"checkpoint-{timestamp}"
        self._run_git(["tag", tag_name])
        return tag_name

    def commit_ticket_changes(self, ticket_id: str, ticket_title: str) -> str:
        # 1. Add all changed files under repo_path
        self._run_git(["add", "."])
        
        # Check if there are any staged changes to prevent empty commit errors
        res = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            cwd=self.repo_path
        )
        if res.returncode == 0:
            # No changes to commit, return current hash
            return self.get_current_head_hash()
            
        # 2. Commit with author info to bypass global config missing errors in tests/containers
        self._run_git([
            "commit",
            "-m", f"{ticket_id}: {ticket_title}",
            "--author=Gemini Flash <gemini@nexus.local>"
        ])
        return self.get_current_head_hash()

    def rollback_changes(self):
        # Discard unstaged changes
        self._run_git(["checkout", "."])
        # Clean untracked files
        self._run_git(["clean", "-fd"])
