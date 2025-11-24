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
        
        # Try to extract window.__REPORT_DATA__ (new format)
        match = re.search(r'window\.__REPORT_DATA__\s*=\s*({.+?});', text, re.DOTALL)
        if match:
            data = json.loads(match.group(1))
            summary = data.get("summary", {})
        else:
            # Fallback: parse embedded HTML data (old format)
            summary = {}
            
            # Extract system name from title
            title_match = re.search(r'<h1>(.+?)\s+测试报告</h1>', text)
            if title_match:
                summary['system_name'] = title_match.group(1).strip()
            
            # Extract statistics from badge divs
            total_match = re.search(r"badge-label'>用例总数</span><span class='badge-value'>(\d+)</span>", text)
            passed_match = re.search(r"badge-label'>通过</span><span class='badge-value'>(\d+)</span>", text)
            failed_match = re.search(r"badge-label'>失败</span><span class='badge-value'>(\d+)</span>", text)
            skipped_match = re.search(r"badge-label'>跳过</span><span class='badge-value'>(\d+)</span>", text)
            duration_match = re.search(r"badge-label'>耗时</span><span class='badge-value'>([\d.]+)<span", text)
            
            if total_match:
                summary['total'] = int(total_match.group(1))
            if passed_match:
                summary['passed'] = int(passed_match.group(1))
            if failed_match:
                summary['failed'] = int(failed_match.group(1))
            if skipped_match:
                summary['skipped'] = int(skipped_match.group(1))
            if duration_match:
                summary['duration_ms'] = float(duration_match.group(1))
        
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
        reports_path.mkdir(parents=True, exist_ok=True)
        return 0
    
    count = 0
    for html_file in reports_path.glob("*.html"):
        if html_file.name == "index.html":
            continue
        
        try:
            metadata = extract_report_metadata(html_file)
            if metadata:
                db.insert_report(metadata)
                count += 1
                print(f"[SCANNER] Indexed: {html_file.name}")
        except Exception as e:
            print(f"[SCANNER] Failed to index {html_file.name}: {e}")
    
    return count
