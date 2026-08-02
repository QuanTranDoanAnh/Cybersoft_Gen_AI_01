import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .copilot import run_copilot
from .dashboard import get_overview_dashboard
from .database import fetch_value
from .schemas import (
    CopilotRequest,
    CopilotResponse,
    DashboardResponse,
    MetaResponse,
)
from .seed import seed_database


logging.basicConfig(level=logging.INFO)
settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    await asyncio.to_thread(seed_database)
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "database": "ok" if fetch_value("SELECT 1 AS value") == 1 else "error",
    }


@app.get("/api/meta", response_model=MetaResponse)
def meta() -> MetaResponse:
    return MetaResponse(
        app_name=settings.app_name,
        model=settings.openai_model,
        copilot_mode="openai" if settings.openai_api_key else "demo",
        dataset="TMDB TV Shows",
    )


@app.get("/api/dashboard/overview", response_model=DashboardResponse)
def overview() -> DashboardResponse:
    return get_overview_dashboard()


@app.post("/api/copilot/query", response_model=CopilotResponse)
def copilot_query(request: CopilotRequest) -> CopilotResponse:
    try:
        return run_copilot(request.prompt)
    except Exception as exc:
        logging.exception("Copilot request failed")
        raise HTTPException(status_code=422, detail=str(exc)) from exc
