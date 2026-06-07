"""Adapter: Docker profile sync + gateway control."""

import json
import os
import sqlite3
import subprocess
import time

from backend.core.ports import ProfileSync, GatewayController
from backend.core.entities import ServerInfo, LogEntry


class SqliteProfileSync(ProfileSync):
    def __init__(self, db_path: str, catalog_getter):
        self._db = db_path
        self._get_catalog = catalog_getter

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db, timeout=3)
        conn.execute("PRAGMA busy_timeout=3000")
        return conn

    def sync(self, enabled: set[str]) -> None:
        """Sync enabled servers into the Docker profile."""
        conn = self._connect()
        rows = conn.execute(
            "SELECT servers FROM working_set WHERE id='profile'"
        ).fetchall()
        profile = json.loads(rows[0][0]) if rows else []
        existing: set[str] = {
            s.get("snapshot", {}).get("server", {}).get("name", "").lower()
            for s in profile
        }
        kept = [
            s
            for s in profile
            if s.get("snapshot", {}).get("server", {}).get("name", "").lower()
            in {n.lower() for n in enabled}
        ]
        catalog = self._get_catalog()
        catalog_map: dict[str, ServerInfo] = {s.name.lower(): s for s in catalog}
        for name in enabled:
            if name.lower() not in existing:
                snap_info = catalog_map.get(name.lower())
                if snap_info:
                    entry = {
                        "type": "image",
                        "secrets": "default",
                        "tools": None,
                        "image": f"mcp/{name.lower()}@sha256:latest",
                        "catalog_ref": "mcp/docker-mcp-catalog:latest",
                        "snapshot": {
                            "server": {
                                "name": name,
                                "type": "server",
                                "image": f"mcp/{name.lower()}",
                                "description": snap_info.desc,
                                "title": snap_info.title,
                                "secrets": [
                                    {
                                        "name": f"{name.lower()}.api_key",
                                        "env": f"{name.upper()}_API_KEY",
                                    }
                                ]
                                if snap_info.secrets
                                else [],
                                "remote": {},
                            }
                        },
                    }
                    kept.append(entry)
        conn.execute(
            "UPDATE working_set SET servers=? WHERE id='profile'",
            (json.dumps(kept),),
        )
        conn.commit()
        conn.close()


class SubprocessGateway(GatewayController):
    LOG = "/tmp/gateway.log"

    def _run_gateway(self) -> None:
        os.system(
            "(export MCP_GATEWAY_AUTH_TOKEN=mcp-local-token; "
            "nohup docker mcp gateway run --profile profile "
            "--transport sse --port 3099 --long-lived > /tmp/gateway.log 2>&1 &)"
        )

    def restart(self) -> bool:
        import platform as _platform
        subprocess.run(
            ["pkill", "-9", "-f", "docker mcp gateway run"], capture_output=True
        )
        self._run_gateway()
        macos = _platform.system() == "Darwin"
        for _ in range(30):
            try:
                if macos:
                    r = subprocess.run(
                        ["lsof", "-i", ":3099", "-P", "-n"],
                        capture_output=True, text=True, timeout=5
                    )
                    if "LISTEN" in r.stdout:
                        return True
                else:
                    r = subprocess.run(
                        ["ss", "-tlnp"], capture_output=True, text=True
                    )
                    if "3099" in r.stdout:
                        return True
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass
            time.sleep(0.5)
        return False

    def restart_async(self) -> None:
        subprocess.run(
            ["pkill", "-9", "-f", "docker mcp gateway run"], capture_output=True
        )
        self._run_gateway()

    def recent_logs(self, n: int = 5) -> list[str]:
        try:
            with open(self.LOG) as f:
                lines = [l for l in f.read().split("\n") if l.strip()]
            return lines[-n:]
        except (FileNotFoundError, OSError):
            return []

    def get_logs(self) -> list[LogEntry]:
        try:
            with open(self.LOG) as f:
                lines = [l for l in f.read().split("\n") if l.strip()]
            
            logs = []
            for line in lines:
                level = "INFO"
                if line.startswith("Warning:"):
                    level = "WARN"
                elif line.startswith("Error:"):
                    level = "ERROR"
                elif "DEBUG" in line.upper(): 
                    level = "DEBUG"
                
                logs.append(LogEntry(level=level, message=line, timestamp=""))
            return logs
        except (FileNotFoundError, OSError):
            return []
