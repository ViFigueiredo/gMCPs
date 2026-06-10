import os
"""Adapter: reads MCP container connections from Docker, persists to SQLite."""

import json
import os
import re
import subprocess
from datetime import datetime, timezone

from backend.core.ports import ConnectionRepository
from backend.core.entities import ContainerRecord
from backend.adapters.connection_db import persist_records, load_history, remove_active


def _parse_mcp_name(image: str) -> str:
    m = re.match(r'mcp/([a-zA-Z0-9_.-]+)', image)
    if m:
        return m.group(1).lower()
    return image


def _detect_active_agents() -> dict[str, str]:
    """Returns {mcp_name: agent_name} for active connections to port 3099.
    Falls back to detecting known agent processes on the system."""
    import platform as _platform
    result: dict[str, str] = {}
    macos = _platform.system() == "Darwin"
    try:
        if macos:
            r = subprocess.run(
                ["lsof", "-i", ":3099", "-sTCP:ESTABLISHED", "-P", "-n"],
                capture_output=True, text=True, timeout=5
            )
            pids = set()
            for line in r.stdout.split("\n"):
                parts = line.split()
                if len(parts) >= 9 and parts[8] == "ESTABLISHED":
                    pids.add(parts[1])
        else:
            r = subprocess.run(
                ["ss", "-tlnp", "sport", "=:3099"],
                capture_output=True, text=True, timeout=5
            )
            r2 = subprocess.run(
                ["ss", "-tnp", "dport", "=:3099"],
                capture_output=True, text=True, timeout=5
            )
            combined = r.stdout + "\n" + r2.stdout
            pids = set()
            for line in combined.split("\n"):
                m = re.search(r'pid=(\d+)', line)
                if m:
                    pids.add(m.group(1))
        for pid in pids:
            try:
                if macos:
                    comm = subprocess.run(
                        ["ps", "-o", "comm=", "-p", pid],
                        capture_output=True, text=True, timeout=5
                    ).stdout.strip()
                else:
                    comm = open(f"/proc/{pid}/comm").read().strip()
                if comm:
                    result[str(pid)] = comm
            except (OSError, subprocess.TimeoutExpired):
                pass
    except (subprocess.TimeoutExpired, OSError):
        pass

    # Fallback: detect known agent processes
    if not result:
        known_agents = {
            "opencode": "OpenCode",
            "claude": "Claude Code",
            "codex": "Codex CLI",
            "kilo": "Kilo Code",
            "node": "Gateway",
        }
        try:
            r = subprocess.run(
                ["ps", "-eo", "pid,comm", "--no-headers"],
                capture_output=True, text=True, timeout=5
            )
            for line in r.stdout.strip().split("\n"):
                parts = line.strip().split(None, 1)
                if len(parts) == 2:
                    _, comm = parts
                    for binary, name in known_agents.items():
                        if binary in comm.lower():
                            result["fallback:" + binary] = name
                            break
        except (subprocess.TimeoutExpired, OSError):
            pass

    return result


class DockerConnectionRepo(ConnectionRepository):
    LOG = os.path.expanduser("~/.config/gmcp/gateway.log")

    def list_connections(
        self,
        mcp_filter: list[str] | None = None,
        date_start: str | None = None,
        date_end: str | None = None,
    ) -> list[ContainerRecord]:
        # Try Docker first
        docker_records: list[ContainerRecord] = []
        try:
            r = subprocess.run(
                ["docker", "ps", "-a", "--no-trunc", "--format", "{{json .}}"],
                capture_output=True, text=True, timeout=15
            )
            if r.returncode == 0:
                lines = [l for l in r.stdout.strip().split("\n") if l]
                agents = _detect_active_agents()
                for line in lines:
                    try:
                        c = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    image = c.get("Image", "")
                    if "mcp/" not in image.lower():
                        continue
                    mcp = _parse_mcp_name(image)
                    created = c.get("CreatedAt", "")
                    started = self._parse_docker_time(created)
                    status_raw = c.get("Status", "")
                    is_active = status_raw.startswith("Up")
                    status = "active" if is_active else "stopped"
                    agent = "Gateway"
                    if is_active:
                        agent = " / ".join(sorted(set(agents.values()))) if agents else "Desconhecido"
                    container_id = c.get("ID", "")[:12]
                    container_name = c.get("Names", "").replace("/", "")
                    ended = None
                    if not is_active:
                        try:
                            ir = subprocess.run(
                                ["docker", "inspect", container_id],
                                capture_output=True, text=True, timeout=10
                            )
                            if ir.returncode == 0:
                                info = json.loads(ir.stdout)
                                if info:
                                    finished = info[0].get("State", {}).get("FinishedAt", "")
                                    if finished and finished != "0001-01-01T00:00:00Z":
                                        ended = self._parse_docker_time(finished)
                        except (subprocess.TimeoutExpired, json.JSONDecodeError):
                            pass
                    docker_records.append(ContainerRecord(
                        agent=agent, mcp_name=mcp, container_id=container_id,
                        container_name=container_name, started_at=started,
                        ended_at=ended, status=status,
                    ))
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        # Also parse gateway log for servers that were started (transient containers)
        log_records = self._parse_log_entries()
        all_records = docker_records + log_records

        # Persist all to SQLite
        if all_records:
            try:
                persist_records(all_records)
            except Exception:
                pass

        # Load full history from SQLite
        try:
            history = load_history(mcp_filter, date_start, date_end)
            if history:
                return history
        except Exception:
            pass

        # Fallback: return merged records directly
        result = all_records
        if mcp_filter:
            result = [r for r in result if r.mcp_name in mcp_filter]
        if date_start:
            result = [r for r in result if r.started_at >= date_start]
        if date_end:
            result = [r for r in result if r.started_at <= date_end]
        result.sort(key=lambda r: r.started_at, reverse=True)
        return result

    def _parse_log_entries(self) -> list[ContainerRecord]:
        """Parse gateway log for 'Running mcp/SERVER' entries to capture history.
        Only processes new lines since last call."""
        try:
            stat = os.stat(self.LOG)
            current_size = stat.st_size
        except (FileNotFoundError, OSError):
            return []

        marker = os.path.expanduser("~/.config/gmcp/log_marker.txt")
        last_size = 0
        try:
            last_size = int(open(marker).read().strip())
        except (OSError, ValueError):
            pass

        if current_size <= last_size:
            return []
        try:
            open(marker, "w").write(str(current_size))
        except OSError:
            pass

        try:
            with open(self.LOG) as f:
                f.seek(last_size)
                content = f.read()
        except OSError:
            return []

        records: list[ContainerRecord] = []
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        seen = set()
        for line in content.split("\n"):
            m = re.search(r'Running mcp/([a-zA-Z0-9_.-]+)\s', line)
            if m:
                name = m.group(1).lower()
                if name not in seen:
                    seen.add(name)
                    records.append(ContainerRecord(
                        agent="Gateway",
                        mcp_name=name,
                        container_id=f"log-{name}-{now}",
                        container_name="-",
                        started_at=now,
                        ended_at=now,
                        status="stopped",
                    ))
        return records

    def get_filter_tags(self) -> list[dict]:
        try:
            all_conns = load_history()
        except Exception:
            all_conns = []
        counts: dict[str, dict] = {}
        for c in all_conns:
            if c.mcp_name not in counts:
                counts[c.mcp_name] = {"mcp_name": c.mcp_name, "active": 0, "total": 0}
            counts[c.mcp_name]["total"] += 1
            if c.status == "active":
                counts[c.mcp_name]["active"] += 1
        return list(counts.values())

    @staticmethod
    def _parse_docker_time(t: str) -> str:
        t = t.replace("Z", "").strip()
        for fmt in ["%Y-%m-%d %H:%M:%S %z %Z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"]:
            try:
                dt = datetime.strptime(t[:25], fmt) if len(t) > 25 else datetime.strptime(t, fmt)
                return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            except ValueError:
                continue
        return t
