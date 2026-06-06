"""FastAPI adapter — thin web layer over GatewayService."""

import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.core.services import GatewayService
from backend.adapters.sqlite_catalog import SqliteCatalogRepo
from backend.adapters.file_state import FileStateRepo
from backend.adapters.docker_profile import SqliteProfileSync, SubprocessGateway
from backend.core.entities import Stats
from backend.core.integrations import detect_agents, add_server, McpServerDef


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
    return GatewayService(
        catalog=catalog,
        state_repo=state_repo,
        profile=profile,
        gateway=gateway,
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


@app.get("/api/gateway/logs")
def gateway_logs(n: int = 5):
    return {"logs": svc.get_logs(n)}


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
