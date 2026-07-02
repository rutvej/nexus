import os
import signal
import subprocess
import time
from typing import Tuple

class SandboxRunner:
    def __init__(self, workspace_dir: str):
        self.workspace_dir = workspace_dir

    def run_command(self, cmd: list[str], timeout: int = 60) -> Tuple[int, str, str]:
        """
        Runs a command inside the workspace directory in an isolated process group.
        If it times out, kills the entire process group.
        """
        preexec = None
        if os.name != 'nt':
            preexec = os.setsid
            
        proc = subprocess.Popen(
            cmd,
            cwd=self.workspace_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            preexec_fn=preexec
        )
        
        try:
            out, err = proc.communicate(timeout=timeout)
            return proc.returncode, out, err
        except subprocess.TimeoutExpired:
            if os.name != 'nt':
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                except Exception:
                    pass
            else:
                proc.kill()
            out, err = proc.communicate()
            return -1, out, f"TimeoutExpired: Process terminated after {timeout}s.\n" + err
