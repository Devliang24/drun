from __future__ import annotations

import sqlite3
import json
from pathlib import Path
from typing import List, Optional, Dict, Any


class ReportsDB:
    """SQLite database for test report metadata"""
    
    def __init__(self, db_path: str = "reports/reports.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()
    
    def get_conn(self):
        """Get database connection with Row factory"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_db(self):
        """Initialize database tables and indexes"""
        conn = self.get_conn()
        conn.execute('''
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_name TEXT UNIQUE NOT NULL,
                file_path TEXT NOT NULL,
                system_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                run_time TIMESTAMP,
                
                total_cases INTEGER DEFAULT 0,
                passed_cases INTEGER DEFAULT 0,
                failed_cases INTEGER DEFAULT 0,
                skipped_cases INTEGER DEFAULT 0,
                
                total_steps INTEGER DEFAULT 0,
                passed_steps INTEGER DEFAULT 0,
                failed_steps INTEGER DEFAULT 0,
                
                duration_ms REAL DEFAULT 0,
                
                tags TEXT,
                notes TEXT,
                environment TEXT,
                commit_sha TEXT,
                
                raw_summary TEXT,
                file_size INTEGER,
                indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_run_time ON reports(run_time DESC)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_system_name ON reports(system_name)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_environment ON reports(environment)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_failed_cases ON reports(failed_cases)')
        conn.commit()
        conn.close()
    
    def insert_report(self, report_data: Dict[str, Any]) -> int:
        """Insert or replace a report record"""
        conn = self.get_conn()
        cursor = conn.execute('''
            INSERT OR REPLACE INTO reports 
            (file_name, file_path, system_name, run_time,
             total_cases, passed_cases, failed_cases, skipped_cases,
             total_steps, passed_steps, failed_steps,
             duration_ms, tags, environment, raw_summary, file_size)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            report_data['file_name'],
            report_data['file_path'],
            report_data.get('system_name'),
            report_data.get('run_time'),
            report_data.get('total_cases', 0),
            report_data.get('passed_cases', 0),
            report_data.get('failed_cases', 0),
            report_data.get('skipped_cases', 0),
            report_data.get('total_steps', 0),
            report_data.get('passed_steps', 0),
            report_data.get('failed_steps', 0),
            report_data.get('duration_ms', 0),
            json.dumps(report_data.get('tags', [])),
            report_data.get('environment'),
            json.dumps(report_data.get('raw_summary', {})),
            report_data.get('file_size', 0),
        ))
        conn.commit()
        report_id = cursor.lastrowid
        conn.close()
        return report_id
    
    def list_reports(self, 
                     limit: int = 50, 
                     offset: int = 0,
                     system_name: Optional[str] = None,
                     environment: Optional[str] = None,
                     status: Optional[str] = None) -> List[Dict]:
        """Query reports with optional filtering"""
        conn = self.get_conn()
        
        where_clauses = []
        params = []
        
        if system_name:
            where_clauses.append("system_name LIKE ?")
            params.append(f"%{system_name}%")
        
        if environment:
            where_clauses.append("environment = ?")
            params.append(environment)
        
        if status == "failed":
            where_clauses.append("failed_cases > 0")
        elif status == "passed":
            where_clauses.append("failed_cases = 0")
        
        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
        
        query = f'''
            SELECT * FROM reports 
            WHERE {where_sql}
            ORDER BY run_time DESC 
            LIMIT ? OFFSET ?
        '''
        params.extend([limit, offset])
        
        cursor = conn.execute(query, params)
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        # Parse JSON fields
        for r in results:
            r['tags'] = json.loads(r['tags']) if r['tags'] else []
            r['raw_summary'] = json.loads(r['raw_summary']) if r['raw_summary'] else {}
        
        return results
    
    def get_report(self, report_id: int) -> Optional[Dict]:
        """Get a single report by ID"""
        conn = self.get_conn()
        cursor = conn.execute('SELECT * FROM reports WHERE id = ?', (report_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            result = dict(row)
            result['tags'] = json.loads(result['tags']) if result['tags'] else []
            result['raw_summary'] = json.loads(result['raw_summary']) if result['raw_summary'] else {}
            return result
        return None
    
    def update_notes(self, report_id: int, notes: str):
        """Update report notes"""
        conn = self.get_conn()
        conn.execute('UPDATE reports SET notes = ? WHERE id = ?', (notes, report_id))
        conn.commit()
        conn.close()
    
    def delete_report(self, report_id: int):
        """Delete a report record"""
        conn = self.get_conn()
        conn.execute('DELETE FROM reports WHERE id = ?', (report_id,))
        conn.commit()
        conn.close()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get aggregate statistics"""
        conn = self.get_conn()
        cursor = conn.execute('''
            SELECT 
                COUNT(*) as total_reports,
                SUM(total_cases) as total_cases,
                SUM(passed_cases) as passed_cases,
                SUM(failed_cases) as failed_cases,
                AVG(duration_ms) as avg_duration_ms
            FROM reports
        ''')
        result = dict(cursor.fetchone())
        conn.close()
        return result
