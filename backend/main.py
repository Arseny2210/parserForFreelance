"""
FastAPI backend for the Freelance Market Analyzer.

Serves collected freelance orders with Kwork-first priority, rich filtering,
analytics and on-demand collection. Optionally serves the built React frontend.
"""

from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from backend.service import service

app = FastAPI(
    title="Freelance Market Analyzer API",
    version="2.0.0",
    description="Сбор и анализ IT-заказов с фриланс-бирж (Kwork, FL.ru)",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CollectRequest(BaseModel):
    sources: list[str] = ["kwork", "fl"]


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok", "service": "freelance-market-analyzer"}


@app.get("/api/status")
async def get_status() -> dict:
    return service.status()


@app.get("/api/filters")
async def get_filters() -> dict:
    return service.filters_meta()


@app.get("/api/analytics")
async def get_analytics() -> dict:
    return service.analytics()


@app.get("/api/tasks")
async def get_tasks(
    q: Optional[str] = None,
    sources: Optional[str] = Query(default=None),
    categories: Optional[str] = Query(default=None),
    budget_min: Optional[float] = None,
    budget_max: Optional[float] = None,
    it_only: bool = True,
    scope: str = Query(
        default="all",
        description="Сфера: all | it | design | it_design",
    ),
    freshness: Optional[str] = Query(
        default=None, description="Период: 24h | 3d | 7d | 30d"
    ),
    has_budget: bool = False,
    min_proposals: Optional[int] = None,
    max_proposals: Optional[int] = None,
    search_desc: bool = False,
    sort: str = Query(
        default="priority",
        description="priority | date | budget_desc | budget_asc | proposals_asc",
    ),
    limit: int = Query(default=2000, ge=1, le=5000),
) -> dict:
    src_list = sources.split(",") if sources else None
    cat_list = categories.split(",") if categories else None

    freshness_hours = None
    if freshness:
        if freshness.endswith("h"):
            freshness_hours = int(freshness[:-1])
        elif freshness.endswith("d"):
            freshness_hours = int(freshness[:-1]) * 24

    tasks = service.filter_tasks(
        query=q,
        sources=src_list,
        categories=cat_list,
        budget_min=budget_min,
        budget_max=budget_max,
        scope=scope if scope in ("it", "design", "it_design") else "all",
        freshness_hours=freshness_hours,
        has_budget=has_budget,
        min_proposals=min_proposals,
        max_proposals=max_proposals,
        search_desc=search_desc,
        sort=sort,
    )

    total = len(tasks)
    return {"total": total, "tasks": tasks[:limit]}


@app.post("/api/collect")
async def collect(req: CollectRequest) -> dict:
    return service.start_collect(req.sources)


@app.get("/api/tasks/{source}/{task_id}/full-description")
async def get_full_description(source: str, task_id: str) -> dict:
    import asyncio

    full = await asyncio.to_thread(service.get_full_description, source, task_id)
    if full is None:
        return {"error": "not_found"}
    return {"source": source, "task_id": task_id, "description": full}


# ── Serve built React frontend (production) ──────────────────────
FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"


def _mount_frontend() -> None:
    if not FRONTEND_DIST.exists():
        return
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa(full_path: str):
        candidate = FRONTEND_DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / "index.html")


_mount_frontend()
