from __future__ import annotations

import os
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
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

# Get reports directory from environment variable (absolute path)
REPORTS_DIR = Path(os.getenv("DRUN_REPORTS_DIR", "reports")).resolve()

# Initialize database with absolute path
db = ReportsDB(db_path=str(REPORTS_DIR / "reports.db"))


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
    try:
        count = scan_and_index(str(REPORTS_DIR), db)
        print(f"[SERVER] Indexed {count} reports from {REPORTS_DIR}")
    except Exception as e:
        print(f"[SERVER] Failed to index reports: {e}")
        # Don't crash - allow server to continue starting


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
    status: Optional[str] = Query(None, pattern="^(passed|failed|all)$", description="Filter by status"),
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
    """Serve individual HTML report file with back button"""
    # Security: prevent directory traversal
    if ".." in file_name or "/" in file_name or "\\" in file_name:
        raise HTTPException(status_code=400, detail="Invalid file name")
    
    file_path = REPORTS_DIR / file_name
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Report file not found")
    
    # Read original HTML content
    html_content = file_path.read_text(encoding="utf-8")
    
    # Inject back button style and adjust header to match list page
    button_style = """
    <style>
        /* Override wrap styles to match list page - use higher specificity */
        body .wrap,
        .wrap {
            max-width: 1310px !important;
            margin-left: auto !important;
            margin-right: auto !important;
            padding: 0 20px 40px !important;
        }
        /* Override header styles to match list page */
        .header-sticky {
            position: sticky !important;
            top: 0 !important;
            z-index: 999 !important;
            background: #ffffff !important;
            padding: 16px 0 12px !important;
            border-bottom: 1px solid #d0d7de !important;
            margin-bottom: 20px !important;
            box-shadow: none !important;
        }
        .headbar {
            display: flex !important;
            justify-content: space-between !important;
            align-items: center !important;
            gap: 12px !important;
            margin-bottom: 12px !important;
        }
        /* Remove extra spacing - margin-bottom on header is enough */
        .summary {
            margin-top: 0 !important;
        }
        .back-to-list-btn {
            padding: 0;
            background: none;
            color: #0969da;
            border: none;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            text-decoration: none;
            transition: color 0.15s ease;
            white-space: nowrap;
        }
        .back-to-list-btn:hover {
            color: #1a7f37;
            text-decoration: underline;
        }
        /* Override all button styles in detail page to text-only */
        .toolbar button {
            padding: 0 !important;
            border: none !important;
            background: none !important;
            color: #0969da !important;
            border-radius: 0 !important;
            font-weight: 500 !important;
        }
        .toolbar button:hover {
            color: #1a7f37 !important;
            text-decoration: underline !important;
            border-color: transparent !important;
        }
        .panel .p-head button {
            padding: 0 !important;
            border: none !important;
            background: none !important;
            color: #0969da !important;
            border-radius: 0 !important;
            font-size: 12px !important;
        }
        .panel .p-head button:hover {
            color: #1a7f37 !important;
            text-decoration: underline !important;
            border-color: transparent !important;
        }
        .panel .p-head button.copied {
            color: #1a7f37 !important;
            background: none !important;
            border: none !important;
        }
        .panel .p-head button.copy-failed {
            color: #cf222e !important;
            background: none !important;
            border: none !important;
        }
    </style>
    """
    
    # Replace .meta div with back button
    import re
    # Match: <div class='meta'>...</div>
    pattern = r"<div class=['\"]meta['\"]>.*?</div>"
    
    # Replace meta div with just the back button
    button_html = "<a href='/' class='back-to-list-btn'>返回列表</a>"
    html_content = re.sub(pattern, button_html, html_content, count=1)
    
    # Inject style into <head>
    if "</head>" in html_content:
        html_content = html_content.replace("</head>", f"{button_style}</head>")
    
    return HTMLResponse(content=html_content)
