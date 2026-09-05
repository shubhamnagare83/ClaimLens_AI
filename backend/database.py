"""
ClaimLens AI — Database Layer (SQLite)
"""
import sqlite3
import json
import os
from datetime import datetime
from pathlib import Path
from backend.config import DATABASE_PATH, DATABASE_DIR


def get_connection():
    """Get a SQLite connection with row factory."""
    DATABASE_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DATABASE_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


# Global connection
_conn = None

def get_db():
    global _conn
    if _conn is None:
        _conn = get_connection()
    return _conn


def init_database():
    """Create all tables."""
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS claims (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            claim_id TEXT UNIQUE NOT NULL,
            policy_number TEXT NOT NULL,
            customer_name TEXT NOT NULL,
            vehicle_type TEXT NOT NULL,
            vehicle_registration TEXT NOT NULL,
            vehicle_make TEXT DEFAULT '',
            incident_type TEXT NOT NULL,
            incident_date TEXT NOT NULL,
            incident_time TEXT DEFAULT '',
            incident_location TEXT DEFAULT '',
            claim_date TEXT NOT NULL,
            policy_start_date TEXT NOT NULL,
            policy_end_date TEXT NOT NULL,
            idv REAL DEFAULT 0,
            repair_estimate REAL DEFAULT 0,
            deductible REAL DEFAULT 0,
            status TEXT DEFAULT 'PENDING',
            scenario_type TEXT DEFAULT '',
            expected_outcome TEXT DEFAULT '',
            difficulty TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            claim_id TEXT NOT NULL,
            document_type TEXT NOT NULL,
            filename TEXT NOT NULL,
            content TEXT DEFAULT '',
            uploaded_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (claim_id) REFERENCES claims(claim_id)
        );

        CREATE TABLE IF NOT EXISTS extracted_facts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            claim_id TEXT NOT NULL,
            field_name TEXT NOT NULL,
            field_value TEXT DEFAULT '',
            source_document TEXT DEFAULT '',
            source_page INTEGER DEFAULT 1,
            evidence TEXT DEFAULT '',
            confidence REAL DEFAULT 0.0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (claim_id) REFERENCES claims(claim_id)
        );

        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            claim_id TEXT NOT NULL,
            version INTEGER DEFAULT 1,
            recommendation TEXT DEFAULT 'PENDING',
            confidence TEXT DEFAULT 'LOW',
            evidence_score REAL DEFAULT 0,
            human_review_required INTEGER DEFAULT 1,
            report_json TEXT DEFAULT '{}',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (claim_id) REFERENCES claims(claim_id)
        );

        CREATE TABLE IF NOT EXISTS findings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            review_id INTEGER NOT NULL,
            claim_id TEXT NOT NULL,
            finding_type TEXT NOT NULL,
            severity TEXT DEFAULT 'LOW',
            title TEXT DEFAULT '',
            description TEXT DEFAULT '',
            policy_clause TEXT DEFAULT '',
            source_document TEXT DEFAULT '',
            source_page INTEGER DEFAULT 1,
            evidence TEXT DEFAULT '',
            confidence TEXT DEFAULT 'LOW',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (review_id) REFERENCES reviews(id),
            FOREIGN KEY (claim_id) REFERENCES claims(claim_id)
        );

        CREATE TABLE IF NOT EXISTS citations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            finding_id INTEGER,
            claim_id TEXT NOT NULL,
            source_document TEXT DEFAULT '',
            page INTEGER DEFAULT 1,
            evidence_snippet TEXT DEFAULT '',
            policy_clause TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (claim_id) REFERENCES claims(claim_id)
        );

        CREATE TABLE IF NOT EXISTS audit_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            claim_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            description TEXT DEFAULT '',
            details TEXT DEFAULT '{}',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (claim_id) REFERENCES claims(claim_id)
        );

        CREATE TABLE IF NOT EXISTS simulations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            claim_id TEXT NOT NULL,
            parameters TEXT DEFAULT '{}',
            result TEXT DEFAULT '{}',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (claim_id) REFERENCES claims(claim_id)
        );

        CREATE INDEX IF NOT EXISTS idx_claims_claim_id ON claims(claim_id);
        CREATE INDEX IF NOT EXISTS idx_documents_claim_id ON documents(claim_id);
        CREATE INDEX IF NOT EXISTS idx_reviews_claim_id ON reviews(claim_id);
        CREATE INDEX IF NOT EXISTS idx_findings_claim_id ON findings(claim_id);
        CREATE INDEX IF NOT EXISTS idx_audit_claim_id ON audit_events(claim_id);
    """)
    conn.commit()
    return True


# ── CRUD helpers ────────────────────────────────────────

def insert_claim(claim_data: dict) -> str:
    conn = get_db()
    try:
        conn.execute("""
            INSERT OR REPLACE INTO claims
            (claim_id, policy_number, customer_name, vehicle_type, vehicle_registration,
             vehicle_make, incident_type, incident_date, incident_time, incident_location,
             claim_date, policy_start_date, policy_end_date, idv, repair_estimate,
             deductible, status, scenario_type, expected_outcome, difficulty)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            claim_data.get('claim_id'), claim_data.get('policy_number'),
            claim_data.get('customer_name'), claim_data.get('vehicle_type'),
            claim_data.get('vehicle_registration'), claim_data.get('vehicle_make', ''),
            claim_data.get('incident_type'), claim_data.get('incident_date'),
            claim_data.get('incident_time', ''), claim_data.get('incident_location', ''),
            claim_data.get('claim_date'), claim_data.get('policy_start_date'),
            claim_data.get('policy_end_date'), claim_data.get('idv', 0),
            claim_data.get('repair_estimate', 0), claim_data.get('deductible', 0),
            claim_data.get('status', 'PENDING'),
            claim_data.get('scenario_type', ''),
            claim_data.get('expected_outcome', ''),
            claim_data.get('difficulty', ''),
        ))
        conn.commit()
        return claim_data['claim_id']
    except Exception as e:
        print(f"Error inserting claim: {e}")
        return None


def insert_document(claim_id: str, doc_type: str, filename: str, content: str) -> int:
    conn = get_db()
    cursor = conn.execute("""
        INSERT INTO documents (claim_id, document_type, filename, content)
        VALUES (?, ?, ?, ?)
    """, (claim_id, doc_type, filename, content))
    conn.commit()
    return cursor.lastrowid


def get_claim(claim_id: str) -> dict:
    conn = get_db()
    row = conn.execute("SELECT * FROM claims WHERE claim_id = ?", (claim_id,)).fetchone()
    if row:
        return dict(row)
    return None


def get_all_claims() -> list:
    conn = get_db()
    rows = conn.execute("SELECT * FROM claims ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]


def update_claim(claim_id: str, updates: dict) -> bool:
    conn = get_db()
    allowed_fields = [
        'customer_name', 'vehicle_type', 'vehicle_registration', 'vehicle_make',
        'incident_type', 'incident_date', 'incident_time', 'incident_location',
        'claim_date', 'policy_start_date', 'policy_end_date', 'idv',
        'repair_estimate', 'deductible', 'status', 'scenario_type', 'expected_outcome'
    ]
    set_clauses = []
    params = []
    for k, v in updates.items():
        if k in allowed_fields and v is not None:
            set_clauses.append(f"{k} = ?")
            params.append(v)
    if not set_clauses:
        return False
    set_clauses.append("updated_at = ?")
    params.append(datetime.now().isoformat())
    params.append(claim_id)

    query = f"UPDATE claims SET {', '.join(set_clauses)} WHERE claim_id = ?"
    conn.execute(query, params)
    conn.commit()
    return True


def delete_claim(claim_id: str) -> bool:
    conn = get_db()
    conn.execute("DELETE FROM simulations WHERE claim_id = ?", (claim_id,))
    conn.execute("DELETE FROM audit_events WHERE claim_id = ?", (claim_id,))
    conn.execute("DELETE FROM citations WHERE claim_id = ?", (claim_id,))
    conn.execute("DELETE FROM findings WHERE claim_id = ?", (claim_id,))
    conn.execute("DELETE FROM reviews WHERE claim_id = ?", (claim_id,))
    conn.execute("DELETE FROM documents WHERE claim_id = ?", (claim_id,))
    cursor = conn.execute("DELETE FROM claims WHERE claim_id = ?", (claim_id,))
    conn.commit()
    return cursor.rowcount > 0



def get_claim_documents(claim_id: str) -> list:
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM documents WHERE claim_id = ? ORDER BY uploaded_at", (claim_id,)
    ).fetchall()
    return [dict(r) for r in rows]


def insert_review(claim_id: str, version: int, recommendation: str, confidence: str,
                  evidence_score: float, report_json: dict) -> int:
    conn = get_db()
    cursor = conn.execute("""
        INSERT INTO reviews (claim_id, version, recommendation, confidence,
                            evidence_score, human_review_required, report_json)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (claim_id, version, recommendation, confidence, evidence_score,
          1, json.dumps(report_json)))
    conn.commit()
    # Update claim status
    conn.execute("UPDATE claims SET status = ?, updated_at = ? WHERE claim_id = ?",
                 (recommendation, datetime.now().isoformat(), claim_id))
    conn.commit()
    return cursor.lastrowid


def get_latest_review(claim_id: str) -> dict:
    conn = get_db()
    row = conn.execute("""
        SELECT * FROM reviews WHERE claim_id = ? ORDER BY version DESC LIMIT 1
    """, (claim_id,)).fetchone()
    if row:
        r = dict(row)
        r['report_json'] = json.loads(r.get('report_json', '{}'))
        return r
    return None


def get_review_versions(claim_id: str) -> list:
    conn = get_db()
    rows = conn.execute("""
        SELECT * FROM reviews WHERE claim_id = ? ORDER BY version ASC
    """, (claim_id,)).fetchall()
    results = []
    for r in rows:
        d = dict(r)
        d['report_json'] = json.loads(d.get('report_json', '{}'))
        results.append(d)
    return results


def insert_finding(review_id: int, claim_id: str, finding_type: str, severity: str,
                   title: str, description: str, policy_clause: str = '',
                   source_document: str = '', source_page: int = 1,
                   evidence: str = '', confidence: str = 'LOW') -> int:
    conn = get_db()
    cursor = conn.execute("""
        INSERT INTO findings (review_id, claim_id, finding_type, severity, title,
                             description, policy_clause, source_document, source_page,
                             evidence, confidence)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (review_id, claim_id, finding_type, severity, title, description,
          policy_clause, source_document, source_page, evidence, confidence))
    conn.commit()
    return cursor.lastrowid


def get_findings(claim_id: str) -> list:
    conn = get_db()
    rows = conn.execute("""
        SELECT * FROM findings WHERE claim_id = ? ORDER BY created_at
    """, (claim_id,)).fetchall()
    return [dict(r) for r in rows]


def insert_audit_event(claim_id: str, event_type: str, description: str, details: dict = None):
    conn = get_db()
    conn.execute("""
        INSERT INTO audit_events (claim_id, event_type, description, details)
        VALUES (?, ?, ?, ?)
    """, (claim_id, event_type, description, json.dumps(details or {})))
    conn.commit()


def get_audit_trail(claim_id: str) -> list:
    conn = get_db()
    rows = conn.execute("""
        SELECT * FROM audit_events WHERE claim_id = ? ORDER BY created_at ASC
    """, (claim_id,)).fetchall()
    results = []
    for r in rows:
        d = dict(r)
        try:
            d['details'] = json.loads(d.get('details', '{}'))
        except:
            d['details'] = {}
        results.append(d)
    return results


def insert_simulation(claim_id: str, parameters: dict, result: dict) -> int:
    conn = get_db()
    cursor = conn.execute("""
        INSERT INTO simulations (claim_id, parameters, result)
        VALUES (?, ?, ?)
    """, (claim_id, json.dumps(parameters), json.dumps(result)))
    conn.commit()
    return cursor.lastrowid


def get_dashboard_stats() -> dict:
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) as c FROM claims").fetchone()['c']
    stats = {
        'total_claims': total,
        'pending': conn.execute("SELECT COUNT(*) as c FROM claims WHERE status='PENDING'").fetchone()['c'],
        'approved': conn.execute("SELECT COUNT(*) as c FROM claims WHERE status='APPROVE'").fetchone()['c'],
        'rejected': conn.execute("SELECT COUNT(*) as c FROM claims WHERE status='REJECT'").fetchone()['c'],
        'request_info': conn.execute("SELECT COUNT(*) as c FROM claims WHERE status='REQUEST_INFORMATION'").fetchone()['c'],
        'escalated': conn.execute("SELECT COUNT(*) as c FROM claims WHERE status='ESCALATE'").fetchone()['c'],
    }

    # By type
    stats['by_incident_type'] = {}
    for row in conn.execute("SELECT incident_type, COUNT(*) as c FROM claims GROUP BY incident_type").fetchall():
        stats['by_incident_type'][row['incident_type']] = row['c']

    stats['by_vehicle_type'] = {}
    for row in conn.execute("SELECT vehicle_type, COUNT(*) as c FROM claims GROUP BY vehicle_type").fetchall():
        stats['by_vehicle_type'][row['vehicle_type']] = row['c']

    # Average evidence score from reviews
    avg_row = conn.execute("SELECT AVG(evidence_score) as avg_score FROM reviews WHERE evidence_score > 0").fetchone()
    stats['avg_evidence_score'] = round(avg_row['avg_score'] or 0, 1)

    sums = conn.execute("SELECT SUM(repair_estimate) as tot_est, SUM(idv) as tot_idv FROM claims").fetchone()
    stats['total_repair_estimates'] = round(sums['tot_est'] or 0, 2)
    stats['total_idv'] = round(sums['tot_idv'] or 0, 2)

    return stats


def get_extracted_facts(claim_id: str) -> list:
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM extracted_facts WHERE claim_id = ? ORDER BY field_name",
        (claim_id,)
    ).fetchall()
    return [dict(r) for r in rows]


def insert_extracted_fact(claim_id: str, field_name: str, field_value: str,
                          source_document: str, evidence: str, confidence: float):
    conn = get_db()
    conn.execute("""
        INSERT INTO extracted_facts (claim_id, field_name, field_value,
                                     source_document, evidence, confidence)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (claim_id, field_name, field_value, source_document, evidence, confidence))
    conn.commit()
