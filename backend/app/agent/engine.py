import os
import sys
import shutil
import time
import difflib
from pathlib import Path
from typing import Dict, Any, List
from sqlalchemy.orm import Session

from backend.app.models.job import ReviewJob
from backend.app.agent.sandbox import ControlledExecutionRunner
from backend.app.agent.llm import LLMClient

class DevSentinelAgent:
    def __init__(self, db: Session, job: ReviewJob):
        self.db = db
        self.job = job
        self.llm = LLMClient()
        self.trajectory: List[Dict[str, Any]] = []

    def _record_step(self, stage: str, thought: str, action: str, observation: str):
        step = {
            "step_index": len(self.trajectory) + 1,
            "stage": stage,
            "thought": thought,
            "action": action,
            "observation": observation,
            "timestamp": time.time()
        }
        self.trajectory.append(step)
        self.job.trajectory = list(self.trajectory)
        self.db.commit()

    def _validate_safe_path(self, base_dir: Path, rel_path: str) -> Path:
        """
        Guarantees candidate target file resides strictly within the workspace boundary,
        rejecting directory traversal attacks (e.g., ../../../etc/passwd).
        """
        canonical_target = (base_dir / rel_path).resolve()
        canonical_base = base_dir.resolve()
        try:
            canonical_target.relative_to(canonical_base)
        except ValueError:
            raise ValueError(f"Security violation: Path traversal detected outside workspace: '{rel_path}'")
        return canonical_target

    def run(self):
        start_time = time.time()
        orig_repo_dir = Path(self.job.repo_path).resolve()

        if not orig_repo_dir.exists():
            self.job.status = "FAILED"
            self.job.verification_status = "FAILED"
            self._record_step("ERROR", "Target repository path does not exist", "validate_path()", f"Path not found: {orig_repo_dir}")
            self.db.commit()
            return

        # P0 FIX: Protect original repository!
        # Create an isolated candidate workspace copy. Original repo remains 100% untouched until human approval.
        staging_root = orig_repo_dir.parent / "_candidate_workspaces"
        staging_root.mkdir(parents=True, exist_ok=True)
        workspace_dir = staging_root / f"candidate_{self.job.id[:8]}"

        if workspace_dir.exists():
            shutil.rmtree(workspace_dir, ignore_errors=True)
        shutil.copytree(orig_repo_dir, workspace_dir)
        self.job.candidate_workspace_path = str(workspace_dir)

        sandbox = ControlledExecutionRunner(working_dir=str(workspace_dir), timeout=30)

        try:
            # === STAGE 1: Reconnaissance ===
            self.job.status = "ANALYZING"
            self.db.commit()

            python_files = [
                str(p.relative_to(workspace_dir))
                for p in workspace_dir.rglob("*.py")
                if not p.name.startswith(".") and "tests" not in p.parts and "venv" not in str(p)
            ]
            recon_obs = f"Discovered candidate Python modules: {', '.join(python_files[:8]) if python_files else 'None'}"
            self._record_step(
                stage="RECONNAISSANCE",
                thought="Scanning candidate workspace for modules and existing test fixtures.",
                action="scan_workspace(pattern='*.py')",
                observation=recon_obs
            )

            # Read source context
            context_snippets = []
            for rel_file in python_files[:4]:
                file_path = workspace_dir / rel_file
                if file_path.is_file():
                    context_snippets.append(f"--- File: {rel_file} ---\n{file_path.read_text(encoding='utf-8', errors='replace')[:2000]}")
            repo_context = "\n\n".join(context_snippets)

            # === STAGE 2: Defect Analysis & Reproduction Test Synthesis ===
            self.job.status = "TESTING"
            self.db.commit()

            llm_result = self.llm.generate_analysis(repo_context, self.job.issue_description)
            self.job.provider_used = llm_result.get("provider_used", "auto")
            self.job.execution_mode = llm_result.get("execution_mode", "LIVE_LLM")
            self.job.remaining_uncertainty = llm_result.get("remaining_uncertainty", "")

            # Path Traversal Check for reproduction test file
            reproduction_code = llm_result.get("reproduction_test", "")
            test_file_path = self._validate_safe_path(workspace_dir, "tests/test_devsentinel_reproduce.py")
            test_file_path.parent.mkdir(parents=True, exist_ok=True)
            test_file_path.write_text(reproduction_code, encoding="utf-8")

            self._record_step(
                stage="TEST_SYNTHESIS",
                thought=llm_result.get("defect_summary", "Synthesized reproduction test asserting the reported defect."),
                action="write_reproduction_test('tests/test_devsentinel_reproduce.py')",
                observation=f"Written reproduction test file ({len(reproduction_code.splitlines())} lines) in isolated candidate workspace."
            )

            # === STAGE 3: Baseline Test Execution in Sandbox ===
            # A valid reproduction test MUST fail before any fix is applied!
            py_bin = sys.executable or "python"
            baseline_res = sandbox.run_command(f'"{py_bin}" -m pytest -q tests/test_devsentinel_reproduce.py')
            self.job.baseline_exit_code = baseline_res.returncode
            self.job.baseline_test_output = baseline_res.output

            baseline_failed_as_expected = baseline_res.returncode != 0
            self._record_step(
                stage="BASELINE_VERIFICATION",
                thought=(
                    "Executed reproduction test to confirm defect manifestation. "
                    + ("Defect successfully manifested (non-zero exit code as expected)." if baseline_failed_as_expected
                       else "Warning: Reproduction test passed unexpectedly before fix was applied.")
                ),
                action="pytest -q tests/test_devsentinel_reproduce.py",
                observation=baseline_res.output.strip() or f"Process exit code: {baseline_res.returncode}"
            )

            # === STAGE 4: Surgical Code Remediation in Candidate Workspace ===
            self.job.status = "PATCHING"
            self.db.commit()

            diff_parts = []

            # Primary file patch with path traversal containment
            target_rel = llm_result.get("target_file", "")
            if not target_rel:
                raise ValueError("LLM result did not provide a target_file")
            
            target_path = self._validate_safe_path(workspace_dir, target_rel)
            original_file_in_repo = orig_repo_dir / target_rel
            original_text = original_file_in_repo.read_text(encoding="utf-8", errors="replace") if original_file_in_repo.exists() else ""

            new_text = llm_result.get("fix_code", original_text)
            target_path.write_text(new_text, encoding="utf-8")

            primary_diff = "".join(difflib.unified_diff(
                original_text.splitlines(keepends=True),
                new_text.splitlines(keepends=True),
                fromfile=f"a/{target_rel}",
                tofile=f"b/{target_rel}"
            ))
            if primary_diff:
                diff_parts.append(primary_diff)

            # Secondary file patch (if any)
            secondary_rel = llm_result.get("secondary_target_file")
            secondary_fix = llm_result.get("secondary_fix_code")
            if secondary_rel and secondary_fix:
                sec_path = self._validate_safe_path(workspace_dir, secondary_rel)
                sec_orig_in_repo = orig_repo_dir / secondary_rel
                sec_orig = sec_orig_in_repo.read_text(encoding="utf-8", errors="replace") if sec_orig_in_repo.exists() else ""
                sec_path.write_text(secondary_fix, encoding="utf-8")
                
                sec_diff = "".join(difflib.unified_diff(
                    sec_orig.splitlines(keepends=True),
                    secondary_fix.splitlines(keepends=True),
                    fromfile=f"a/{secondary_rel}",
                    tofile=f"b/{secondary_rel}"
                ))
                if sec_diff:
                    diff_parts.append(sec_diff)

            full_diff = "\n\n".join(diff_parts)
            self.job.patch_diff = full_diff

            self._record_step(
                stage="CODE_REMEDIATION",
                thought="Applied surgical candidate changes within isolated staging workspace. Original branch untouched.",
                action=f"apply_candidate_patch({target_rel})",
                observation=f"Generated unified patch ({len(full_diff.splitlines())} lines diff)."
            )

            # === STAGE 5: Regression & Verification Testing ===
            # Run pytest in candidate workspace. MUST return 0 for success!
            verification_res = sandbox.run_command(f'"{py_bin}" -m pytest -q')
            self.job.verification_exit_code = verification_res.returncode
            self.job.test_output = verification_res.output

            if verification_res.returncode == 0:
                self.job.verification_status = "PASSED"
                self.job.status = "AWAITING_REVIEW"
                test_status_summary = f"PASSED (exit code 0)\n{verification_res.output.strip()}"
            else:
                self.job.verification_status = "FAILED"
                self.job.status = "VERIFICATION_FAILED"
                test_status_summary = f"FAILED (exit code {verification_res.returncode})\n{verification_res.output.strip()}"

            self._record_step(
                stage="REGRESSION_VERIFICATION",
                thought="Re-executed test suite in sandbox. Verification status strictly determined by process return code.",
                action="pytest -q",
                observation=test_status_summary
            )

            # === STAGE 6: Telemetry and Review State ===
            self.job.security_score = llm_result.get("estimated_security_score", 90)
            self.job.maintainability_score = llm_result.get("estimated_maintainability_score", 85)
            self.job.cost_usd = llm_result.get("measured_cost_usd", 0.0)
            self.job.execution_time_seconds = round(time.time() - start_time, 2)
            self.db.commit()

        except Exception as e:
            self.job.status = "FAILED"
            self.job.verification_status = "FAILED"
            self._record_step("ERROR", f"Agent execution aborted: {e}", "agent.abort()", str(e))
            self.db.commit()
