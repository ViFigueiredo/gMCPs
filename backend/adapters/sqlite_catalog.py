"""Adapter: SQLite catalog repository."""

import json
import sqlite3

from backend.core.entities import ServerInfo
from backend.core.ports import CatalogRepository


class SqliteCatalogRepo(CatalogRepository):
    def __init__(self, db_path: str):
        self._db = db_path

    def list_all(self) -> list[ServerInfo]:
        try:
            conn = sqlite3.connect(self._db, timeout=10)
            rows = conn.execute(
                "SELECT snapshot FROM catalog_server ORDER BY json_extract(snapshot,'$.server.name')"
            ).fetchall()
            conn.close()
        except sqlite3.OperationalError:
            return []
        out = []
        for (s,) in rows:
            snap = json.loads(s).get("server", {})
            name = snap.get("name")
            if name:
                meta = snap.get("metadata", {}) or {}
                out.append(
                    ServerInfo(
                        name=name,
                        title=snap.get("title", ""),
                        desc=snap.get("description", ""),
                        icon=snap.get("icon") or meta.get("icon", ""),
                        category=meta.get("category", ""),
                        secrets=len(snap.get("secrets", [])) > 0,
                    )
                )
        return out
