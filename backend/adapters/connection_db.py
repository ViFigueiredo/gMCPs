"""Adapter: persists container connection history in SQLite."""

import json
import os
import sqlite3
import subprocess
from datetime import datetime, timezone

from backend.core.entities import ContainerRecord


DB_PATH = os.path.expanduser("~/.config/gmcp/connections.db")
RECENT_SECONDS = 86400 * 7  # Keep 7 days of history by default


def _ensure_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS connections (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            agent       TEXT NOT NULL DEFAULT 'Gateway',
            mcp_name    TEXT NOT NULL,
            container_id TEXT NOT NULL DEFAULT '-',
            container_name TEXT NOT NULL DEFAULT '-',
            started_at  TEXT NOT NULL,
            ended_at    TEXT,
            status      TEXT NOT NULL DEFAULT 'stopped',
            inserted_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_conn_mcp ON connections(mcp_name)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_conn_started ON connections(started_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_conn_inserted ON connections(inserted_at)")
    conn.commit()
    return conn


def persist_records(records: list[ContainerRecord]) -> None:
    """Append connection records. Each call to list_connections adds new rows,
    preserving history across gateway restarts."""
    if not records:
        return
    db = _ensure_db()
    # Dedup within this batch: use (mcp_name, container_id, started_at) as logical key
    seen = set()
    for rec in records:
        key = (rec.mcp_name, rec.container_id, rec.started_at)
        if key in seen:
            continue
        seen.add(key)
        # Check if an identical record already exists (same mcp+container+started_at)
        existing = db.execute(
            "SELECT COUNT(*) FROM connections WHERE mcp_name=? AND container_id=? AND started_at=?",
            (rec.mcp_name, rec.container_id, rec.started_at)
        ).fetchone()[0]
        if existing > 0:
            continue
        try:
            db.execute(
                """INSERT INTO connections
                   (agent, mcp_name, container_id, container_name, started_at, ended_at, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (rec.agent, rec.mcp_name, rec.container_id, rec.container_name,
                 rec.started_at, rec.ended_at or "", rec.status)
            )
        except sqlite3.Error:
            pass
    db.commit()
    db.close()


def load_history(
    mcp_filter: list[str] | None = None,
    date_start: str | None = None,
    date_end: str | None = None,
) -> list[ContainerRecord]:
    """Load persisted connection history with optional filters."""
    db = _ensure_db()
    query = "SELECT agent, mcp_name, container_id, container_name, started_at, ended_at, status FROM connections WHERE 1=1"
    params: list = []
    if mcp_filter:
        placeholders = ",".join("?" for _ in mcp_filter)
        query += f" AND mcp_name IN ({placeholders})"
        params.extend(mcp_filter)
    if date_start:
        query += " AND started_at >= ?"
        params.append(date_start)
    if date_end:
        query += " AND started_at <= ?"
        params.append(date_end)
    query += " ORDER BY started_at DESC"

    rows = db.execute(query, params).fetchall()
    db.close()

    return [
        ContainerRecord(
            agent=row[0],
            mcp_name=row[1],
            container_id=row[2],
            container_name=row[3],
            started_at=row[4],
            ended_at=row[5] if row[5] else None,
            status=row[6],
        )
        for row in rows
    ]


def remove_active(mcp_names: list[str] | None = None) -> int:
    """Remove active entries so next list_connections re-persists current state."""
    db = _ensure_db()
    query = "DELETE FROM connections WHERE status='active'"
    params: list = []
    if mcp_names:
        placeholders = ",".join("?" for _ in mcp_names)
        query += f" AND mcp_name IN ({placeholders})"
        params.extend(mcp_names)
    removed = db.execute(query, params).rowcount
    db.commit()
    db.close()
    return removed


def _parse_docker_time(t: str) -> str:
    t = t.replace("Z", "").strip()
    for fmt in ["%Y-%m-%d %H:%M:%S %z %Z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"]:
        try:
            dt = datetime.strptime(t[:25], fmt) if len(t) > 25 else datetime.strptime(t, fmt)
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            continue
    return t
