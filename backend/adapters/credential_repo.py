"""SQLite adapter for encrypted credential storage."""

import sqlite3
from typing import Optional
from backend.core.ports import CredentialRepository


class SqliteCredentialRepo(CredentialRepository):
    """Persists encrypted credentials in the catalog SQLite database."""

    def __init__(self, db_path: str):
        self._db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS credential_store (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    server_name TEXT    NOT NULL,
                    key         TEXT    NOT NULL,
                    value       TEXT    NOT NULL,
                    updated_at  TEXT    NOT NULL DEFAULT (datetime('now')),
                    UNIQUE(server_name, key)
                )
            """)

    def upsert(self, server: str, key: str, value: str) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """INSERT INTO credential_store (server_name, key, value, updated_at)
                   VALUES (?, ?, ?, datetime('now'))
                   ON CONFLICT(server_name, key) DO UPDATE SET
                       value=excluded.value,
                       updated_at=datetime('now')""",
                (server, key, value),
            )

    def get(self, server: str, key: str) -> Optional[str]:
        with sqlite3.connect(self._db_path) as conn:
            row = conn.execute(
                "SELECT value FROM credential_store WHERE server_name=? AND key=?",
                (server, key),
            ).fetchone()
            return row[0] if row else None

    def list_keys(self, server: str) -> list[str]:
        with sqlite3.connect(self._db_path) as conn:
            rows = conn.execute(
                "SELECT key FROM credential_store WHERE server_name=?",
                (server,),
            ).fetchall()
            return [r[0] for r in rows]

    def list_servers(self) -> list[str]:
        with sqlite3.connect(self._db_path) as conn:
            rows = conn.execute(
                "SELECT DISTINCT server_name FROM credential_store"
            ).fetchall()
            return [r[0] for r in rows]

    def list_all(self) -> list[tuple[str, str, bool]]:
        with sqlite3.connect(self._db_path) as conn:
            rows = conn.execute(
                "SELECT server_name, key, 1 FROM credential_store"
            ).fetchall()
            return rows

    def delete(self, server: str, key: str) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                "DELETE FROM credential_store WHERE server_name=? AND key=?",
                (server, key),
            )