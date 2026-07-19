from __future__ import annotations

import json
from datetime import datetime

from pydantic import BaseModel, Field

from app.models import CandidateScore, JobProfile, RankingResponse, RubricCriterion
from app.services.scoring import default_rubric


class LLMRankingPayload(BaseModel):
    job_profile: JobProfile
    rubric: list[RubricCriterion] = Field(default_factory=list)
    candidates: list[CandidateScore] = Field(default_factory=list)


def truncate_text(text: str, max_chars: int = 16000) -> str:
    text = (text or "").strip()
    if len(text) <= max_chars:
        return text
    return f"{text[:max_chars]}\n\n[TRUNCATED]"


def rank_candidates_with_openai(
    jd_text: str,
    cv_documents: list[tuple[str, str]],
    model_name: str,
) -> RankingResponse:
    try:
        from langchain_openai import ChatOpenAI
    except ImportError as exc:
        raise RuntimeError(
            "Missing langchain-openai. Install backend requirements first."
        ) from exc

    rubric = default_rubric()
    # Code ở đây
    cv_payload = [
        {"file_name": file_name, "cv_text": truncate_text(cv_text)}
        for file_name, cv_text in cv_documents
    ]

    prompt = f"""
    You are an evidence-based recruiting analyst.

Task:
Rank candidate CVs against the uploaded JD using structured output only.

Rules:
- Analyze the JD first. Extract must-have requirements, nice-to-have requirements, responsibilities, required skills, domain terms, and years_required.
- Use the rubric below exactly. The total score must be 100.
- Must-have requirements are gating conditions, not extra points.
- If a candidate misses any must-have requirement, set qualified=false and cap overall_score at 59.
- Every criterion score must include concise evidence from the CV when evidence exists.
- Do not use protected or sensitive attributes such as age, gender, marital status, race, religion, photo, nationality, or family status.
- Do not infer facts that are not present in the CV.
- Keep reasons concise and suitable for a recruiter dashboard.
- Sort candidates from strongest to weakest.

Rubric:
{json.dumps([item.model_dump() for item in rubric], ensure_ascii=False, indent=2)}

JD:
{truncate_text(jd_text)}

CVS:
{json.dumps(cv_payload, ensure_ascii=False, indent=2)}
    """
    llm = ChatOpenAI(model=model_name, temperature=0)
    structured_llm = llm.with_structured_output(LLMRankingPayload)
    payload = structured_llm.invoke(prompt)

    candidates = payload.candidates
    candidates.sort(
        key=lambda item: (item.qualified, item.overall_score, item.confidence_score),
        reverse=True,
    )

    return RankingResponse(
        generated_at=datetime.utcnow(),
        engine="openai",
        model=model_name,
        job_profile=payload.job_profile,
        rubric=payload.rubric,
        candidates=candidates,
    )
