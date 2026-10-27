import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.database import Base, engine, SessionLocal
from backend.app.models.job import ReviewJob

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_test_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_get_dashboard_stats_empty():
    response = client.get("/api/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["total_jobs"] == 0
    assert data["acceptance_rate"] == 0.0

def test_create_and_fetch_job(tmp_path):
    repo_dir = tmp_path / "sample_test_repo"
    repo_dir.mkdir()
    payload = {
        "repo_name": "Test Repo",
        "repo_path": str(repo_dir),
        "issue_description": "Fix boundary condition in audio DSP parser"
    }
    response = client.post("/api/jobs", json=payload)
    assert response.status_code == 200
    job_id = response.json()["id"]
    assert job_id is not None

    get_resp = client.get(f"/api/jobs/{job_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["repo_name"] == "Test Repo"
    assert get_resp.json()["verification_status"] in ["PENDING", "FAILED"]

def test_state_transition_validation():
    db = SessionLocal()
    job = ReviewJob(
        repo_name="Pending Repo",
        repo_path="sample_repos/audio_transcoder",
        issue_description="CWE-120 Buffer Overrun",
        status="PENDING"
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Attempting to approve while in PENDING state must return 400 Bad Request
    action_payload = {
        "decision": "APPROVED",
        "feedback": "Premature approval test"
    }
    resp = client.post(f"/api/jobs/{job.id}/action", json=action_payload)
    assert resp.status_code == 400
    assert "must be in 'AWAITING_REVIEW'" in resp.json()["detail"]
    db.close()

def test_human_in_the_loop_approval_and_rejection(tmp_path):
    orig_dir = tmp_path / "live_repo"
    orig_dir.mkdir()
    target_file = orig_dir / "service.py"
    target_file.write_text("def run(): return 'unpatched'", encoding="utf-8")

    cand_dir = tmp_path / "candidate_staging"
    cand_dir.mkdir()
    cand_file = cand_dir / "service.py"
    cand_file.write_text("def run(): return 'patched'", encoding="utf-8")

    db = SessionLocal()
    job = ReviewJob(
        repo_name="Staged Repo",
        repo_path=str(orig_dir),
        candidate_workspace_path=str(cand_dir),
        issue_description="CWE-120 Buffer Overrun in parser",
        status="AWAITING_REVIEW"
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Prior to approval, original file must remain unpatched
    assert target_file.read_text(encoding="utf-8") == "def run(): return 'unpatched'"

    # Approve
    action_resp = client.post(f"/api/jobs/{job.id}/action", json={"decision": "APPROVED", "feedback": "Approved by engineer"})
    assert action_resp.status_code == 200
    assert action_resp.json()["status"] == "APPROVED"

    # Now original file has the approved patch applied
    assert target_file.read_text(encoding="utf-8") == "def run(): return 'patched'"
    db.close()
