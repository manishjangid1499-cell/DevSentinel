import pytest
from pathlib import Path
from backend.app.core.database import SessionLocal, Base, engine
from backend.app.models.job import ReviewJob
from backend.app.agent.engine import DevSentinelAgent

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def test_devsentinel_agent_full_loop():
    db = SessionLocal()
    sample_dir = Path("sample_repos/audio_transcoder")
    sample_dir.mkdir(parents=True, exist_ok=True)
    (sample_dir / "audio_transcoder").mkdir(parents=True, exist_ok=True)
    (sample_dir / "tests").mkdir(parents=True, exist_ok=True)
    (sample_dir / "audio_transcoder" / "__init__.py").write_text("", encoding="utf-8")
    (sample_dir / "audio_transcoder" / "parser.py").write_text('''def parse_audio_metadata(header_bytes: bytes) -> dict:
    riff = header_bytes[0:4]
    chunk_size = int.from_bytes(header_bytes[4:8], "little")
    return {"format": "WAVE", "chunk_size": chunk_size}
''', encoding="utf-8")

    job = ReviewJob(
        repo_name="Test Audio Transcoder",
        repo_path=str(sample_dir),
        issue_description="CWE-120 Buffer Overrun in parser. Synthesize reproduction test and apply bounds check.",
        status="PENDING"
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    agent = DevSentinelAgent(db, job)
    agent.run()

    db.refresh(job)
    assert job.status == "AWAITING_REVIEW"
    assert job.security_score >= 90
    assert len(job.trajectory) >= 5
    assert "tests/test_devsentinel_reproduce.py" in str(job.trajectory)
    assert job.patch_diff != ""
    db.close()
