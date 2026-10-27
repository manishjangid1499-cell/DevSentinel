import os
import shutil
from pathlib import Path
from typing import List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.core.database import get_db
from backend.app.models.job import ReviewJob
from backend.app.schemas.job import JobCreate, JobResponse, JobActionRequest, DashboardStats
from backend.app.agent.engine import DevSentinelAgent

router = APIRouter()

def execute_agent_task(job_id: str, db_factory):
    db: Session = db_factory()
    try:
        job = db.query(ReviewJob).filter(ReviewJob.id == job_id).first()
        if job:
            agent = DevSentinelAgent(db, job)
            agent.run()
    finally:
        db.close()

@router.post("/jobs", response_model=JobResponse)
def create_job(job_in: JobCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    job = ReviewJob(
        repo_name=job_in.repo_name,
        repo_path=job_in.repo_path,
        issue_description=job_in.issue_description,
        status="PENDING"
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    from backend.app.core.database import SessionLocal
    background_tasks.add_task(execute_agent_task, job.id, SessionLocal)
    return job.to_dict()

@router.get("/jobs", response_model=List[JobResponse])
def list_jobs(db: Session = Depends(get_db)):
    jobs = db.query(ReviewJob).order_by(ReviewJob.created_at.desc()).all()
    return [j.to_dict() for j in jobs]

@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(ReviewJob).filter(ReviewJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.to_dict()

@router.post("/jobs/{job_id}/action", response_model=JobResponse)
def handle_human_action(job_id: str, action: JobActionRequest, db: Session = Depends(get_db)):
    job = db.query(ReviewJob).filter(ReviewJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    decision = action.decision.upper()
    job.human_decision = decision
    job.human_feedback = action.feedback or ""
    
    if decision == "APPROVED":
        job.status = "APPROVED"
    elif decision == "REJECTED":
        job.status = "REJECTED"
    elif decision == "REVISION_REQUESTED":
        job.status = "REVISION_REQUESTED"

    db.commit()
    db.refresh(job)
    return job.to_dict()

@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(db: Session = Depends(get_db)):
    total = db.query(ReviewJob).count()
    approved = db.query(ReviewJob).filter(ReviewJob.human_decision == "APPROVED").count()
    rejected = db.query(ReviewJob).filter(ReviewJob.human_decision == "REJECTED").count()
    pending = db.query(ReviewJob).filter(ReviewJob.status == "AWAITING_REVIEW").count()
    
    acceptance_rate = round((approved / total * 100), 1) if total > 0 else 0.0
    total_cost = db.query(func.sum(ReviewJob.cost_usd)).scalar() or 0.0
    avg_sec = db.query(func.avg(ReviewJob.security_score)).scalar() or 0.0

    return {
        "total_jobs": total,
        "approved_jobs": approved,
        "rejected_jobs": rejected,
        "pending_review": pending,
        "acceptance_rate": acceptance_rate,
        "total_cost_usd": round(total_cost, 4),
        "avg_security_score": round(avg_sec, 1)
    }

@router.post("/demo/seed", response_model=JobResponse)
def seed_demo_job(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Sets up the sample Shure audio transcoder repository with intentional flaws
    and launches an automated DevSentinel remediation job.
    """
    base_dir = Path(__file__).resolve().parent.parent.parent.parent
    sample_dir = base_dir / "sample_repos" / "audio_transcoder"
    sample_dir.mkdir(parents=True, exist_ok=True)
    (sample_dir / "audio_transcoder").mkdir(parents=True, exist_ok=True)
    (sample_dir / "tests").mkdir(parents=True, exist_ok=True)

    # Write intentional buggy audio parser
    (sample_dir / "audio_transcoder" / "__init__.py").write_text("", encoding="utf-8")
    (sample_dir / "audio_transcoder" / "parser.py").write_text('''"""
Audio Metadata Parser & Transcoder Engine.
VULNERABLE VERSION: Contains unchecked buffer bounds.
"""
def parse_audio_metadata(header_bytes: bytes) -> dict:
    if len(header_bytes) < 12:
        raise ValueError("Header too short")
    riff = header_bytes[0:4]
    chunk_size = int.from_bytes(header_bytes[4:8], "little")
    wave_format = header_bytes[8:12]
    # BUG: No bounds check on chunk_size vs len(header_bytes)
    return {
        "format": wave_format.decode("ascii", errors="replace"),
        "chunk_size": chunk_size,
        "valid": True
    }
''', encoding="utf-8")

    # Write intentional SQL injection vulnerability in db.py
    (sample_dir / "audio_transcoder" / "db.py").write_text('''"""
Track Logging Database Module.
VULNERABLE VERSION: Direct string formatting into SQL query.
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
    # VULNERABILITY: Raw SQL query string interpolation (CWE-89)
    query = f"INSERT INTO track_logs (title, duration) VALUES ('{title}', {duration})"
    cursor.execute(query)
    conn.commit()
    conn.close()
    return True
''', encoding="utf-8")

    # Create the demo job
    job = ReviewJob(
        repo_name="Shure Audio DSP Transcoder",
        repo_path=str(sample_dir),
        issue_description="CWE-120 Buffer Overrun in metadata parser and CWE-89 SQL Injection in track logging query. Generate unit tests, apply secure patches, and verify regression.",
        status="PENDING"
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    from backend.app.core.database import SessionLocal
    background_tasks.add_task(execute_agent_task, job.id, SessionLocal)
    return job.to_dict()
