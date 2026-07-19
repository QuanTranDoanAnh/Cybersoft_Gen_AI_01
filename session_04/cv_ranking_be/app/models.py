from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


RequirementStatus = Literal["met", "partial", "missing"]
Recommendation = Literal["strong_match", "match", "potential", "weak_match", "not_match"]


class RequirementCheck(BaseModel):
    requirement: str
    status: RequirementStatus
    evidence: str = ""


class RubricCriterion(BaseModel):
    name: str
    description: str
    weight: int = Field(ge=0, le=100)
    scoring_guide: str
    evidence_required: bool = True


class CriterionScore(BaseModel):
    name: str
    max_points: int
    awarded_points: float
    score_ratio: float = Field(ge=0, le=1)
    reason: str
    evidence: list[str] = Field(default_factory=list)


class JobProfile(BaseModel):
    title: str
    must_have_requirements: list[str] = Field(default_factory=list)
    nice_to_have_requirements: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    required_skills: list[str] = Field(default_factory=list)
    domain_terms: list[str] = Field(default_factory=list)
    years_required: int | None = None


class CandidateScore(BaseModel):
    file_name: str
    candidate_name: str
    overall_score: float = Field(ge=0, le=100)
    recommendation: Recommendation
    qualified: bool
    confidence_score: float = Field(ge=0, le=1)
    summary: str
    must_have_checks: list[RequirementCheck] = Field(default_factory=list)
    criterion_scores: list[CriterionScore] = Field(default_factory=list)
    matched_requirements: list[str] = Field(default_factory=list)
    missing_requirements: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    interview_questions: list[str] = Field(default_factory=list)


class RankingResponse(BaseModel):
    generated_at: datetime
    engine: str = "heuristic"
    model: str | None = None
    job_profile: JobProfile
    rubric: list[RubricCriterion]
    candidates: list[CandidateScore]


class HealthResponse(BaseModel):
    status: str
    service: str
    openai_configured: bool = False
    default_model: str | None = None
    database_url: str | None = None


class RegisterRequest(BaseModel):
    email: str
    password: str = Field(min_length=6)
    full_name: str


class LoginRequest(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    created_at: datetime


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class AnalysisListItem(BaseModel):
    id: str
    title: str
    engine: str
    model: str | None = None
    candidate_count: int
    qualified_count: int
    average_score: float
    created_at: datetime


class AnalysisDetail(AnalysisListItem):
    result: RankingResponse


class JDProfileListItem(BaseModel):
    id: str
    title: str
    file_name: str
    must_have_count: int
    required_skills: list[str] = Field(default_factory=list)
    created_at: datetime


class CVProfileListItem(BaseModel):
    id: str
    candidate_name: str
    file_name: str
    created_at: datetime


class DashboardResponse(BaseModel):
    total_analyses: int
    total_candidates: int
    total_jds: int
    total_cvs: int
    qualified_rate: float
    average_score: float
    recommendation_counts: dict[str, int] = Field(default_factory=dict)
    engine_counts: dict[str, int] = Field(default_factory=dict)
    score_buckets: dict[str, int] = Field(default_factory=dict)
    recent_analyses: list[AnalysisListItem] = Field(default_factory=list)
