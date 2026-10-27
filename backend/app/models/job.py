import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Integer, Float, DateTime, JSON
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class ReviewJob(Base):
    __tablename__ = "review_jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    repo_name = Column(String(255), nullable=False)
    repo_path = Column(String(1024), nullable=False)
    candidate_workspace_path = Column(String(1024), nullable=True) # Isolated staging dir
    issue_description = Column(Text, nullable=False)
    
    # State machine: PENDING -> ANALYZING -> TESTING -> PATCHING -> AWAITING_REVIEW -> APPROVED / REJECTED
    status = Column(String(50), default="PENDING")
    verification_status = Column(String(50), default="PENDING") # PASSED, FAILED, TIMED_OUT, INCONCLUSIVE
    execution_mode = Column(String(50), default="LIVE_LLM")     # LIVE_LLM, DEMO_FIXTURE
    provider_used = Column(String(100), default="auto")

    # Quality Audit & Scoring (Explicitly labeled as estimates)
    security_score = Column(Integer, default=0)
    maintainability_score = Column(Integer, default=0)
    cost_usd = Column(Float, default=0.0)
    execution_time_seconds = Column(Float, default=0.0)

    # Verification Telemetry
    baseline_exit_code = Column(Integer, default=-1)
    baseline_test_output = Column(Text, default="")
    verification_exit_code = Column(Integer, default=-1)
    test_output = Column(Text, default="")
    patch_diff = Column(Text, default="")
    remaining_uncertainty = Column(Text, default="")
    trajectory = Column(JSON, default=list)

    # Human-in-the-Loop Decision & Feedback
    human_decision = Column(String(50), default="PENDING") # PENDING, APPROVED, REJECTED, REVISION_REQUESTED
    human_feedback = Column(Text, default="")

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "repo_name": self.repo_name,
            "repo_path": self.repo_path,
            "status": self.status,
            "verification_status": self.verification_status,
            "execution_mode": self.execution_mode,
            "provider_used": self.provider_used,
            "issue_description": self.issue_description,
            "security_score": self.security_score,
            "maintainability_score": self.maintainability_score,
            "cost_usd": self.cost_usd,
            "execution_time_seconds": self.execution_time_seconds,
            "baseline_exit_code": self.baseline_exit_code,
            "verification_exit_code": self.verification_exit_code,
            "test_output": self.test_output,
            "patch_diff": self.patch_diff,
            "remaining_uncertainty": self.remaining_uncertainty,
            "trajectory": self.trajectory or [],
            "human_decision": self.human_decision,
            "human_feedback": self.human_feedback,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
