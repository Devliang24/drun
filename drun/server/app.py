from __future__ import annotations

from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from typing import Optional, List
from pydantic import BaseModel

from .database import ReportsDB
from .scanner import scan_and_index

app = FastAPI(
    title="Drun Report Server",
    description="Lightweight test report server with SQLite persistence",
    version="1.0.0"
)

# Initialize database
db = ReportsDB()

# Mount static files (HTML reports)
try:
    app.mount("/static", StaticFiles(directory="reports"), name="static")
except RuntimeError:
    # Directory might not exist yet
    pass


# Pydantic models
class ReportSummary(BaseModel):
    id: int
    file_name: str
    system_name: Optional[str] = None
    run_time: Optional[str] = None
    total_cases: int
    passed_cases: int
    failed_cases: int
    duration_ms: float
    tags: List[str] = []
    environment: Optional[str] = None


class ReportDetail(ReportSummary):
    file_path: str
    notes: Optional[str] = None
    raw_summary: dict = {}


@app.on_event("startup")
async def startup_event():
    """Scan reports directory on startup"""
    count = scan_and_index("reports", db)
    print(f"[SERVER] Indexed {count} reports")


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve frontend page"""
    html_file = Path(__file__).parent / "templates" / "index.html"
    if not html_file.exists():
        return HTMLResponse(
            content="<h1>Drun Report Server</h1><p>Frontend template not found. Visit <a href='/docs'>/docs</a> for API documentation.</p>",
            status_code=500
        )
    return HTMLResponse(content=html_file.read_text(encoding="utf-8"))


@app.get("/api/reports", response_model=List[ReportSummary])
async def list_reports(
    limit: int = Query(50, ge=1, le=100, description="Maximum number of reports to return"),
    offset: int = Query(0, ge=0, description="Number of reports to skip"),
    system_name: Optional[str] = Query(None, description="Filter by system name (partial match)"),
    environment: Optional[str] = Query(None, description="Filter by environment"),
    status: Optional[str] = Query(None, regex="^(passed|failed|all)$", description="Filter by status"),
):
    """Get list of reports with optional filtering and pagination"""
    reports = db.list_reports(
        limit=limit,
        offset=offset,
        system_name=system_name,
        environment=environment,
        status=status if status != "all" else None
    )
    return reports


@app.get("/api/reports/{report_id}", response_model=ReportDetail)
async def get_report(report_id: int):
    """Get detailed information about a specific report"""
    report = db.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@app.post("/api/reports/rescan")
async def rescan_reports():
    """Rescan reports directory and update database"""
    count = scan_and_index("reports", db)
    return {"message": f"Indexed {count} reports", "count": count}


@app.patch("/api/reports/{report_id}/notes")
async def update_notes(report_id: int, notes: str = Query(..., description="New notes content")):
    """Update notes for a report"""
    report = db.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    db.update_notes(report_id, notes)
    return {"message": "Notes updated successfully"}


@app.delete("/api/reports/{report_id}")
async def delete_report(report_id: int):
    """Delete a report record from database"""
    report = db.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    db.delete_report(report_id)
    return {"message": "Report deleted successfully"}


@app.get("/api/stats")
async def get_stats():
    """Get aggregate statistics across all reports"""
    return db.get_stats()


@app.get("/reports/{file_name}")
async def serve_report(file_name: str):
    """Serve individual HTML report file"""
    file_path = Path("reports") / file_name
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Report file not found")
    
    # Security: prevent directory traversal
    if ".." in file_name or "/" in file_name or "\\" in file_name:
        raise HTTPException(status_code=400, detail="Invalid file name")
    
    return FileResponse(file_path, media_type="text/html")
