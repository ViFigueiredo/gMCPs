"""FastAPI adapter — thin web layer over GatewayService."""

import os
import json

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.core.services import GatewayService
from backend.adapters.sqlite_catalog import SqliteCatalogRepo
from backend.adapters.file_state import FileStateRepo
from backend.adapters.docker_profile import SqliteProfileSync, SubprocessGateway
from backend.adapters.docker_containers import DockerConnectionRepo
from backend.core.entities import Stats
from backend.core.integrations import detect_agents, add_server, remove_server, McpServerDef, AGENTS


def build_service(
    db_path: str | None = None,
    state_path: str | None = None,
) -> GatewayService:
    db = db_path or os.path.expanduser("~/.docker/mcp/mcp-toolkit.db")
    sp = state_path or os.path.expanduser("~/.config/gmcp/state.json")
    catalog = SqliteCatalogRepo(db)
    state_repo = FileStateRepo(sp, db)
    profile = SqliteProfileSync(db, catalog.list_all)
    gateway = SubprocessGateway()
    conn_repo = DockerConnectionRepo()
    return GatewayService(
        catalog=catalog,
        state_repo=state_repo,
        profile=profile,
        gateway=gateway,
        conn_repo=conn_repo,
    )


svc = build_service()

app = FastAPI(title="gmcp API", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Helpers ──────────────────────────────────────────────────────


def _merge(server_status) -> dict:
    """Merge catalog info + status into one response dict."""
    catalog_map = {s.name: s for s in svc.list_catalog()}
    info = catalog_map.get(server_status.name)
    return {
        "name": server_status.name,
        "title": info.title if info else "",
        "desc": info.desc if info else "",
        "secrets": info.secrets if info else False,
        "installed": server_status.installed,
        "enabled": server_status.enabled,
    }


# ── Routes ───────────────────────────────────────────────────────


@app.get("/api/servers")
def list_servers():
    return [_merge(s) for s in svc.list_servers()]


@app.get("/api/catalog")
def list_catalog():
    return [
        {"name": s.name, "title": s.title, "desc": s.desc, "secrets": s.secrets}
        for s in svc.list_catalog()
    ]


@app.get("/api/state")
def get_state():
    st = svc.get_state()
    return {"installed": st.installed, "enabled": st.enabled}


@app.get("/api/stats")
def get_stats():
    st = svc.get_stats()
    return {"catalog": st.catalog, "installed": st.installed, "enabled": st.enabled}


@app.post("/api/servers/{name}/install")
def install_server(name: str):
    catalog = svc.list_catalog()
    if not any(s.name == name for s in catalog):
        raise HTTPException(404, f"Server '{name}' not found")
    result = svc.install(name)
    return _merge(result)


@app.post("/api/servers/{name}/uninstall")
def uninstall_server(name: str):
    result = svc.uninstall(name)
    return _merge(result)


@app.post("/api/servers/{name}/toggle")
def toggle_server(name: str):
    result = svc.toggle(name)
    return _merge(result)


@app.get("/api/servers/{name}")
def server_detail(name: str):
    catalog_map = {s.name: s for s in svc.list_catalog()}
    info = catalog_map.get(name)
    if not info:
        raise HTTPException(404, f"Server '{name}' not found")
    state = svc.get_state()
    return {
        "name": info.name,
        "title": info.title,
        "desc": info.desc,
        "secrets": info.secrets,
        "installed": name in state.installed,
        "enabled": name in state.enabled,
    }


@app.post("/api/gateway/restart")
def restart_gateway():
    ok = svc.restart_gateway()
    return {"status": "ok" if ok else "timeout"}


@app.get("/api/logs")
def get_logs(level: str | None = None):
    entries = svc.get_logs(level=level)
    return {"logs": [e.message for e in entries]}


# ── Shared mode ──────────────────────────────────────────────────────


@app.get("/api/shared")
def list_shared():
    return {"shared": svc.list_shared()}


@app.post("/api/servers/{name}/share")
def enable_shared(name: str):
    from backend.adapters.mcp_relay import list_relays
    try:
        info = svc.enable_shared(name)
        return {"status": "ok", "relay": info}
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/servers/{name}/unshare")
def disable_shared(name: str):
    ok = svc.disable_shared(name)
    return {"status": "ok" if ok else "not_found"}


@app.get("/api/shared/status")
def shared_status():
    from backend.adapters.mcp_relay import list_relays
    relays = list_relays()
    return {"relays": [r.to_dict() for r in relays]}


# ── System Resources ────────────────────────────────────────────────


def _is_macos() -> bool:
    import platform
    return platform.system() == "Darwin"


@app.get("/api/resources")
def system_resources():
    import subprocess, os, json

    resources = {
        "ram_used_mb": 0.0,
        "cpu_percent": 0.0,
        "storage_used_gb": 0.0,
        "active_servers": 0,
        "gateway_online": False,
    }

    macos = _is_macos()
    gateway_pids = set()
    try:
        r = subprocess.run(
            ["pgrep", "-f", "docker mcp gateway run"],
            capture_output=True, text=True, timeout=5
        )
        if r.returncode == 0:
            for pid in r.stdout.strip().split("\n"):
                if pid:
                    gateway_pids.add(pid)
    except (FileNotFoundError, OSError):
        pass

    resources["gateway_online"] = len(gateway_pids) > 0

    # Servers configurados (state.json)
    state_path = os.path.expanduser("~/.config/gmcp/state.json")
    try:
        with open(state_path) as f:
            state = json.load(f)
            resources["active_servers"] = len(state.get("enabled", []))
    except (OSError, json.JSONDecodeError):
        pass

    # RAM do processo do gateway
    total_ram_mb = 0.0
    for pid in gateway_pids:
        try:
            if macos:
                r = subprocess.run(
                    ["ps", "-o", "rss=", "-p", pid],
                    capture_output=True, text=True, timeout=5
                )
                if r.returncode == 0 and r.stdout.strip():
                    total_ram_mb += int(r.stdout.strip()) / 1024
            else:
                with open(f"/proc/{pid}/status") as f:
                    for ln in f:
                        if ln.startswith("VmRSS:"):
                            total_ram_mb += int(ln.split()[1]) / 1024
                            break
        except (OSError, ValueError, FileNotFoundError, subprocess.TimeoutExpired):
            pass
    resources["ram_used_mb"] = round(total_ram_mb, 1)

    # CPU do processo do gateway
    try:
        for pid in gateway_pids:
            with open(f"/proc/{pid}/stat") as f:
                parts = f.read().split()
                if len(parts) > 13:
                    utime = int(parts[13])
                    stime = int(parts[14])
                    total_cpu = (utime + stime) / 100.0
                    resources["cpu_percent"] = round(max(resources["cpu_percent"], total_cpu), 1)
    except (OSError, ValueError, IndexError):
        pass

    # Storage — try docker first, fallback to system df
    try:
        r = subprocess.run(
            ["docker", "system", "df", "--format", "{{.Size}}"],
            capture_output=True, text=True, timeout=10
        )
        if r.returncode == 0:
            for line in r.stdout.strip().split("\n"):
                line = line.strip()
                if not line:
                    continue
                if "GB" in line:
                    val = line.replace("GB", "").strip()
                    try: resources["storage_used_gb"] = max(resources["storage_used_gb"], float(val))
                    except ValueError: pass
                elif "MB" in line:
                    val = line.replace("MB", "").strip()
                    try: resources["storage_used_gb"] = max(resources["storage_used_gb"], round(float(val) / 1024, 2))
                    except ValueError: pass
        else:
            raise OSError(r.stderr)
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        # Fallback: system disk usage
        try:
            r = subprocess.run(
                ["df", "-h", "/"],
                capture_output=True, text=True, timeout=5
            )
            if r.returncode == 0:
                for line in r.stdout.strip().split("\n"):
                    parts = line.split()
                    if len(parts) >= 6 and parts[-1] == "/":
                        used = parts[2]
                        if used.endswith("G"):
                            resources["storage_used_gb"] = float(used.replace("G", ""))
                        elif used.endswith("T"):
                            resources["storage_used_gb"] = float(used.replace("T", "")) * 1024
                        elif used.endswith("M"):
                            resources["storage_used_gb"] = round(float(used.replace("M", "")) / 1024, 2)
        except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
            pass

    return resources


# ── Connections (container logs) ─────────────────────────────────────


@app.get("/api/connections")
def list_connections(
    mcp: str = "",
    date_start: str = "",
    date_end: str = "",
):
    mcp_filter = mcp.split(",") if mcp else None
    conns = svc.list_connections(
        mcp_filter=mcp_filter,
        date_start=date_start or None,
        date_end=date_end or None,
    )
    return {
        "connections": [
            {
                "agent": c.agent,
                "mcp_name": c.mcp_name,
                "container_id": c.container_id,
                "container_name": c.container_name,
                "started_at": c.started_at,
                "ended_at": c.ended_at,
                "status": c.status,
            }
            for c in conns
        ]
    }


@app.get("/api/connections/tags")
def connection_tags():
    return {"tags": svc.get_connection_tags()}


@app.post("/api/connections/{mcp_name}/stop")
def stop_container(mcp_name: str):
    import subprocess, re
    target = mcp_name.lower()
    try:
        # Find by label docker-mcp-name (set by gateway)
        r = subprocess.run(
            ["docker", "ps", "--no-trunc", "--format", "{{.ID}}\t{{.Names}}\t{{.Image}}",
             "--filter", f"label=docker-mcp-name={mcp_name}",
             "--filter", "label=docker-mcp=true"],
            capture_output=True, text=True, timeout=10
        )
        for line in r.stdout.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t")
            cid = parts[0]
            subprocess.run(["docker", "stop", cid], capture_output=True, timeout=15)
            subprocess.run(["docker", "rm", "-f", cid], capture_output=True, timeout=15)
            return {"status": "ok", "mcp": mcp_name, "method": "label"}

        # Fallback: match by image name mcp/SERVERNAME
        r = subprocess.run(
            ["docker", "ps", "-a", "--no-trunc", "--format", "{{json .}}"],
            capture_output=True, text=True, timeout=10
        )
        if r.returncode == 0:
            for line in r.stdout.strip().split("\n"):
                if not line:
                    continue
                import json as _json
                try:
                    c = _json.loads(line)
                except _json.JSONDecodeError:
                    continue
                img = c.get("Image", "")
                m = re.match(r'mcp/([a-zA-Z0-9_.-]+)', img)
                if m and m.group(1).lower() == target:
                    cid = c.get("ID", "")
                    subprocess.run(["docker", "stop", cid], capture_output=True, timeout=15)
                    subprocess.run(["docker", "rm", "-f", cid], capture_output=True, timeout=15)
                    return {"status": "ok", "mcp": mcp_name, "method": "image"}

        # No container found — kill gateway process to force restart
        subprocess.run(["pkill", "-9", "-f", "docker mcp gateway run"], capture_output=True, timeout=5)
        # Clean orphan containers
        subprocess.run(
            ["docker", "rm", "-f"] + subprocess.run(
                ["docker", "ps", "-aq", "--filter", "label=docker-mcp=true"],
                capture_output=True, text=True, timeout=5
            ).stdout.strip().split("\n"),
            capture_output=True, timeout=15
        )
        return {"status": "restarted", "mcp": mcp_name, "detail": "no running container found, gateway restarted"}
    except subprocess.TimeoutExpired:
        raise HTTPException(504, "Docker timeout")


@app.post("/api/connections/clear")
def clear_connections(body: dict):
    import subprocess, re, json as _json, logging
    from datetime import datetime, timedelta

    logger = logging.getLogger("uvicorn")

    mcps_filter = body.get("mcps", [])
    date_start = body.get("date_start", "")
    date_end = body.get("date_end", "")
    last_seconds = body.get("last_seconds", 0)

    try:
        now = datetime.now()
        if last_seconds and last_seconds > 0:
            date_start = (now - timedelta(seconds=int(last_seconds))).isoformat(timespec="seconds")
    except (TypeError, ValueError) as e:
        raise HTTPException(400, f"Invalid last_seconds: {e}")

    try:
        r = subprocess.run(
            ["docker", "ps", "--no-trunc", "--format", "{{json .}}", "--filter", "label=docker-mcp=true"],
            capture_output=True, text=True, timeout=30
        )
        if r.returncode != 0:
            raise HTTPException(500, f"Docker unavailable: {r.stderr.strip()}")
    except subprocess.TimeoutExpired:
        raise HTTPException(504, "Docker timeout listing containers")
    except FileNotFoundError:
        raise HTTPException(500, "Docker not found in PATH")

    stopped = 0
    found_real = False
    for line in r.stdout.strip().split("\n"):
        if not line:
            continue
        try:
            c = _json.loads(line)
        except _json.JSONDecodeError:
            logger.warning("clear: invalid JSON from docker ps")
            continue

        # Parse docker-mcp-name from labels
        labels = c.get("Labels", "") or ""
        mcp_name = ""
        if isinstance(labels, str):
            for part in labels.split(","):
                part = part.strip()
                if part.startswith("docker-mcp-name="):
                    mcp_name = part.split("=", 1)[1]
                    break
        elif isinstance(labels, dict):
            mcp_name = labels.get("docker-mcp-name", "")

        if not mcp_name:
            img = c.get("Image", "")
            m = re.match(r'mcp/([a-zA-Z0-9_.-]+)', img)
            if m:
                mcp_name = m.group(1)
        if not mcp_name:
            continue
        if mcps_filter and mcp_name not in mcps_filter:
            continue

        # Filter by date
        created = c.get("CreatedAt", "")
        if created:
            created_ts = created.split(".")[0]
            if date_start and created_ts < date_start:
                continue
            if date_end and created_ts > date_end:
                continue

        status = c.get("Status", "")
        if not status.startswith("Up"):
            continue

        cid = c.get("ID", "")
        found_real = True
        try:
            subprocess.run(["docker", "stop", cid], capture_output=True, timeout=15)
            subprocess.run(["docker", "rm", "-f", cid], capture_output=True, timeout=15)
            stopped += 1
        except subprocess.TimeoutExpired:
            logger.warning(f"clear: timeout stopping {cid}")
        except Exception as e:
            logger.warning(f"clear: error stopping {cid}: {e}")

    # If no real containers found, fallback: remove active from DB history
    if not found_real:
        from backend.adapters.connection_db import remove_active, load_history
        removed = remove_active(mcps_filter if mcps_filter else None)
        logger.info(f"clear: no real containers, removed {removed} active entries from history")
        # Also kill gateway to reset state
        subprocess.run(["pkill", "-9", "-f", "docker mcp gateway run"], capture_output=True, timeout=5)
        subprocess.run(
            ["docker", "rm", "-f"] + subprocess.run(
                ["docker", "ps", "-aq", "--filter", "label=docker-mcp=true"],
                capture_output=True, text=True, timeout=5
            ).stdout.strip().split("\n"),
            capture_output=True, timeout=15
        )

    return {"status": "ok", "stopped": stopped}

    return {"status": "ok", "stopped": stopped}


# ── Integrations ─────────────────────────────────────────────────────


class AddServerBody(BaseModel):
    agent_id: str
    name: str
    type: str = "local"
    command: str = ""
    args: list[str] = []
    url: str = ""
    env: dict[str, str] = {}


@app.get("/api/integrations")
def list_integrations():
    return [{
        "id": a.id,
        "name": a.name,
        "config_path": a.config_path,
        "config_format": a.config_format,
        "installed": a.installed,
        "servers": [
            {
                "name": s.name,
                "type": s.type,
                "command": s.command,
                "args": s.args,
                "url": s.url,
                "env": s.env,
                "enabled": s.enabled,
            }
            for s in a.servers
        ],
        "error": a.error,
    } for a in detect_agents()]


@app.post("/api/integrations/add-server")
def add_integration_server(body: AddServerBody):
    catalog_map = {s.name.lower(): s for s in svc.list_catalog()}
    is_catalog = body.name.lower() in catalog_map
    token = os.environ.get("MCP_GATEWAY_AUTH_TOKEN", "mcp-local-token")

    if is_catalog and not body.url and not body.command:
        mcp_type = "http" if body.agent_id == "openclaude" else "remote"
        server = McpServerDef(
            name=body.name,
            type=mcp_type,
            url=f"http://localhost:3099/sse?server={body.name}",
            enabled=True,
            env={
                "headers": {
                    "Authorization": f"Bearer {token}"
                }
            },
        )
    else:
        server = McpServerDef(
            name=body.name,
            type=body.type,
            command=body.command,
            args=body.args,
            url=body.url,
            env=body.env,
        )
    try:
        agents = add_server(body.agent_id, server)
        return {"status": "ok"}
    except (FileNotFoundError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/integrations/remove-server/{agent_id}/{server_name}")
def remove_integration_server(agent_id: str, server_name: str):
    try:
        agents = remove_server(agent_id, server_name)
        return {"status": "ok"}
    except (FileNotFoundError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/integrations/auto-add/{agent_id}/{mcp_name}")
def auto_add_mcp(agent_id: str, mcp_name: str):
    catalog_map = {s.name.lower(): s for s in svc.list_catalog()}
    info = catalog_map.get(mcp_name.lower())
    if not info:
        raise HTTPException(404, f"MCP '{mcp_name}' not found in catalog")
    token = os.environ.get("MCP_GATEWAY_AUTH_TOKEN", "mcp-local-token")
    local_agents = {"codex"}
    if agent_id in local_agents:
        server = McpServerDef(
            name=mcp_name,
            type="local",
            command="sh",
            args=["-c", f"exec docker run -i --rm mcp/{mcp_name.lower()}"],
            enabled=True,
        )
    elif agent_id == "claudecode":
        import pathlib
        # Remove stale entry from .claude.json if present
        claude_path = pathlib.Path(os.path.expanduser("~/.claude.json"))
        if claude_path.exists():
            try:
                claude_data = json.loads(claude_path.read_text())
                removed_global = claude_data.get("mcpServers", {}).pop(mcp_name, None)
                removed_from_project = False
                for proj, pdata in claude_data.get("projects", {}).items():
                    if isinstance(pdata, dict):
                        if pdata.get("mcpServers", {}).pop(mcp_name, None):
                            removed_from_project = True
                if removed_global or removed_from_project:
                    claude_path.write_text(json.dumps(claude_data, indent=2) + "\n")
            except (json.JSONDecodeError, OSError):
                pass
        # Write .mcp.json
        mcp_json = pathlib.Path.cwd() / ".mcp.json"
        existing = {}
        if mcp_json.exists():
            existing = json.loads(mcp_json.read_text()) if mcp_json.stat().st_size > 0 else {}
        existing.setdefault("mcpServers", {})[mcp_name] = {
            "command": "sh",
            "args": ["-c", f"exec docker run -i --rm mcp/{mcp_name.lower()}"],
        }
        mcp_json.write_text(json.dumps(existing, indent=2) + "\n")
        return {"status": "ok", "method": "mcp.json"}
    else:
        mcp_type = "http" if agent_id == "openclaude" else "remote"
        server = McpServerDef(
            name=mcp_name,
            type=mcp_type,
            url=f"http://localhost:3099/sse?server={mcp_name}",
            enabled=True,
            env={
                "headers": {
                    "Authorization": f"Bearer {token}"
                }
            },
        )
    try:
        agents = add_server(agent_id, server)
        return {"status": "ok"}
    except (FileNotFoundError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))
