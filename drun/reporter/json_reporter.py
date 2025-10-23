from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from drun.models.report import RunReport


def write_json(report: RunReport, outfile: str | Path) -> None:
    p = Path(outfile)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(report.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8")
