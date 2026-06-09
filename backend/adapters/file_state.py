"""Adapter: JSON file state repository."""

import json
import os

from backend.core.entities import GatewayState
from backend.core.ports import StateRepository


class FileStateRepo(StateRepository):
    def __init__(self, state_path: str, db_path: str = ""):
        self._path = state_path
        self._db = db_path  # fallback to bootstrap from profile

    def load(self) -> GatewayState:
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        try:
            with open(self._path) as f:
                data = json.load(f)
            return GatewayState(
                installed=data.get("installed", []),
                enabled=data.get("enabled", []),
                shared_servers=data.get("shared_servers", {}),
            )
        except (FileNotFoundError, json.JSONDecodeError):
            return self._bootstrap()

    def save(self, state: GatewayState) -> None:
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        with open(self._path, "w") as f:
            json.dump(
                {
                    "installed": state.installed,
                    "enabled": state.enabled,
                    "shared_servers": state.shared_servers,
                },
                f,
                indent=2,
            )

    def _bootstrap(self) -> GatewayState:
        """Create initial state from existing Docker profile."""
        if not self._db:
            return GatewayState()
        import sqlite3

        try:
            conn = sqlite3.connect(self._db)
            rows = conn.execute(
                "SELECT servers FROM working_set WHERE id='profile'"
            ).fetchall()
            conn.close()
            if rows:
                profile = json.loads(rows[0][0])
                names = [
                    s.get("snapshot", {}).get("server", {}).get("name")
                    for s in profile
                    if s.get("snapshot", {}).get("server", {}).get("name")
                ]
                state = GatewayState(installed=names[:], enabled=names[:])
                self.save(state)
                return state
        except Exception:
            pass
        return GatewayState()
