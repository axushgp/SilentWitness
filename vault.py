from __future__ import annotations

import json
import sqlite3
from datetime import datetime

from utils import VAULT_PATH


def init_db() -> None:
    with sqlite3.connect(VAULT_PATH) as con:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS changes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service TEXT NOT NULL,
                detected_at TEXT NOT NULL,
                severity TEXT NOT NULL,
                summary TEXT,
                deadline TEXT,
                risk_score INTEGER,
                data_score INTEGER,
                financial_score INTEGER,
                ip_score INTEGER,
                continuity_score INTEGER,
                primary_driver TEXT,
                dpdp_flags TEXT,
                diff_text TEXT,
                docx_path TEXT,
                mike_clauses TEXT
            )
            """
        )
        _ensure_column(con, "changes", "mike_clauses", "TEXT")
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS contracts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                uploaded_at TEXT NOT NULL,
                uploaded_by TEXT,
                severity TEXT,
                summary TEXT,
                risk_score INTEGER,
                diff_text TEXT,
                report_path TEXT,
                clauses TEXT
            )
            """
        )
        _ensure_column(con, "contracts", "report_path", "TEXT")
        _ensure_column(con, "contracts", "clauses", "TEXT")
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS heartbeat_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                crawled INTEGER DEFAULT 0,
                failed INTEGER DEFAULT 0,
                diffs INTEGER DEFAULT 0,
                alerts INTEGER DEFAULT 0,
                status TEXT NOT NULL,
                details TEXT
            )
            """
        )
        con.execute(
            """
            UPDATE heartbeat_runs
            SET status = 'interrupted', finished_at = COALESCE(finished_at, ?)
            WHERE status = 'running'
            """,
            (datetime.now().isoformat(timespec="seconds"),),
        )


def _ensure_column(con: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    columns = {row[1] for row in con.execute(f"PRAGMA table_info({table})")}
    if column not in columns:
        con.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def start_run() -> int:
    init_db()
    with sqlite3.connect(VAULT_PATH) as con:
        cur = con.execute(
            "INSERT INTO heartbeat_runs (started_at, status) VALUES (?, ?)",
            (datetime.now().isoformat(timespec="seconds"), "running"),
        )
        return int(cur.lastrowid)


def finish_run(run_id: int, crawled: int, failed: int, diffs: int, alerts: int, status: str, details: dict) -> None:
    init_db()
    with sqlite3.connect(VAULT_PATH) as con:
        con.execute(
            """
            UPDATE heartbeat_runs
            SET finished_at = ?, crawled = ?, failed = ?, diffs = ?, alerts = ?, status = ?, details = ?
            WHERE id = ?
            """,
            (
                datetime.now().isoformat(timespec="seconds"),
                crawled,
                failed,
                diffs,
                alerts,
                status,
                json.dumps(details),
                run_id,
            ),
        )


def add_change(
    service: str,
    severity: str,
    summary: str,
    deadline: str | None,
    risk,
    dpdp_flags: list[dict[str, str]],
    diff_text: str,
    docx_path: str | None = None,
    mike_clauses: list[dict[str, str]] | None = None,
) -> int:
    init_db()
    with sqlite3.connect(VAULT_PATH) as con:
        existing = con.execute(
            """
            SELECT id FROM changes
            WHERE service = ? AND severity = ? AND diff_text = ?
            ORDER BY id DESC LIMIT 1
            """,
            (service, severity, diff_text),
        ).fetchone()
        if existing:
            con.execute(
                """
                UPDATE changes
                SET docx_path = COALESCE(NULLIF(?, ''), docx_path),
                    mike_clauses = CASE WHEN ? != '[]' THEN ? ELSE mike_clauses END
                WHERE id = ?
                """,
                (
                    docx_path,
                    json.dumps(mike_clauses or []),
                    json.dumps(mike_clauses or []),
                    int(existing[0]),
                ),
            )
            return int(existing[0])

        cur = con.execute(
            """
            INSERT INTO changes (
                service, detected_at, severity, summary, deadline, risk_score,
                data_score, financial_score, ip_score, continuity_score,
                primary_driver, dpdp_flags, diff_text, docx_path, mike_clauses
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                service,
                datetime.now().isoformat(timespec="seconds"),
                severity,
                summary,
                deadline,
                risk.total_score,
                risk.data_score,
                risk.financial_score,
                risk.ip_score,
                risk.continuity_score,
                risk.primary_driver,
                json.dumps(dpdp_flags),
                diff_text,
                docx_path,
                json.dumps(mike_clauses or []),
            ),
        )
        return int(cur.lastrowid)


def recent_changes(limit: int = 5) -> list[sqlite3.Row]:
    init_db()
    con = sqlite3.connect(VAULT_PATH)
    con.row_factory = sqlite3.Row
    return list(
        con.execute(
            "SELECT * FROM changes ORDER BY detected_at DESC, id DESC LIMIT ?",
            (limit,),
        )
    )


def all_changes(limit: int = 50) -> list[sqlite3.Row]:
    init_db()
    con = sqlite3.connect(VAULT_PATH)
    con.row_factory = sqlite3.Row
    return list(
        con.execute(
            "SELECT * FROM changes ORDER BY detected_at DESC, id DESC LIMIT ?",
            (limit,),
        )
    )


def recent_runs(limit: int = 10) -> list[sqlite3.Row]:
    init_db()
    con = sqlite3.connect(VAULT_PATH)
    con.row_factory = sqlite3.Row
    return list(
        con.execute(
            "SELECT * FROM heartbeat_runs ORDER BY started_at DESC, id DESC LIMIT ?",
            (limit,),
        )
    )


def add_contract(filename: str, uploaded_by: str | None, severity: str, summary: str, risk_score: int, diff_text: str, report_path: str | None, clauses: list[dict[str, str]]) -> int:
    init_db()
    with sqlite3.connect(VAULT_PATH) as con:
        cur = con.execute(
            """
            INSERT INTO contracts (
                filename, uploaded_at, uploaded_by, severity, summary,
                risk_score, diff_text, report_path, clauses
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                filename,
                datetime.now().isoformat(timespec="seconds"),
                uploaded_by,
                severity,
                summary,
                risk_score,
                diff_text,
                report_path,
                json.dumps(clauses),
            ),
        )
        return int(cur.lastrowid)


def recent_contracts(limit: int = 20) -> list[sqlite3.Row]:
    init_db()
    con = sqlite3.connect(VAULT_PATH)
    con.row_factory = sqlite3.Row
    return list(
        con.execute(
            "SELECT * FROM contracts ORDER BY uploaded_at DESC, id DESC LIMIT ?",
            (limit,),
        )
    )


def stats() -> dict[str, int]:
    init_db()
    with sqlite3.connect(VAULT_PATH) as con:
        total = con.execute("SELECT COUNT(*) FROM changes").fetchone()[0]
        critical = con.execute("SELECT COUNT(*) FROM changes WHERE severity='CRITICAL'").fetchone()[0]
        moderate = con.execute("SELECT COUNT(*) FROM changes WHERE severity='MODERATE'").fetchone()[0]
        contracts = con.execute("SELECT COUNT(*) FROM contracts").fetchone()[0]
        runs = con.execute("SELECT COUNT(*) FROM heartbeat_runs").fetchone()[0]
        alerts = con.execute("SELECT COALESCE(SUM(alerts), 0) FROM heartbeat_runs").fetchone()[0]
    return {"changes": total, "critical": critical, "moderate": moderate, "contracts": contracts, "runs": runs, "alerts": alerts}
