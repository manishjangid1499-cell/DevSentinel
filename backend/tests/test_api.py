import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.database import Base, engine

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_test_db():
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

def test_create_and_fetch_job():
    payload = {
        "repo_name": "Test Repo",
        "repo_path": "sample_repos/audio_transcoder",
        "issue_description": "Fix boundary condition in signal parser"
    }
    response = client.post("/api/jobs", json=payload)
    assert response.status_code == 200
    job_id = response.json()["id"]
    assert job_id is not None

    get_resp = client.get(f"/api/jobs/{job_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["repo_name"] == "Test Repo"

def test_human_in_the_loop_action():
    payload = {
        "repo_name": "Review Sample",
        "repo_path": "sample_repos/audio_transcoder",
        "issue_description": "Review security audit patch"
    }
    create_resp = client.post("/api/jobs", json=payload)
    job_id = create_resp.json()["id"]

    # Act as human reviewer approving the patch
    action_payload = {
        "decision": "APPROVED",
        "feedback": "Regression tests passed and verified."
    }
    action_resp = client.post(f"/api/jobs/{job_id}/action", json=action_payload)
    assert action_resp.status_code == 200
    data = action_resp.json()
    assert data["status"] == "APPROVED"
    assert data["human_decision"] == "APPROVED"
    assert "Regression tests" in data["human_feedback"]
