"""FastAPI adapter — thin web layer over GatewayService."""

import os

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


@app.get("/api/resources")
def _is_macos() -> bool:
    import platform
    return platform.system() == "Darwin"


def system_resources():
    import subprocess, os

    resources = {
        "ram_used_mb": 0,
        "cpu_percent": 0.0,
        "storage_used_gb": 0.0,
        "active_containers": 0,
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

    mcp_container_ids: list[str] = []
    try:
        r = subprocess.run(
            ["docker", "ps", "--no-trunc", "--format", "{{.ID}}\t{{.Image}}"],
            capture_output=True, text=True, timeout=10
        )
        if r.returncode == 0:
            for line in r.stdout.strip().split("\n"):
                if not line:
                    continue
                parts = line.split("\t")
                if len(parts) == 2 and "mcp/" in parts[1].lower():
                    mcp_container_ids.append(parts[0])
    except (FileNotFoundError, OSError):
        pass

    resources["active_containers"] = len(mcp_container_ids)

    # RAM
    try:
        total_ram_mb = 0.0
        if mcp_container_ids:
            r = subprocess.run(
                ["docker", "stats", "--no-stream", "--format", "{{.MemUsage}}"] + mcp_container_ids,
                capture_output=True, text=True, timeout=10
            )
            for line in r.stdout.strip().split("\n"):
                line = line.strip()
                if "MiB" in line:
                    val = line.split(" /")[0].replace("MiB", "").strip()
                    try: total_ram_mb += float(val)
                    except ValueError: pass
                elif "GiB" in line:
                    val = line.split(" /")[0].replace("GiB", "").strip()
                    try: total_ram_mb += float(val) * 1024
                    except ValueError: pass
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
    except (subprocess.TimeoutExpired, OSError):
        pass

    # CPU
    try:
        total_cpu = 0.0
        if mcp_container_ids:
            r = subprocess.run(
                ["docker", "stats", "--no-stream", "--format", "{{.CPUPerc}}"] + mcp_container_ids,
                capture_output=True, text=True, timeout=10
            )
            for line in r.stdout.strip().split("\n"):
                line = line.strip().replace("%", "")
                try: total_cpu += float(line)
                except ValueError: pass
        for pid in gateway_pids:
            try:
                if macos:
                    r = subprocess.run(
                        ["ps", "-o", "%cpu=", "-p", pid],
                        capture_output=True, text=True, timeout=5
                    )
                    if r.returncode == 0 and r.stdout.strip():
                        total_cpu += float(r.stdout.strip())
                else:
                    with open(f"/proc/{pid}/stat") as f:
                        parts = f.read().split()
                        utime = int(parts[13]); stime = int(parts[14])
                        cutime = int(parts[15]); cstime = int(parts[16])
                        total = utime + stime + cutime + cstime
                    with open("/proc/stat") as f:
                        cpu_parts = f.readline().split()
                        cpu_total = sum(int(x) for x in cpu_parts[1:])
                    total_cpu += round(total / cpu_total * 100, 1)
            except (OSError, ValueError, IndexError, FileNotFoundError, subprocess.TimeoutExpired):
                pass
        resources["cpu_percent"] = round(total_cpu, 1)
    except (subprocess.TimeoutExpired, OSError):
        pass

    # Storage
    try:
        used_gb = 0.0
        for pid in gateway_pids:
            try:
                if macos:
                    r = subprocess.run(
                        ["lsof", "-p", pid, "-Fn"],
                        capture_output=True, text=True, timeout=5
                    )
                    files = set()
                    for ln in r.stdout.split("\n"):
                        if ln.startswith("n/"):
                            files.add(os.path.dirname(ln[1:]))
                    for d in list(files)[:5]:
                        rs = subprocess.run(
                            ["du", "-sk", d],
                            capture_output=True, text=True, timeout=5
                        )
                        if rs.returncode == 0:
                            used_gb += int(rs.stdout.split()[0]) * 1024 / (1024**3)
                else:
                    r = subprocess.run(
                        ["readlink", "-f", f"/proc/{pid}/exe"],
                        capture_output=True, text=True, timeout=5
                    )
                    if r.returncode == 0:
                        rs = subprocess.run(
                            ["du", "-sb", r.stdout.strip()],
                            capture_output=True, text=True, timeout=5
                        )
                        if rs.returncode == 0:
                            used_gb += int(rs.stdout.split()[0]) / (1024**3)
            except (OSError, ValueError, subprocess.TimeoutExpired):
                pass
        for d in ["~/.config/gmcp", "~/.docker/mcp"]:
            try:
                dd = os.path.expanduser(d)
                if os.path.exists(dd):
                    rs = subprocess.run(
                        ["du", "-sk", dd],
                        capture_output=True, text=True, timeout=5
                    )
                    if rs.returncode == 0:
                        used_gb += int(rs.stdout.split()[0]) * 1024 / (1024**3)
            except (OSError, ValueError, subprocess.TimeoutExpired):
                pass
        resources["storage_used_gb"] = round(used_gb, 2)
    except (subprocess.TimeoutExpired, OSError):
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
    agent_types = {"claudecode": "http", "openclaude": "http"}
    mcp_type = agent_types.get(agent_id, "remote")
    server = McpServerDef(
        name=mcp_name,
        type=mcp_type,
        url="http://localhost:3099/sse",
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
