from __future__ import annotations

import os
from typing import Annotated

from dotenv import load_dotenv
from fastapi import Depends, File, Form, Header, HTTPException, UploadFile
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.database import DATABASE_URL, get_db, init_db
from app.db_models import AnalysisRecord, CVProfileRecord, JDProfileRecord, User
from app.models import (
    AnalysisDetail,
    AnalysisListItem,
    AuthResponse,
    CVProfileListItem,
    DashboardResponse,
    HealthResponse,
    JDProfileListItem,
    LoginRequest,
    RankingResponse,
    RegisterRequest,
    UserResponse,
)
from app.security import create_access_token, decode_access_token, hash_password, verify_password
from app.services.parser import SUPPORTED_EXTENSIONS, extract_text_from_bytes, guess_person_name
from app.services.openai_scoring import rank_candidates_with_openai
from app.services.scoring import rank_candidates


load_dotenv()

FRONTEND_ORIGINS = [
    origin.strip()
    for origin in os.getenv("FRONTEND_ORIGIN", "http://localhost:3000").split(",")
    if origin.strip()
]
DEV_FRONTEND_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
    "http://localhost:3002",
    "http://127.0.0.1:3002",
]

app = FastAPI(
    title="CV Ranking Platform API",
    description="Evidence-based CV ranking API for JD-to-candidate screening.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted(set(FRONTEND_ORIGINS + DEV_FRONTEND_ORIGINS)),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


def database_label() -> str:
    if DATABASE_URL.startswith("postgresql"):
        return "postgresql"
    if DATABASE_URL.startswith("sqlite"):
        return "sqlite"
    return "custom"


def serialize_user(user: User) -> UserResponse:
    return UserResponse(id=user.id, email=user.email, full_name=user.full_name, created_at=user.created_at)


def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token.")

    token = authorization.split(" ", 1)[1]
    try:
        payload = decode_access_token(token)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token.") from exc

    user = db.query(User).filter(User.id == payload["sub"]).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found.")
    return user


def analysis_to_list_item(record: AnalysisRecord) -> AnalysisListItem:
    return AnalysisListItem(
        id=record.id,
        title=record.title,
        engine=record.engine,
        model=record.model,
        candidate_count=record.candidate_count,
        qualified_count=record.qualified_count,
        average_score=round(record.average_score, 2),
        created_at=record.created_at,
    )


@app.get("/api/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service="cv-ranking-api",
        openai_configured=bool(os.getenv("OPENAI_API_KEY")),
        default_model=os.getenv("OPENAI_MODEL", "gpt-5-mini"),
        database_url=database_label(),
    )


@app.post("/api/auth/register", response_model=AuthResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> AuthResponse:
    email = payload.email.strip().lower()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=409, detail="Email is already registered.")

    user = User(email=email, full_name=payload.full_name.strip(), password_hash=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return AuthResponse(access_token=create_access_token(user.id, user.email), user=serialize_user(user))


@app.post("/api/auth/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> AuthResponse:
    email = payload.email.strip().lower()
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    return AuthResponse(access_token=create_access_token(user.id, user.email), user=serialize_user(user))


@app.get("/api/auth/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return serialize_user(current_user)


@app.post("/api/rank", response_model=RankingResponse)
async def rank_endpoint(
    jd: Annotated[UploadFile, File(description="Job description file")],
    cvs: Annotated[list[UploadFile], File(description="One or more CV files")],
    engine: Annotated[str, Form(description="heuristic or openai")] = "heuristic",
    model: Annotated[str | None, Form(description="OpenAI model name")] = None,
    analysis_title: Annotated[str | None, Form(description="Optional analysis title")] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RankingResponse:
    if not cvs:
        raise HTTPException(status_code=400, detail="Upload at least one CV file.")

    try:
        jd_text = extract_text_from_bytes(jd.filename or "job_description.txt", await jd.read())
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not read JD: {exc}") from exc

    cv_documents: list[tuple[str, str]] = []
    errors: list[str] = []
    for cv in cvs:
        file_name = cv.filename or "candidate_cv.txt"
        try:
            extension = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
            if extension not in SUPPORTED_EXTENSIONS:
                errors.append(f"{file_name}: unsupported file type")
                continue
            cv_documents.append((file_name, extract_text_from_bytes(file_name, await cv.read())))
        except Exception as exc:
            errors.append(f"{file_name}: {exc}")

    if not cv_documents:
        raise HTTPException(status_code=400, detail={"message": "No CV files could be read.", "errors": errors})

    normalized_engine = engine.strip().lower()
    if normalized_engine not in {"heuristic", "openai"}:
        raise HTTPException(status_code=400, detail="engine must be 'heuristic' or 'openai'.")

    if normalized_engine == "openai":
        if not os.getenv("OPENAI_API_KEY"):
            raise HTTPException(status_code=400, detail="OPENAI_API_KEY is missing in backend .env.")
        try:
            response = rank_candidates_with_openai(
                jd_text=jd_text,
                cv_documents=cv_documents,
                model_name=model or os.getenv("OPENAI_MODEL", "gpt-5-mini"),
            )
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"OpenAI ranking failed: {exc}") from exc
    else:
        response = rank_candidates(jd_text, cv_documents)

    if errors:
        for candidate in response.candidates:
            candidate.risks.append(f"Some uploaded files were skipped: {'; '.join(errors[:3])}")
            break

    jd_profile = JDProfileRecord(
        user_id=current_user.id,
        title=response.job_profile.title,
        file_name=jd.filename or "job_description.txt",
        content=jd_text,
        extracted_profile=response.job_profile.model_dump(mode="json"),
    )
    db.add(jd_profile)
    db.flush()

    for file_name, cv_text in cv_documents:
        db.add(
            CVProfileRecord(
                user_id=current_user.id,
                candidate_name=guess_person_name(cv_text, file_name),
                file_name=file_name,
                content=cv_text,
            )
        )

    candidate_count = len(response.candidates)
    qualified_count = sum(1 for candidate in response.candidates if candidate.qualified)
    average_score = (
        sum(candidate.overall_score for candidate in response.candidates) / candidate_count if candidate_count else 0
    )
    result_json = response.model_dump(mode="json")
    db.add(
        AnalysisRecord(
            user_id=current_user.id,
            jd_profile_id=jd_profile.id,
            title=(analysis_title or response.job_profile.title or "Untitled analysis")[:255],
            engine=response.engine,
            model=response.model,
            candidate_count=candidate_count,
            qualified_count=qualified_count,
            average_score=average_score,
            result_json=result_json,
        )
    )
    db.commit()
    return response


@app.get("/api/analyses", response_model=list[AnalysisListItem])
def list_analyses(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[AnalysisListItem]:
    records = (
        db.query(AnalysisRecord)
        .filter(AnalysisRecord.user_id == current_user.id)
        .order_by(AnalysisRecord.created_at.desc())
        .all()
    )
    return [analysis_to_list_item(record) for record in records]


@app.get("/api/analyses/{analysis_id}", response_model=AnalysisDetail)
def get_analysis(
    analysis_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AnalysisDetail:
    record = (
        db.query(AnalysisRecord)
        .filter(AnalysisRecord.id == analysis_id, AnalysisRecord.user_id == current_user.id)
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="Analysis not found.")

    item = analysis_to_list_item(record)
    return AnalysisDetail(**item.model_dump(), result=RankingResponse.model_validate(record.result_json))


@app.get("/api/library/jds", response_model=list[JDProfileListItem])
def list_jds(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[JDProfileListItem]:
    records = (
        db.query(JDProfileRecord)
        .filter(JDProfileRecord.user_id == current_user.id)
        .order_by(JDProfileRecord.created_at.desc())
        .all()
    )
    return [
        JDProfileListItem(
            id=record.id,
            title=record.title,
            file_name=record.file_name,
            must_have_count=len(record.extracted_profile.get("must_have_requirements", [])),
            required_skills=record.extracted_profile.get("required_skills", []),
            created_at=record.created_at,
        )
        for record in records
    ]


@app.get("/api/library/cvs", response_model=list[CVProfileListItem])
def list_cvs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[CVProfileListItem]:
    records = (
        db.query(CVProfileRecord)
        .filter(CVProfileRecord.user_id == current_user.id)
        .order_by(CVProfileRecord.created_at.desc())
        .all()
    )
    return [
        CVProfileListItem(
            id=record.id,
            candidate_name=record.candidate_name,
            file_name=record.file_name,
            created_at=record.created_at,
        )
        for record in records
    ]


@app.get("/api/dashboard", response_model=DashboardResponse)
def dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DashboardResponse:
    analyses = db.query(AnalysisRecord).filter(AnalysisRecord.user_id == current_user.id).all()
    total_jds = db.query(JDProfileRecord).filter(JDProfileRecord.user_id == current_user.id).count()
    total_cvs = db.query(CVProfileRecord).filter(CVProfileRecord.user_id == current_user.id).count()

    total_candidates = sum(record.candidate_count for record in analyses)
    total_qualified = sum(record.qualified_count for record in analyses)
    weighted_score_sum = sum(record.average_score * record.candidate_count for record in analyses)
    average_score = weighted_score_sum / total_candidates if total_candidates else 0

    recommendation_counts: dict[str, int] = {}
    engine_counts: dict[str, int] = {}
    score_buckets = {"90-100": 0, "75-89": 0, "60-74": 0, "40-59": 0, "0-39": 0}

    for record in analyses:
        engine_counts[record.engine] = engine_counts.get(record.engine, 0) + 1
        for candidate in record.result_json.get("candidates", []):
            recommendation = candidate.get("recommendation", "unknown")
            recommendation_counts[recommendation] = recommendation_counts.get(recommendation, 0) + 1
            score = float(candidate.get("overall_score", 0))
            if score >= 90:
                score_buckets["90-100"] += 1
            elif score >= 75:
                score_buckets["75-89"] += 1
            elif score >= 60:
                score_buckets["60-74"] += 1
            elif score >= 40:
                score_buckets["40-59"] += 1
            else:
                score_buckets["0-39"] += 1

    recent = (
        db.query(AnalysisRecord)
        .filter(AnalysisRecord.user_id == current_user.id)
        .order_by(AnalysisRecord.created_at.desc())
        .limit(5)
        .all()
    )

    return DashboardResponse(
        total_analyses=len(analyses),
        total_candidates=total_candidates,
        total_jds=total_jds,
        total_cvs=total_cvs,
        qualified_rate=round(total_qualified / total_candidates, 4) if total_candidates else 0,
        average_score=round(average_score, 2),
        recommendation_counts=recommendation_counts,
        engine_counts=engine_counts,
        score_buckets=score_buckets,
        recent_analyses=[analysis_to_list_item(record) for record in recent],
    )
