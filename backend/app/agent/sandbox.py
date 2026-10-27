import os
import signal
import subprocess
from typing import Dict, Any, Optional

SENSITIVE_ENV_PREFIXES = ("OPENAI", "GEMINI", "ANTHROPIC", "AWS_", "GITHUB_", "SECRET", "PASSWORD", "KEY", "TOKEN")

class SandboxExecutionResult:
    def __init__(self, command: str, returncode: int, stdout: str, stderr: str, timed_out: bool = False):
        self.command = command
        self.returncode = returncode
        self.stdout = stdout or ""
        self.stderr = stderr or ""
        self.timed_out = timed_out

    @property
    def is_success(self) -> bool:
        return self.returncode == 0 and not self.timed_out

    @property
    def output(self) -> str:
        parts = []
        if self.stdout:
            parts.append(self.stdout)
        if self.stderr:
            parts.append(self.stderr)
        return "\n".join(parts)

class ControlledExecutionRunner:
    """
    Controlled local execution runner with environment variable sanitization,
    strict timeout boundaries, and cross-platform process-tree termination.
    NOTE: For full untrusted multi-tenant isolation, containerized / Docker execution
    must be enabled in production deployments.
    """
    def __init__(self, working_dir: str, timeout: int = 30):
        self.working_dir = working_dir
        self.timeout = timeout

    def _sanitize_env(self, custom_env: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        # Filter out host API keys and sensitive tokens
        sanitized = {
            k: v for k, v in os.environ.items()
            if not any(k.upper().startswith(prefix) for prefix in SENSITIVE_ENV_PREFIXES)
        }
        # Keep standard PATH and point PYTHONPATH to local workspace directory
        sanitized["PYTHONUNBUFFERED"] = "1"
        sanitized["PYTHONDONTWRITEBYTECODE"] = "1"
        sanitized["PYTHONPATH"] = str(self.working_dir)

        if custom_env:
            sanitized.update(custom_env)
        return sanitized

    def run_command(self, command: str, env: Optional[Dict[str, str]] = None) -> SandboxExecutionResult:
        execution_env = self._sanitize_env(env)
        is_posix = os.name == "posix"

        try:
            process = subprocess.Popen(
                command,
                shell=True,
                text=True,
                cwd=self.working_dir,
                env=execution_env,
                encoding="utf-8",
                errors="replace",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=is_posix
            )
        except Exception as e:
            return SandboxExecutionResult(
                command=command,
                returncode=-1,
                stdout="",
                stderr=f"Process launch failure: {e}",
                timed_out=False
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
                try:
                    subprocess.run(f"taskkill /F /T /PID {process.pid}", shell=True, capture_output=True)
                except Exception:
                    process.kill()

            stdout, stderr = process.communicate()
            return SandboxExecutionResult(
                command=command,
                returncode=-1,
                stdout=stdout or "",
                stderr=(stderr or "") + f"\n[TIMEOUT] Command exceeded {self.timeout}s execution limit",
                timed_out=True
            )

# Backward compatibility alias
LocalSandbox = ControlledExecutionRunner
