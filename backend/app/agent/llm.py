import os
import json
import logging
from typing import Dict, Any, Optional
import httpx
from backend.app.core.config import settings

logger = logging.getLogger("devsentinel.llm")

class LLMClient:
    def __init__(self):
        self.api_key = settings.LLM_API_KEY
        self.model = settings.LLM_MODEL
        self.provider = settings.LLM_PROVIDER

    def is_configured(self) -> bool:
        return bool(self.api_key and len(self.api_key.strip()) > 5)

    def generate_analysis(self, repo_context: str, issue_description: str) -> Dict[str, Any]:
        """
        Generates diagnostic defect summary, reproduction unit test, and targeted code fix.
        """
        if self.is_configured():
            try:
                return self._call_real_llm(repo_context, issue_description)
            except Exception as e:
                logger.warning(f"Real LLM request failed ({e}). Checking demo scenario fallback.")

        # Check if the task matches the demo scenario
        desc_lower = issue_description.lower()
        is_audio_demo = any(k in desc_lower for k in ["audio", "transcoder", "buffer", "sql injection", "cwe-120", "cwe-89", "shure"])

        if is_audio_demo:
            return self._demo_fixture_analysis(repo_context, issue_description)
        else:
            raise RuntimeError(
                "No active LLM provider configured and task does not match pre-packaged demo. "
                "Please configure LLM_API_KEY in .env to process arbitrary repositories."
            )

    def _call_real_llm(self, repo_context: str, issue_description: str) -> Dict[str, Any]:
        prompt = f"""You are DevSentinel, an AI Software Engineering Agent specializing in code remediation and verification.
Repository Context:
{repo_context}

Issue Requirements:
{issue_description}

Respond ONLY with a valid JSON object with the following exact keys:
- "defect_summary": Concise explanation of the defect and root cause.
- "supporting_evidence": Specific file lines or stack trace patterns confirming the issue.
- "reproduction_test": Python code for test_devsentinel_reproduce.py using pytest that fails before the fix.
- "target_file": Relative path of the primary file to modify.
- "fix_code": Full replacement content for the target file.
- "secondary_target_file": (Optional) relative path for secondary file, or null.
- "secondary_fix_code": (Optional) content for secondary file, or null.
- "estimated_security_score": Integer 0-100 estimating security post-fix.
- "estimated_maintainability_score": Integer 0-100 estimating maintainability post-fix.
- "remaining_uncertainty": Any edge cases or limitations requiring human reviewer attention.
"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are DevSentinel, an autonomous code repair agent. Always return clean, strict JSON."},
                {"role": "user", "content": prompt}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1
        }

        with httpx.Client(timeout=45.0) as client:
            resp = client.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            result = json.loads(content)
            result["provider_used"] = "openai"
            result["model_used"] = self.model
            result["execution_mode"] = "LIVE_LLM"
            
            # Approximate cost tracking
            usage = data.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            result["measured_cost_usd"] = round((prompt_tokens * 0.000005) + (completion_tokens * 0.000015), 4)
            return result

    def _demo_fixture_analysis(self, repo_context: str, issue_description: str) -> Dict[str, Any]:
        """
        Deterministic verification fixture for the pre-configured Shure Audio DSP demo scenario.
        Explicitly flagged as demo fixture.
        """
        return {
            "defect_summary": (
                "Identified CWE-120 (unchecked buffer bounds in RIFF/WAVE chunk header parser) "
                "and CWE-89 (unparameterized SQL query interpolation in track logging module)."
            ),
            "supporting_evidence": "audio_transcoder/parser.py line 10 chunk_size check omitted; db.py line 20 uses f-string SQL query.",
            "reproduction_test": '''import pytest
from audio_transcoder.parser import parse_audio_metadata
from audio_transcoder.db import log_track_event

def test_metadata_buffer_overflow_reproduction():
    # Oversized chunk header that must trigger ValueError when properly validated
    malformed_header = b"RIFF" + (99999).to_bytes(4, 'little') + b"WAVEfmt "
    with pytest.raises(ValueError, match="Chunk length exceeds buffer boundary"):
        parse_audio_metadata(malformed_header)

def test_sql_injection_prevention():
    # Injection payload that must be safely escaped via parameterized query
    malicious_title = "Shure Mic Test'; DROP TABLE track_logs; --"
    res = log_track_event(malicious_title, duration=120)
    assert res == True, "Failed safe parameterized insert"
''',
            "target_file": "audio_transcoder/parser.py",
            "fix_code": '''"""
Audio Metadata Parser & Transcoder Engine.
Remediated by DevSentinel: Enforces strict byte buffer bounds checks.
"""
def parse_audio_metadata(header_bytes: bytes) -> dict:
    if len(header_bytes) < 12:
        raise ValueError("Header too short")
    
    riff = header_bytes[0:4]
    chunk_size = int.from_bytes(header_bytes[4:8], "little")
    wave_format = header_bytes[8:12]

    # Boundary validation check (CWE-120 fix)
    if chunk_size > len(header_bytes):
        raise ValueError("Chunk length exceeds buffer boundary")

    return {
        "format": wave_format.decode("ascii", errors="replace"),
        "chunk_size": chunk_size,
        "valid": True
    }
''',
            "secondary_target_file": "audio_transcoder/db.py",
            "secondary_fix_code": '''"""
Track Logging Database Module.
Remediated by DevSentinel: Parameterized query prevents SQL injection (CWE-89).
"""
import sqlite3

def init_db(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS track_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            duration INTEGER
        )
    """)
    conn.commit()

def log_track_event(title: str, duration: int) -> bool:
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    cursor = conn.cursor()
    # Parameterized SQL query execution
    cursor.execute("INSERT INTO track_logs (title, duration) VALUES (?, ?)", (title, duration))
    conn.commit()
    conn.close()
    return True
''',
            "estimated_security_score": 96,
            "estimated_maintainability_score": 92,
            "remaining_uncertainty": "Assumes SQLite dialect. Verify production database driver compatibility if migrating to PostgreSQL.",
            "provider_used": "deterministic-demo-fixture",
            "model_used": "shure-audio-dsp-fixture",
            "execution_mode": "DEMO_FIXTURE",
            "measured_cost_usd": 0.0
        }
