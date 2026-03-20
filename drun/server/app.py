from __future__ import annotations

from contextlib import asynccontextmanager
import html
import logging
import os
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field

from .database import ReportsDB
from .services import ReportService


logger = logging.getLogger("drun.server")

# Get reports directory from environment variable (absolute path)
REPORTS_DIR = Path(os.getenv("DRUN_REPORTS_DIR", "reports")).resolve()

# Initialize database with absolute path
db = ReportsDB(db_path=str(REPORTS_DIR / "reports.db"))
service = ReportService(reports_dir=REPORTS_DIR, db=db, logger=logger)


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        count = service.rescan_reports()
        logger.info("[SERVER] Indexed %s reports from %s", count, REPORTS_DIR)
    except Exception as exc:
        logger.warning("[SERVER] Failed to index reports from %s: %s", REPORTS_DIR, exc)
    yield


app = FastAPI(
    title="Drun Report Server",
    description="Lightweight test report server with SQLite persistence",
    version="2.0.0",
    lifespan=lifespan,
)


class ReportSummary(BaseModel):
    id: int
    file_name: str
    system_name: Optional[str] = None
    run_time: Optional[str] = None
    total_cases: int
    passed_cases: int
    failed_cases: int
    duration_ms: float
    tags: List[str] = Field(default_factory=list)
    environment: Optional[str] = None


class ReportDetail(ReportSummary):
    file_path: str
    notes: Optional[str] = None
    raw_summary: dict = Field(default_factory=dict)


def _load_template(name: str) -> Path:
    template_path = Path(__file__).parent / "templates" / name
    if not template_path.exists():
        raise HTTPException(status_code=500, detail=f"Template not found: {name}")
    return template_path


def _render_detail_shell(file_name: str) -> str:
    template = _load_template("detail.html").read_text(encoding="utf-8")
    report = service.get_report_by_file_name(file_name)

    report_title = file_name.replace(".html", "")
    subtitle_parts = [f"文件：{file_name}"]
    if report:
        system_name = report.get("system_name")
        if system_name:
            report_title = str(system_name)
        if report.get("environment"):
            subtitle_parts.append(f"环境：{report['environment']}")
        if report.get("run_time"):
            subtitle_parts.append(f"运行时间：{report['run_time']}")

    return (
        template
        .replace("__REPORT_TITLE__", html.escape(report_title))
        .replace("__REPORT_SUBTITLE__", html.escape(" | ".join(subtitle_parts)))
        .replace("__REPORT_FILE_NAME__", html.escape(file_name, quote=True))
    )


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve frontend page"""
    html_file = _load_template("index.html")
    return HTMLResponse(content=html_file.read_text(encoding="utf-8"))


@app.get("/api/reports", response_model=List[ReportSummary])
async def list_reports(
    limit: int = Query(50, ge=1, le=100, description="Maximum number of reports to return"),
    offset: int = Query(0, ge=0, description="Number of reports to skip"),
    system_name: Optional[str] = Query(None, description="Filter by system name (partial match)"),
    environment: Optional[str] = Query(None, description="Filter by environment"),
    status: Optional[str] = Query(None, pattern="^(passed|failed|all)$", description="Filter by status"),
):
    """Get list of reports with optional filtering and pagination"""
    return service.list_reports(
        limit=limit,
        offset=offset,
        system_name=system_name,
        environment=environment,
        status=status if status != "all" else None,
    )


@app.get("/api/reports/{report_id}", response_model=ReportDetail)
async def get_report(report_id: int):
    """Get detailed information about a specific report"""
    report = service.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@app.post("/api/reports/rescan")
async def rescan_reports():
    """Rescan reports directory and update database"""
    count = service.rescan_reports()
    return {"message": f"Indexed {count} reports", "count": count}


@app.patch("/api/reports/{report_id}/notes")
async def update_notes(report_id: int, notes: str = Query(..., description="New notes content")):
    """Update notes for a report"""
    if not service.update_notes(report_id, notes):
        raise HTTPException(status_code=404, detail="Report not found")
    return {"message": "Notes updated successfully"}


@app.delete("/api/reports/{report_id}")
async def delete_report(report_id: int):
    """Delete a report record from database"""
    if not service.delete_report(report_id):
        raise HTTPException(status_code=404, detail="Report not found")
    return {"message": "Report deleted successfully"}


@app.get("/api/stats")
async def get_stats():
    """Get aggregate statistics across all reports"""
    return service.get_stats()


@app.get("/reports/raw/{file_name}")
async def serve_raw_report(file_name: str):
    """Serve the original HTML report file."""
    try:
        file_path = service.resolve_report_file(file_name)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid file name") from None

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Report file not found")

    return FileResponse(path=file_path, media_type="text/html")


@app.get("/reports/{file_name}", response_class=HTMLResponse)
async def serve_report_shell(file_name: str):
    """Serve report detail shell page with embedded original report."""
    try:
        file_path = service.resolve_report_file(file_name)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid file name") from None

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Report file not found")

    return HTMLResponse(content=_render_detail_shell(file_name))
