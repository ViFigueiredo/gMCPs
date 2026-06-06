"""Adapter: SQLite catalog repository."""

import json
import sqlite3

from backend.core.entities import ServerInfo
from backend.core.ports import CatalogRepository


class SqliteCatalogRepo(CatalogRepository):
    def __init__(self, db_path: str):
        self._db = db_path

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db, timeout=15)
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def list_all(self) -> list[ServerInfo]:
        conn = self._connect()
        rows = conn.execute(
            "SELECT snapshot FROM catalog_server ORDER BY json_extract(snapshot,'$.server.name')"
        ).fetchall()
        conn.close()
        out = []
        for (s,) in rows:
            snap = json.loads(s).get("server", {})
            name = snap.get("name")
            if name:
                out.append(
                    ServerInfo(
                        name=name,
                        title=snap.get("title", ""),
                        desc=snap.get("description", ""),
                        secrets=len(snap.get("secrets", [])) > 0,
                    )
                )
        return out
