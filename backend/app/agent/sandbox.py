import os
import signal
import subprocess
from typing import Dict, Any

class SandboxExecutionResult:
    def __init__(self, command: str, returncode: int, stdout: str, stderr: str, timed_out: bool = False):
        self.command = command
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.timed_out = timed_out

    @property
    def output(self) -> str:
        return (self.stdout or "") + ("\n" + self.stderr if self.stderr else "")

class LocalSandbox:
    """
    Isolated command execution environment with cross-platform process tree termination
    and stdout/stderr capture.
    """
    def __init__(self, working_dir: str, timeout: int = 30):
        self.working_dir = working_dir
        self.timeout = timeout

    def run_command(self, command: str, env: Dict[str, str] = None) -> SandboxExecutionResult:
        full_env = os.environ.copy()
        if env:
            full_env.update(env)

        is_posix = os.name == "posix"
        process = subprocess.Popen(
            command,
            shell=True,
            text=True,
            cwd=self.working_dir,
            env=full_env,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=is_posix
        )

        try:
            stdout, stderr = process.communicate(timeout=self.timeout)
            return SandboxExecutionResult(command, process.returncode, stdout, stderr, timed_out=False)
        except subprocess.TimeoutExpired:
            # Cross-platform safe process-tree termination
            if is_posix:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except Exception:
                    process.kill()
            else:
                # Windows safe process tree cleanup using taskkill
                try:
                    subprocess.run(f"taskkill /F /T /PID {process.pid}", shell=True, capture_output=True)
                except Exception:
                    process.kill()

            stdout, stderr = process.communicate()
            return SandboxExecutionResult(
                command=command,
                returncode=-1,
                stdout=stdout or "",
                stderr=(stderr or "") + f"\n[TIMEOUT] Command timed out after {self.timeout}s",
                timed_out=True
            )
