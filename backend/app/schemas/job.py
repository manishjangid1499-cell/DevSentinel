from typing import Optional, List, Any
from pydantic import BaseModel, Field

class JobCreate(BaseModel):
    repo_name: str = Field(..., example="audio_transcoder")
    repo_path: str = Field(..., example="sample_repos/audio_transcoder")
    issue_description: str = Field(..., example="Fix buffer overflow in metadata parser and prevent SQL injection in track logging")

class JobActionRequest(BaseModel):
    decision: str = Field(..., example="APPROVED") # APPROVED, REJECTED, REVISION_REQUESTED
    feedback: Optional[str] = Field("", example="Looks good, clean patch and passes regression tests.")

class JobResponse(BaseModel):
    id: str
    repo_name: str
    repo_path: str
    issue_description: str
    status: str
    security_score: int
    maintainability_score: int
    cost_usd: float
    execution_time_seconds: float
    test_output: str
    patch_diff: str
    trajectory: List[Any]
    human_decision: str
    human_feedback: str
    created_at: Optional[str]
    updated_at: Optional[str]

class DashboardStats(BaseModel):
    total_jobs: int
    approved_jobs: int
    rejected_jobs: int
    pending_review: int
    acceptance_rate: float
    total_cost_usd: float
    avg_security_score: float
