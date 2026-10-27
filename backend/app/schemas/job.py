from enum import Enum
from typing import Optional, List, Any
from pydantic import BaseModel, Field

class HumanDecisionEnum(str, Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    REVISION_REQUESTED = "REVISION_REQUESTED"

class JobCreate(BaseModel):
    repo_name: str = Field(..., min_length=1, max_length=255)
    repo_path: str = Field(..., min_length=1, max_length=1024)
    issue_description: str = Field(..., min_length=5, max_length=4000)

class JobActionRequest(BaseModel):
    decision: HumanDecisionEnum
    feedback: Optional[str] = Field("", max_length=2000)

class JobResponse(BaseModel):
    id: str
    repo_name: str
    repo_path: str
    status: str
    verification_status: str
    execution_mode: str
    provider_used: str
    issue_description: str
    security_score: int
    maintainability_score: int
    cost_usd: float
    execution_time_seconds: float
    baseline_exit_code: int
    verification_exit_code: int
    test_output: str
    patch_diff: str
    remaining_uncertainty: str
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
