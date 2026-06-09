"""Updated API tests — uses core service with in-memory adapters."""

import json
import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.core.entities import ServerInfo, GatewayState
from backend.core.services import GatewayService
from backend.core.credential_manager import CredentialManager, CREDENTIAL_SCHEMA
from backend.tests.test_core import (
    InMemoryCatalog,
    InMemoryState,
    SpyProfile,
    SpyGateway,
    InMemoryCredentialRepo,
)


def make_app(catalog: list | None = None, state: GatewayState | None = None,
             cred_manager: CredentialManager | None = None) -> FastAPI:
    if catalog is None:
        catalog = [
            ServerInfo(name="memory", title="Memory", desc="Persistent"),
            ServerInfo(name="fetch", title="Fetch", desc="URL fetcher"),
            ServerInfo(name="exa", title="Exa", desc="Search", secrets=True),
        ]
    if state is None:
        state = GatewayState(installed=["memory", "fetch"], enabled=["memory"])
    svc = GatewayService(
        catalog=InMemoryCatalog(catalog),
        state_repo=InMemoryState(state),
        profile=SpyProfile(),
        gateway=SpyGateway(),
        conn_repo=None,
        cred_manager=cred_manager,
    )

    app = FastAPI()
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

    def _merge(server_status):
        cm = {s.name: s for s in svc.list_catalog()}
        info = cm.get(server_status.name)
        return {
            "name": server_status.name,
            "title": info.title if info else "",
            "desc": info.desc if info else "",
            "secrets": info.secrets if info else False,
            "installed": server_status.installed,
            "enabled": server_status.enabled,
        }

    @app.get("/api/servers")
    def list_servers():
        return [_merge(s) for s in svc.list_servers()]

    @app.get("/api/catalog")
    def list_catalog():
        return [{"name": s.name, "title": s.title, "desc": s.desc, "secrets": s.secrets} for s in svc.list_catalog()]

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
        cat = svc.list_catalog()
        if not any(s.name == name for s in cat):
            from fastapi import HTTPException
            raise HTTPException(404)
        return _merge(svc.install(name))

    @app.post("/api/servers/{name}/uninstall")
    def uninstall_server(name: str):
        return _merge(svc.uninstall(name))

    @app.post("/api/servers/{name}/toggle")
    def toggle_server(name: str):
        return _merge(svc.toggle(name))

    @app.get("/api/servers/{name}")
    def server_detail(name: str):
        cm = {s.name: s for s in svc.list_catalog()}
        info = cm.get(name)
        if not info:
            from fastapi import HTTPException
            raise HTTPException(404)
        st = svc.get_state()
        return {
            "name": info.name, "title": info.title, "desc": info.desc,
            "secrets": info.secrets, "installed": name in st.installed,
            "enabled": name in st.enabled,
        }

    @app.post("/api/gateway/restart")
    def restart():
        ok = svc.restart_gateway()
        return {"status": "ok" if ok else "timeout"}

    @app.get("/api/gateway/logs")
    def logs(n: int = 5):
        all_logs = svc.get_logs()
        return {"logs": [l.message for l in all_logs[-n:]]}

    # ── Credential routes (mirror main.py) ──

    class CredentialBody:
        def __init__(self, key: str, value: str):
            self.key = key
            self.value = value

    from pydantic import BaseModel

    class CredBody(BaseModel):
        key: str
        value: str

    @app.get("/api/credentials")
    def list_creds():
        cm = svc.cred_manager
        if cm is None:
            return {}
        result: dict[str, dict[str, bool]] = {}
        for server, keys in cm.get_schema().items():
            status = {}
            for k in keys:
                try:
                    val = cm.get(server, k)
                    status[k] = val is not None
                except Exception:
                    status[k] = False
            if status:
                result[server] = status
        return result

    @app.put("/api/credentials/{server}")
    def set_cred(server: str, body: CredBody):
        cm = svc.cred_manager
        if cm is None:
            from fastapi import HTTPException
            raise HTTPException(503)
        if not cm.is_allowed(server, body.key):
            from fastapi import HTTPException
            raise HTTPException(400)
        cm.set(server, body.key, body.value)
        return {"ok": True}

    @app.delete("/api/credentials/{server}/{key}")
    def del_cred(server: str, key: str):
        cm = svc.cred_manager
        if cm is None:
            from fastapi import HTTPException
            raise HTTPException(503)
        cm.delete(server, key)
        return {"ok": True}

    return app


@pytest.fixture
def client():
    with TestClient(make_app()) as c:
        yield c


# ── Tests ───────────────────────────────────────────────────────


class TestServers:
    def test_list_servers(self, client: TestClient):
        resp = client.get("/api/servers")
        assert resp.status_code == 200
        names = {s["name"] for s in resp.json()}
        assert "memory" in names and "fetch" in names and "exa" in names

    def test_server_fields(self, client: TestClient):
        for s in client.get("/api/servers").json():
            assert all(k in s for k in ("name", "title", "desc", "secrets", "installed", "enabled"))

    def test_install_status(self, client: TestClient):
        data = {s["name"]: s for s in client.get("/api/servers").json()}
        assert data["memory"]["installed"] is True and data["memory"]["enabled"] is True
        assert data["fetch"]["installed"] is True and data["fetch"]["enabled"] is False
        assert data["exa"]["installed"] is False and data["exa"]["enabled"] is False

    def test_install_server(self, client: TestClient):
        r = client.post("/api/servers/exa/install")
        assert r.status_code == 200
        assert r.json()["installed"] is True

    def test_install_nonexistent(self, client: TestClient):
        assert client.post("/api/servers/nope/install").status_code == 404

    def test_uninstall_server(self, client: TestClient):
        r = client.post("/api/servers/memory/uninstall")
        assert r.status_code == 200
        assert r.json()["installed"] is False

    def test_toggle(self, client: TestClient):
        assert client.post("/api/servers/fetch/toggle").json()["enabled"] is True
        assert client.post("/api/servers/fetch/toggle").json()["enabled"] is False

    def test_server_detail(self, client: TestClient):
        r = client.get("/api/servers/exa")
        assert r.status_code == 200
        assert r.json()["name"] == "exa"
        assert r.json()["secrets"] is True
        assert client.get("/api/servers/nope").status_code == 404


class TestState:
    def test_get_state(self, client: TestClient):
        d = client.get("/api/state").json()
        assert "installed" in d and "enabled" in d
        assert "memory" in d["installed"] and "fetch" in d["installed"]

    def test_stats(self, client: TestClient):
        d = client.get("/api/stats").json()
        assert d == {"catalog": 3, "installed": 2, "enabled": 1}


class TestGateway:
    def test_logs(self, client: TestClient):
        d = client.get("/api/gateway/logs").json()
        assert len(d["logs"]) == 2

    def test_restart(self, client: TestClient):
        assert client.post("/api/gateway/restart").json()["status"] == "ok"


class TestCredentials:
    @pytest.fixture
    def cred_client(self):
        repo = InMemoryCredentialRepo()
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".key", delete=False) as f:
            key_path = f.name
        cm = CredentialManager(repo, key_path=key_path)
        with TestClient(make_app(cred_manager=cm)) as c:
            yield c

    def test_list_empty(self, cred_client):
        resp = cred_client.get("/api/credentials")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)

    def test_set_and_list(self, cred_client):
        resp = cred_client.put("/api/credentials/neon", json={"key": "NEON_API_KEY", "value": "sk-123"})
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}
        resp2 = cred_client.get("/api/credentials")
        assert resp2.status_code == 200
        data = resp2.json()
        assert "neon" in data
        assert data["neon"].get("NEON_API_KEY") is True

    def test_set_invalid_key(self, cred_client):
        resp = cred_client.put("/api/credentials/neon", json={"key": "INVALID_KEY", "value": "x"})
        assert resp.status_code == 400

    def test_delete(self, cred_client):
        cred_client.put("/api/credentials/neon", json={"key": "NEON_API_KEY", "value": "sk-123"})
        resp = cred_client.delete("/api/credentials/neon/NEON_API_KEY")
        assert resp.status_code == 200
        resp2 = cred_client.get("/api/credentials")
        data = resp2.json()
        assert data.get("neon", {}).get("NEON_API_KEY") is False
