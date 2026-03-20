from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from .database import ReportsDB
from .scanner import extract_report_metadata, scan_and_index


class ReportService:
    def __init__(self, *, reports_dir: Path, db: ReportsDB, logger: logging.Logger | None = None):
        self.reports_dir = reports_dir.resolve()
        self.db = db
        self.logger = logger or logging.getLogger("drun.server")

    def rescan_reports(self) -> int:
        return scan_and_index(str(self.reports_dir), self.db, logger=self.logger)

    def list_reports(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        system_name: Optional[str] = None,
        environment: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        return self.db.list_reports(
            limit=limit,
            offset=offset,
            system_name=system_name,
            environment=environment,
            status=status,
        )

    def get_report(self, report_id: int) -> Optional[Dict[str, Any]]:
        return self.db.get_report(report_id)

    def get_report_by_file_name(self, file_name: str) -> Optional[Dict[str, Any]]:
        report = self.db.get_report_by_file_name(file_name)
        if report:
            return report

        try:
            file_path = self.resolve_report_file(file_name)
        except ValueError:
            return None

        if not file_path.exists():
            return None

        return extract_report_metadata(file_path, logger=self.logger)

    def update_notes(self, report_id: int, notes: str) -> bool:
        report = self.get_report(report_id)
        if not report:
            return False
        self.db.update_notes(report_id, notes)
        return True

    def delete_report(self, report_id: int) -> bool:
        report = self.get_report(report_id)
        if not report:
            return False
        self.db.delete_report(report_id)
        return True

    def get_stats(self) -> Dict[str, Any]:
        return self.db.get_stats()

    def resolve_report_file(self, file_name: str) -> Path:
        if ".." in file_name or "/" in file_name or "\\" in file_name:
            raise ValueError("Invalid file name")

        return self.reports_dir / file_name
