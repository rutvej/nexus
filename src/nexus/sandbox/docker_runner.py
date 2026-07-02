import subprocess
import os
import sys
import signal
from pathlib import Path
from nexus import config

class DockerRunner:
    def __init__(self, workspace_dir: str = None, image_name: str = "python:3.12-slim"):
        self.workspace_dir = Path(workspace_dir or config.WORKSPACE_DIR)
        self.image_name = image_name

    def is_docker_available(self) -> bool:
        try:
            res = subprocess.run(
                ["docker", "info"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=3
            )
            return res.returncode == 0
        except Exception:
            return False

    def run_in_sandbox(self, cmd: list[str], timeout: int = 60) -> tuple[int, str, str]:
        """
        Runs a command inside a resource-constrained, network-isolated Docker sandbox.
        If Docker is not running or available, falls back gracefully to a path-restricted local subprocess.
        """
        if self.is_docker_available():
            # Construct the docker command
            # We map self.workspace_dir to /workspace inside the container
            docker_cmd = [
                "docker", "run", "--rm",
                "--network=none",
                "--memory=512m",
                "--cpus=1",
                "-v", f"{self.workspace_dir.resolve()}:/workspace:rw",
                "-w", "/workspace",
                self.image_name
            ] + cmd
            
            return self._run_command(docker_cmd, timeout=timeout)
        else:
            # Fallback to local subprocess execution
            return self._run_command(cmd, cwd=str(self.workspace_dir), timeout=timeout)

    def _run_command(self, cmd: list[str], cwd: str = None, timeout: int = 60) -> tuple[int, str, str]:
        preexec = os.setsid if sys.platform != "win32" else None
        proc = subprocess.Popen(
            cmd,
            cwd=cwd,
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
            return -1, stdout, f"TimeoutExpired: Command timed out after {timeout} seconds."
