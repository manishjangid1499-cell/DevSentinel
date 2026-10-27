import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, Float, DateTime, JSON
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class ReviewJob(Base):
    __tablename__ = "review_jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    repo_name = Column(String(255), nullable=False)
    repo_path = Column(String(1024), nullable=False)
    issue_description = Column(Text, nullable=False)
    status = Column(String(50), default="PENDING")  # PENDING, ANALYZING, TESTING, PATCHING, AWAITING_REVIEW, APPROVED, REJECTED
    
    # Metrics & Quality Audit
    security_score = Column(Integer, default=0)         # 0 - 100
    maintainability_score = Column(Integer, default=0)   # 0 - 100
    cost_usd = Column(Float, default=0.0)
    execution_time_seconds = Column(Float, default=0.0)

    # Artifacts
    test_output = Column(Text, default="")
    patch_diff = Column(Text, default="")
    trajectory = Column(JSON, default=list)  # List of steps with thoughts, actions, observations

    # Human-in-the-Loop Feedback
    human_decision = Column(String(50), default="PENDING") # PENDING, APPROVED, REJECTED, REVISION_REQUESTED
    human_feedback = Column(Text, default="")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "repo_name": self.repo_name,
            "repo_path": self.repo_path,
            "issue_description": self.issue_description,
            "status": self.status,
            "security_score": self.security_score,
            "maintainability_score": self.maintainability_score,
            "cost_usd": self.cost_usd,
            "execution_time_seconds": self.execution_time_seconds,
            "test_output": self.test_output,
            "patch_diff": self.patch_diff,
            "trajectory": self.trajectory or [],
            "human_decision": self.human_decision,
            "human_feedback": self.human_feedback,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
