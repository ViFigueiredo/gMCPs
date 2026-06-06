"""FastAPI adapter — thin web layer over GatewayService."""

import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.core.services import GatewayService
from backend.adapters.sqlite_catalog import SqliteCatalogRepo
from backend.adapters.file_state import FileStateRepo
from backend.adapters.docker_profile import SqliteProfileSync, SubprocessGateway
from backend.core.entities import Stats


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
