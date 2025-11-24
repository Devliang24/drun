from __future__ import annotations

import re
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional


def extract_report_metadata(html_file: Path) -> Optional[Dict[str, Any]]:
    """Extract metadata from HTML report file"""
    try:
        text = html_file.read_text(encoding="utf-8")
        
        # Extract window.__REPORT_DATA__
        match = re.search(r'window\.__REPORT_DATA__\s*=\s*({.+?});', text, re.DOTALL)
        if match:
            data = json.loads(match.group(1))
            summary = data.get("summary", {})
            
            # Extract timestamp from filename
            run_time = None
            ts_match = re.search(r'(\d{8})-(\d{6})', html_file.name)
            if ts_match:
                try:
                    run_time = datetime.strptime(
                        f"{ts_match.group(1)}-{ts_match.group(2)}", 
                        "%Y%m%d-%H%M%S"
                    ).isoformat()
                except Exception:
                    pass
            
            # If no timestamp in filename, use file modification time
            if not run_time:
                run_time = datetime.fromtimestamp(html_file.stat().st_mtime).isoformat()
            
            return {
                'file_name': html_file.name,
                'file_path': str(html_file),
                'system_name': summary.get('system_name', 'Unknown'),
                'run_time': run_time,
                'total_cases': summary.get('total', 0),
                'passed_cases': summary.get('passed', 0),
                'failed_cases': summary.get('failed', 0),
                'skipped_cases': summary.get('skipped', 0),
                'total_steps': summary.get('steps_total', 0),
                'passed_steps': summary.get('steps_passed', 0),
                'failed_steps': summary.get('steps_failed', 0),
                'duration_ms': summary.get('duration_ms', 0),
                'environment': summary.get('environment'),
                'raw_summary': summary,
                'file_size': html_file.stat().st_size,
            }
    except Exception as e:
        print(f"Failed to parse {html_file}: {e}")
    
    return None


def scan_and_index(reports_dir: str, db) -> int:
    """Scan reports directory and index all reports"""
    reports_path = Path(reports_dir)
    if not reports_path.exists():
        print(f"[SCANNER] Reports directory not found: {reports_dir}")
        return 0
    
    count = 0
    for html_file in reports_path.glob("*.html"):
        if html_file.name == "index.html":
            continue
        
        metadata = extract_report_metadata(html_file)
        if metadata:
            try:
                db.insert_report(metadata)
                count += 1
            except Exception as e:
                print(f"[SCANNER] Failed to index {html_file.name}: {e}")
    
    return count
