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
    return {"logs": svc.get_logs(level=level)}


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

    # Storage (Docker disk usage)
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
    import subprocess
    try:
        r = subprocess.run(
            ["docker", "ps", "-a", "--no-trunc", "--format", "{{json .}}"],
            capture_output=True, text=True, timeout=10
        )
        if r.returncode != 0:
            raise HTTPException(500, "Docker unavailable")
        target = mcp_name.lower()
        stopped = False
        for line in r.stdout.strip().split("\n"):
            if not line:
                continue
            import json as _json
            try:
                c = _json.loads(line)
            except _json.JSONDecodeError:
                continue
            img = c.get("Image", "")
            import re
            m = re.match(r'mcp/([a-zA-Z0-9_.-]+)', img)
            if m and m.group(1).lower() == target:
                cid = c.get("ID", "")
                subprocess.run(["docker", "stop", cid], capture_output=True, timeout=15)
                subprocess.run(["docker", "rm", cid], capture_output=True, timeout=15)
                stopped = True
        if not stopped:
            raise HTTPException(404, f"No container found for MCP '{mcp_name}'")
        return {"status": "ok", "mcp": mcp_name}
    except subprocess.TimeoutExpired:
        raise HTTPException(504, "Docker timeout")


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
