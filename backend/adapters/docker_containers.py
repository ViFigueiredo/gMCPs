"""Adapter: reads MCP container connections from Docker."""

import json
import os
import re
import subprocess
from datetime import datetime, timezone

from backend.core.ports import ConnectionRepository
from backend.core.entities import ContainerRecord


def _parse_mcp_name(image: str) -> str:
    m = re.match(r'mcp/([a-zA-Z0-9_.-]+)', image)
    if m:
        return m.group(1).lower()
    return image


def _detect_active_agents() -> dict[str, str]:
    """Returns {mcp_name: agent_name} for active connections to port 3099."""
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
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    return result


class DockerConnectionRepo(ConnectionRepository):
    LOG = "/tmp/gateway.log"

    def list_connections(
        self,
        mcp_filter: list[str] | None = None,
        date_start: str | None = None,
        date_end: str | None = None,
    ) -> list[ContainerRecord]:
        try:
            r = subprocess.run(
                ["docker", "ps", "-a", "--no-trunc", "--format", "{{json .}}"],
                capture_output=True, text=True, timeout=15
            )
            if r.returncode != 0:
                return self._from_log_fallback()
            lines = [l for l in r.stdout.strip().split("\n") if l]
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return self._from_log_fallback()

        agents = _detect_active_agents()
        records: list[ContainerRecord] = []
        for line in lines:
            try:
                c = json.loads(line)
            except json.JSONDecodeError:
                continue
            image = c.get("Image", "")
            if "mcp/" not in image.lower():
                continue
            mcp = _parse_mcp_name(image)
            if mcp_filter and mcp not in mcp_filter:
                continue

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

            rec = ContainerRecord(
                agent=agent,
                mcp_name=mcp,
                container_id=container_id,
                container_name=container_name,
                started_at=started,
                ended_at=ended,
                status=status,
            )
            if date_start and rec.started_at < date_start:
                continue
            if date_end and rec.started_at > date_end:
                continue
            records.append(rec)

        records.sort(key=lambda r: r.started_at, reverse=True)
        return records

    def get_filter_tags(self) -> list[dict]:
        all_conns = self.list_connections()
        counts: dict[str, dict] = {}
        for c in all_conns:
            if c.mcp_name not in counts:
                counts[c.mcp_name] = {"mcp_name": c.mcp_name, "active": 0, "total": 0}
            counts[c.mcp_name]["total"] += 1
            if c.status == "active":
                counts[c.mcp_name]["active"] += 1
        return list(counts.values())

    def _from_log_fallback(self) -> list[ContainerRecord]:
        try:
            with open(self.LOG) as f:
                content = f.read()
        except (FileNotFoundError, OSError):
            return []
        records: list[ContainerRecord] = []
        for line in content.split("\n"):
            if "mcp/" in line.lower() and "@sha256" in line:
                m = re.search(r'mcp/([a-zA-Z0-9_.-]+)', line)
                if m:
                    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                    records.append(ContainerRecord(
                        agent="Gateway",
                        mcp_name=m.group(1).lower(),
                        container_id="-",
                        container_name="-",
                        started_at=now,
                        ended_at=None,
                        status="active",
                    ))
        return records

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
