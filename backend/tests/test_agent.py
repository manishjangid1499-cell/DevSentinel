import pytest
from pathlib import Path
from backend.app.core.database import SessionLocal, Base, engine
from backend.app.models.job import ReviewJob
from backend.app.agent.engine import DevSentinelAgent
from backend.app.agent.llm import LLMClient

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def test_devsentinel_agent_preserves_original_workspace_before_approval(tmp_path):
    sample_dir = tmp_path / "audio_project"
    sample_dir.mkdir(parents=True)
    pkg_dir = sample_dir / "audio_transcoder"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("", encoding="utf-8")
    
    orig_parser_code = '''def parse_audio_metadata(header_bytes: bytes) -> dict:
    riff = header_bytes[0:4]
    chunk_size = int.from_bytes(header_bytes[4:8], "little")
    return {"format": "WAVE", "chunk_size": chunk_size}
'''
    (pkg_dir / "parser.py").write_text(orig_parser_code, encoding="utf-8")

    orig_db_code = '''import sqlite3

def init_db(conn):
    conn.execute("CREATE TABLE IF NOT EXISTS track_logs (id INTEGER PRIMARY KEY, title TEXT, duration INTEGER)")
    conn.commit()

def log_track_event(title: str, duration: int) -> bool:
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    conn.execute(f"INSERT INTO track_logs (title, duration) VALUES ('{title}', {duration})")
    conn.commit()
    conn.close()
    return True
'''
    (pkg_dir / "db.py").write_text(orig_db_code, encoding="utf-8")

    db = SessionLocal()
    job = ReviewJob(
        repo_name="Shure Audio Transcoder",
        repo_path=str(sample_dir),
        issue_description="CWE-120 Buffer Overrun in parser and CWE-89 SQL Injection. Synthesize reproduction test and apply bounds check.",
        status="PENDING"
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    agent = DevSentinelAgent(db, job)
    agent.run()

    db.refresh(job)
    print("\n--- JOB VERIFICATION EXIT CODE ---", job.verification_exit_code)
    print("--- JOB TEST OUTPUT ---\n", job.test_output)

    # 1. Verification status must be PASSED
    assert job.status == "AWAITING_REVIEW"
    assert job.verification_status == "PASSED"
    assert job.verification_exit_code == 0
    assert job.patch_diff != ""

    # 2. Crucial P0 assertion: Original repository files MUST NOT be modified yet!
    assert (pkg_dir / "parser.py").read_text(encoding="utf-8") == orig_parser_code
    assert (pkg_dir / "db.py").read_text(encoding="utf-8") == orig_db_code
    
    # 3. Candidate workspace exists and holds candidate files
    assert job.candidate_workspace_path is not None
    assert Path(job.candidate_workspace_path).exists()
    db.close()

def test_path_traversal_prevention(tmp_path):
    db = SessionLocal()
    agent = DevSentinelAgent(db, ReviewJob(repo_name="T", repo_path=str(tmp_path), issue_description="test"))
    
    # Valid relative path inside workspace
    safe_path = agent._validate_safe_path(tmp_path, "sub/file.py")
    assert safe_path.is_relative_to(tmp_path.resolve())

    # Traversal attempts outside workspace MUST raise ValueError
    with pytest.raises(ValueError, match="Path traversal detected"):
        agent._validate_safe_path(tmp_path, "../../etc/passwd")

    with pytest.raises(ValueError, match="Path traversal detected"):
        agent._validate_safe_path(tmp_path, "../outside.txt")
    db.close()

def test_arbitrary_task_without_llm_fails_gracefully():
    client = LLMClient()
    if not client.is_configured():
        with pytest.raises(RuntimeError, match="No active LLM provider configured"):
            client.generate_analysis("def hello(): pass", "Build a React Redux state machine for e-commerce cart")
