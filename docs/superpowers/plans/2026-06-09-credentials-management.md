# Credentials Management Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow users to enter MCP credentials via TUI and Web UIs, store them encrypted in SQLite, and inject them as environment variables when starting the Docker MCP gateway.

**Architecture:** Hexagonal — new `CredentialManager` in core layer, `CredentialRepo` adapter in SQLite, new FastAPI routes, new TUI tab, new Vue 3 view. Encryption via `cryptography.fernet` (AES-256). Master key at `~/.config/gmcp/credentials.key`.

**Tech Stack:** Python 3, cryptography, FastAPI, Vue 3, Pinia, curses (stdlib)

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `requirements.txt` | MODIFY | Add `cryptography` dependency |
| `backend/core/ports.py` | MODIFY | Add `CredentialRepository` abstract port |
| `backend/core/entities.py` | MODIFY | Add `CredentialStatus` dataclass |
| `backend/adapters/credential_repo.py` | CREATE | SQLite persistence for encrypted credentials |
| `backend/core/credential_manager.py` | CREATE | Encryption/decryption orchestration |
| `backend/core/services.py` | MODIFY | Add `cred_manager` property, `restart_with_credentials()` |
| `backend/main.py` | MODIFY | Add `/api/credentials` CRUD routes |
| `start-gateway.sh` | MODIFY | Read credentials from DB and export as env vars |
| `mcp-tui.py` | MODIFY | Add 4th tab "Credenciais" with edit form |
| `src/types/index.ts` | MODIFY | Add `CredentialEntry` type |
| `src/api/index.ts` | MODIFY | Add `credentials` API methods |
| `src/stores/credentials.ts` | CREATE | Pinia store for credentials state |
| `src/views/CredentialsView.vue` | CREATE | Vue 3 credentials management view |
| `src/router/index.ts` | MODIFY | Add `/credentials` route |
| `src/locales/pt-BR.json` | MODIFY | Add credentials i18n keys |
| `src/locales/en-US.json` | MODIFY | Add credentials i18n keys |
| `backend/tests/test_core.py` | MODIFY | Add CredentialManager tests |
| `backend/tests/test_api.py` | MODIFY | Add credential API endpoint tests |

---

### Task 1: Add cryptography dependency

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Update requirements.txt**

Add `cryptography` to `requirements.txt`:

```
# gmcp — Gateway MCP Manager
# Backend dependencies (automatically installed by npm postinstall)

fastapi>=0.115.0
uvicorn>=0.34.0
pydantic>=2.0.0
cryptography>=44.0.0
```

- [ ] **Step 2: Verify installation**

Run: `pip install cryptography`
Expected: cryptography installed successfully

- [ ] **Step 3: Commit**

```bash
git add requirements.txt
git commit -m "chore: add cryptography dependency for credential encryption"
```

---

### Task 2: Add CredentialRepository port

**Files:**
- Modify: `backend/core/ports.py`

- [ ] **Step 1: Add the abstract port**

Add at the end of `backend/core/ports.py`:

```python
class CredentialRepository(ABC):
    """Persists encrypted credential values."""

    @abstractmethod
    def upsert(self, server: str, key: str, value: str) -> None:
        ...

    @abstractmethod
    def get(self, server: str, key: str) -> str | None:
        ...

    @abstractmethod
    def list_keys(self, server: str) -> list[str]:
        ...

    @abstractmethod
    def list_servers(self) -> list[str]:
        ...

    @abstractmethod
    def list_all(self) -> list[tuple[str, str, bool]]:
        ...

    @abstractmethod
    def delete(self, server: str, key: str) -> None:
        ...
```

- [ ] **Step 2: Verify file is valid Python**

Run: `python3 -c "from backend.core.ports import CredentialRepository; print('OK')"`
Expected: OK

- [ ] **Step 3: Commit**

```bash
git add backend/core/ports.py
git commit -m "feat: add CredentialRepository abstract port"
```

---

### Task 3: Add CredentialStatus entity

**Files:**
- Modify: `backend/core/entities.py`

- [ ] **Step 1: Add dataclass**

Add at the end of `backend/core/entities.py`:

```python
@dataclass
class CredentialStatus:
    server: str
    key: str
    has_value: bool
```

- [ ] **Step 2: Verify**

Run: `python3 -c "from backend.core.entities import CredentialStatus; print('OK')"`
Expected: OK

- [ ] **Step 3: Commit**

```bash
git add backend/core/entities.py
git commit -m "feat: add CredentialStatus entity"
```

---

### Task 4: Create CredentialRepo adapter

**Files:**
- Create: `backend/adapters/credential_repo.py`

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_core.py`:

```python
def test_credential_repo_upsert_get():
    repo = InMemoryCredentialRepo()
    repo.upsert("neon", "NEON_API_KEY", "sk-123")
    assert repo.get("neon", "NEON_API_KEY") == "sk-123"

def test_credential_repo_get_nonexistent():
    repo = InMemoryCredentialRepo()
    assert repo.get("neon", "NONEXISTENT") is None

def test_credential_repo_list_keys():
    repo = InMemoryCredentialRepo()
    repo.upsert("neon", "NEON_API_KEY", "v1")
    repo.upsert("neon", "OTHER_KEY", "v2")
    keys = repo.list_keys("neon")
    assert "NEON_API_KEY" in keys
    assert "OTHER_KEY" in keys

def test_credential_repo_list_servers():
    repo = InMemoryCredentialRepo()
    repo.upsert("neon", "NEON_API_KEY", "v1")
    repo.upsert("github", "TOKEN", "v2")
    servers = repo.list_servers()
    assert "neon" in servers
    assert "github" in servers

def test_credential_repo_delete():
    repo = InMemoryCredentialRepo()
    repo.upsert("neon", "KEY", "val")
    assert repo.get("neon", "KEY") == "val"
    repo.delete("neon", "KEY")
    assert repo.get("neon", "KEY") is None

def test_credential_repo_upsert_overwrites():
    repo = InMemoryCredentialRepo()
    repo.upsert("neon", "KEY", "old")
    repo.upsert("neon", "KEY", "new")
    assert repo.get("neon", "KEY") == "new"

def test_credential_repo_list_all():
    repo = InMemoryCredentialRepo()
    repo.upsert("neon", "KEY1", "v1")
    repo.upsert("github", "KEY2", "v2")
    all_items = repo.list_all()
    assert len(all_items) == 2
    assert ("neon", "KEY1", True) in all_items
    assert ("github", "KEY2", True) in all_items
```

Also add an `InMemoryCredentialRepo` class near the other in-memory adapters:

```python
class InMemoryCredentialRepo(CredentialRepository):
    def __init__(self):
        self._store: dict[tuple[str, str], str] = {}

    def upsert(self, server: str, key: str, value: str) -> None:
        self._store[(server, key)] = value

    def get(self, server: str, key: str) -> str | None:
        return self._store.get((server, key))

    def list_keys(self, server: str) -> list[str]:
        return [k for (s, k) in self._store if s == server]

    def list_servers(self) -> list[str]:
        servers = {s for (s, _) in self._store}
        return list(servers)

    def list_all(self) -> list[tuple[str, str, bool]]:
        return [(s, k, True) for (s, k) in self._store]

    def delete(self, server: str, key: str) -> None:
        self._store.pop((server, key), None)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest backend/tests/test_core.py::test_credential_repo_upsert_get -x -v 2>&1 | head -15`
Expected: ImportError or NameError for InMemoryCredentialRepo

- [ ] **Step 3: Create CredentialRepo adapter**

```python
"""SQLite adapter for encrypted credential storage."""

import sqlite3
from typing import Optional
from backend.core.ports import CredentialRepository


class SqliteCredentialRepo(CredentialRepository):
    """Persists encrypted credentials in the catalog SQLite database."""

    def __init__(self, db_path: str):
        self._db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS credential_store (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    server_name TEXT    NOT NULL,
                    key         TEXT    NOT NULL,
                    value       TEXT    NOT NULL,
                    updated_at  TEXT    NOT NULL DEFAULT (datetime('now')),
                    UNIQUE(server_name, key)
                )
            """)

    def upsert(self, server: str, key: str, value: str) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """INSERT INTO credential_store (server_name, key, value, updated_at)
                   VALUES (?, ?, ?, datetime('now'))
                   ON CONFLICT(server_name, key) DO UPDATE SET
                       value=excluded.value,
                       updated_at=datetime('now')""",
                (server, key, value),
            )

    def get(self, server: str, key: str) -> Optional[str]:
        with sqlite3.connect(self._db_path) as conn:
            row = conn.execute(
                "SELECT value FROM credential_store WHERE server_name=? AND key=?",
                (server, key),
            ).fetchone()
            return row[0] if row else None

    def list_keys(self, server: str) -> list[str]:
        with sqlite3.connect(self._db_path) as conn:
            rows = conn.execute(
                "SELECT key FROM credential_store WHERE server_name=?",
                (server,),
            ).fetchall()
            return [r[0] for r in rows]

    def list_servers(self) -> list[str]:
        with sqlite3.connect(self._db_path) as conn:
            rows = conn.execute(
                "SELECT DISTINCT server_name FROM credential_store"
            ).fetchall()
            return [r[0] for r in rows]

    def list_all(self) -> list[tuple[str, str, bool]]:
        with sqlite3.connect(self._db_path) as conn:
            rows = conn.execute(
                "SELECT server_name, key, 1 FROM credential_store"
            ).fetchall()
            return rows

    def delete(self, server: str, key: str) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                "DELETE FROM credential_store WHERE server_name=? AND key=?",
                (server, key),
            )
```

- [ ] **Step 4: Update test imports**

Add to the imports in `backend/tests/test_core.py`:
```python
from backend.core.ports import (
    CatalogRepository,
    StateRepository,
    ProfileSync,
    GatewayController,
    CredentialRepository,
)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /home/viniciusfigueiredo/Documentos/MCPs/backend && python3 -m pytest tests/test_core.py::test_credential_repo_upsert_get tests/test_core.py::test_credential_repo_get_nonexistent tests/test_core.py::test_credential_repo_list_keys tests/test_core.py::test_credential_repo_list_servers tests/test_core.py::test_credential_repo_delete tests/test_core.py::test_credential_repo_upsert_overwrites tests/test_core.py::test_credential_repo_list_all -v`
Expected: 7 passed

- [ ] **Step 6: Commit**

```bash
git add backend/adapters/credential_repo.py backend/tests/test_core.py
git commit -m "feat: add SqliteCredentialRepo adapter with tests"
```

---

### Task 5: Create CredentialManager core

**Files:**
- Create: `backend/core/credential_manager.py`
- Modify: `backend/tests/test_core.py`

- [ ] **Step 1: Write the failing tests**

Add to `backend/tests/test_core.py`:

```python
def test_credential_manager_set_get():
    repo = InMemoryCredentialRepo()
    mgr = CredentialManager(repo, key_path="/tmp/test_cred.key")
    mgr.set("neon", "NEON_API_KEY", "sk-123")
    val = mgr.get("neon", "NEON_API_KEY")
    assert val == "sk-123"

def test_credential_manager_get_nonexistent():
    repo = InMemoryCredentialRepo()
    mgr = CredentialManager(repo, key_path="/tmp/test_cred.key")
    assert mgr.get("neon", "NONEXISTENT") is None

def test_credential_manager_encryption_at_rest():
    import tempfile, os
    with tempfile.NamedTemporaryFile(suffix=".key", delete=False) as f:
        key_path = f.name
    try:
        repo = InMemoryCredentialRepo()
        mgr = CredentialManager(repo, key_path=key_path)
        mgr.set("github", "TOKEN", "ghp_12345")
        # The value stored in repo should be encrypted (not plaintext)
        stored = repo.get("github", "TOKEN")
        assert stored != "ghp_12345"
        assert stored is not None
        assert not stored.startswith("ghp_")
    finally:
        os.unlink(key_path)

def test_credential_manager_get_env_dict():
    repo = InMemoryCredentialRepo()
    mgr = CredentialManager(repo, key_path="/tmp/test_cred.key")
    mgr.set("neon", "NEON_API_KEY", "sk-123")
    mgr.set("github", "GITHUB_TOKEN", "ghp-abc")
    env = mgr.get_env_dict()
    assert env["NEON_API_KEY"] == "sk-123"
    assert env["GITHUB_TOKEN"] == "ghp-abc"

def test_credential_manager_delete():
    repo = InMemoryCredentialRepo()
    mgr = CredentialManager(repo, key_path="/tmp/test_cred.key")
    mgr.set("neon", "KEY", "val")
    assert mgr.get("neon", "KEY") == "val"
    mgr.delete("neon", "KEY")
    assert mgr.get("neon", "KEY") is None

def test_credential_manager_get_all():
    repo = InMemoryCredentialRepo()
    mgr = CredentialManager(repo, key_path="/tmp/test_cred.key")
    mgr.set("neon", "NEON_API_KEY", "sk-1")
    mgr.set("neon", "OTHER", "val-2")
    all_creds = mgr.get_all("neon")
    assert all_creds == {"NEON_API_KEY": "sk-1", "OTHER": "val-2"}

def test_credential_manager_persistent_key():
    import tempfile, os
    with tempfile.NamedTemporaryFile(suffix=".key", delete=False) as f:
        key_path = f.name
    try:
        repo = InMemoryCredentialRepo()
        mgr1 = CredentialManager(repo, key_path=key_path)
        mgr1.set("neon", "KEY", "secret")
        mgr2 = CredentialManager(repo, key_path=key_path)
        assert mgr2.get("neon", "KEY") == "secret"
    finally:
        os.unlink(key_path)
```

- [ ] **Step 2: Add import for CredentialManager**

Add to test imports:
```python
from backend.core.credential_manager import CredentialManager
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd /home/viniciusfigueiredo/Documentos/MCPs/backend && python3 -m pytest tests/test_core.py::test_credential_manager_set_get -x -v 2>&1 | head -10`
Expected: ImportError for CredentialManager

- [ ] **Step 4: Create CredentialManager**

```python
"""Core credential management — encryption/decryption orchestration."""

import os
from pathlib import Path
from cryptography.fernet import Fernet
from backend.core.ports import CredentialRepository


CREDENTIAL_SCHEMA: dict[str, list[str]] = {
    "neon":         ["NEON_API_KEY"],
    "exa":          ["EXA_API_KEY"],
    "sentry":       ["SENTRY_AUTH_TOKEN"],
    "github":       ["GITHUB_PERSONAL_ACCESS_TOKEN"],
    "dockerhub":    ["HUB_PAT_TOKEN", "dockerhub.username"],
    "filesystem":   ["filesystem.paths"],
}


class CredentialManager:
    """Encrypts/decrypts credentials and delegates storage to a repository."""

    def __init__(self, repo: CredentialRepository, key_path: str):
        self._repo = repo
        self._key_path = key_path
        self._fernet = self._load_or_create_key()

    def set(self, server: str, key: str, value: str) -> None:
        encrypted = self._fernet.encrypt(value.encode())
        self._repo.upsert(server, key, encrypted.decode())

    def get(self, server: str, key: str) -> str | None:
        encrypted = self._repo.get(server, key)
        if encrypted is None:
            return None
        return self._fernet.decrypt(encrypted.encode()).decode()

    def get_all(self, server: str) -> dict[str, str]:
        result = {}
        for key in self._repo.list_keys(server):
            val = self.get(server, key)
            if val is not None:
                result[key] = val
        return result

    def get_env_dict(self) -> dict[str, str]:
        env = {}
        for server in self._repo.list_servers():
            for key, val in self.get_all(server).items():
                env[key] = val
        return env

    def delete(self, server: str, key: str) -> None:
        self._repo.delete(server, key)

    def _load_or_create_key(self) -> Fernet:
        path = Path(self._key_path)
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(Fernet.generate_key().decode())
            path.chmod(0o600)
        return Fernet(path.read_text().encode())

    @staticmethod
    def is_allowed(server: str, key: str) -> bool:
        return key in CREDENTIAL_SCHEMA.get(server, [])

    @staticmethod
    def get_schema() -> dict[str, list[str]]:
        return dict(CREDENTIAL_SCHEMA)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /home/viniciusfigueiredo/Documentos/MCPs/backend && python3 -m pytest tests/test_core.py::test_credential_manager_set_get tests/test_core.py::test_credential_manager_get_nonexistent tests/test_core.py::test_credential_manager_encryption_at_rest tests/test_core.py::test_credential_manager_get_env_dict tests/test_core.py::test_credential_manager_delete tests/test_core.py::test_credential_manager_get_all tests/test_core.py::test_credential_manager_persistent_key -v`
Expected: 7 passed

- [ ] **Step 6: Commit**

```bash
git add backend/core/credential_manager.py backend/tests/test_core.py
git commit -m "feat: add CredentialManager with Fernet encryption"
```

---

### Task 6: Update GatewayService

**Files:**
- Modify: `backend/core/services.py`

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_core.py`:

```python
def test_credentials_restart_with_env(tmp_path):
    repo = InMemoryCredentialRepo()
    key_path = str(tmp_path / "test.key")
    cm = CredentialManager(repo, key_path=key_path)
    cm.set("neon", "NEON_API_KEY", "sk-123")
    env = cm.get_env_dict()
    assert env == {"NEON_API_KEY": "sk-123"}
```

- [ ] **Step 2: Modify GatewayService constructor**

In `backend/core/services.py`:
1. Add import for `CredentialManager`
2. Add optional `cred_manager` parameter to `__init__`
3. Expose as property

Updated `__init__`:
```python
from backend.core.credential_manager import CredentialManager

class GatewayService:
    def __init__(
        self,
        catalog: CatalogRepository,
        state_repo: StateRepository,
        profile: ProfileSync,
        gateway: GatewayController,
        conn_repo: ConnectionRepository | None = None,
        cred_manager: CredentialManager | None = None,
    ):
        self._catalog = catalog
        self._state_repo = state_repo
        self._profile = profile
        self._gateway = gateway
        self._conn_repo = conn_repo
        self._cred_manager = cred_manager
```

Add property:
```python
    @property
    def cred_manager(self) -> CredentialManager | None:
        return self._cred_manager
```

- [ ] **Step 3: Run existing tests to verify nothing broke**

Run: `cd /home/viniciusfigueiredo/Documentos/MCPs/backend && python3 -m pytest tests/ -v`
Expected: All existing tests pass (should be ~27+)

- [ ] **Step 4: Commit**

```bash
git add backend/core/services.py
git commit -m "feat: add cred_manager to GatewayService"
```

---

### Task 7: Add FastAPI credential routes

**Files:**
- Modify: `backend/main.py`
- Modify: `backend/tests/test_api.py`

- [ ] **Step 1: Write the failing API test**

Add to `backend/tests/test_api.py`:

```python
def test_credentials_list_empty(client):
    resp = client.get("/api/credentials")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)

def test_credentials_set_and_list(client):
    resp = client.put("/api/credentials/neon", json={"key": "NEON_API_KEY", "value": "sk-123"})
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
    # Verify it appears in list
    resp2 = client.get("/api/credentials")
    assert resp2.status_code == 200
    data = resp2.json()
    assert "neon" in data
    assert data["neon"].get("NEON_API_KEY") is True

def test_credentials_set_invalid_key(client):
    resp = client.put("/api/credentials/neon", json={"key": "INVALID_KEY", "value": "x"})
    assert resp.status_code == 400

def test_credentials_delete(client):
    client.put("/api/credentials/neon", json={"key": "NEON_API_KEY", "value": "sk-123"})
    resp = client.delete("/api/credentials/neon/NEON_API_KEY")
    assert resp.status_code == 200
    # Verify gone
    resp2 = client.get("/api/credentials")
    data = resp2.json()
    assert data.get("neon", {}).get("NEON_API_KEY") is False
```

You'll need a FastAPI `TestClient` fixture. Add near the top:

```python
import pytest
from fastapi.testclient import TestClient
```

And add this fixture (reuse if one exists):

```python
@pytest.fixture
def client():
    # Override to use in-memory
    from backend.main import app
    return TestClient(app)
```

- [ ] **Step 2: Run API tests to verify they fail**

Run: `cd /home/viniciusfigueiredo/Documentos/MCPs/backend && python3 -m pytest tests/test_api.py::test_credentials_list_empty -x -v 2>&1 | head -15`
Expected: 404 or method not found

- [ ] **Step 3: Add credential routes to main.py**

Add near the other imports:
```python
from backend.core.credential_manager import CredentialManager, CREDENTIAL_SCHEMA
from backend.adapters.credential_repo import SqliteCredentialRepo
from pydantic import BaseModel
```

Add Pydantic model:
```python
class CredentialBody(BaseModel):
    key: str
    value: str
```

Update `build_service()` to wire up CredentialManager:
```python
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
    # Credential manager
    cred_repo = SqliteCredentialRepo(db)
    key_path = os.path.expanduser("~/.config/gmcp/credentials.key")
    cred_manager = CredentialManager(cred_repo, key_path=key_path)
    return GatewayService(
        catalog=catalog,
        state_repo=state_repo,
        profile=profile,
        gateway=gateway,
        conn_repo=conn_repo,
        cred_manager=cred_manager,
    )
```

Add credential routes (before the `if __name__` block):

```python
# ── Credentials ────────────────────────────────────────────────────


@app.get("/api/credentials")
def list_credentials():
    """List servers and which keys have values (never exposes decrypted values)."""
    cm = svc.cred_manager
    if cm is None:
        return {}
    result: dict[str, dict[str, bool]] = {}
    schema = cm.get_schema()
    for server, keys in schema.items():
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
def set_credential(server: str, body: CredentialBody):
    """Set a credential value (encrypted before storage)."""
    cm = svc.cred_manager
    if cm is None:
        raise HTTPException(503, "Credential manager not available")
    if not cm.is_allowed(server, body.key):
        raise HTTPException(400, f"Key '{body.key}' not valid for server '{server}'")
    cm.set(server, body.key, body.value)
    return {"ok": True}


@app.delete("/api/credentials/{server}/{key}")
def delete_credential(server: str, key: str):
    """Remove a stored credential."""
    cm = svc.cred_manager
    if cm is None:
        raise HTTPException(503, "Credential manager not available")
    cm.delete(server, key)
    return {"ok": True}
```

- [ ] **Step 4: Run API tests to verify they pass**

Run: `cd /home/viniciusfigueiredo/Documentos/MCPs/backend && python3 -m pytest tests/test_api.py::test_credentials_list_empty tests/test_api.py::test_credentials_set_and_list tests/test_api.py::test_credentials_set_invalid_key tests/test_api.py::test_credentials_delete -v`
Expected: 4 passed

- [ ] **Step 5: Run all backend tests to verify nothing broke**

Run: `cd /home/viniciusfigueiredo/Documentos/MCPs/backend && python3 -m pytest tests/ -v`
Expected: All tests pass

- [ ] **Step 6: Commit**

```bash
git add backend/main.py backend/tests/test_api.py
git commit -m "feat: add credential CRUD API endpoints"
```

---

### Task 8: Update start-gateway.sh

**Files:**
- Modify: `start-gateway.sh`

- [ ] **Step 1: Add credential injection to start-gateway.sh**

Replace the file content with:

```bash
#!/bin/bash

export MCP_GATEWAY_AUTH_TOKEN="mcp-local-token"
PIDFILE="/tmp/gmcp-gateway.pid"

# Mata gateway anterior se existir
if [ -f "$PIDFILE" ] && kill -0 $(cat "$PIDFILE") 2>/dev/null; then
    OLD_PID=$(cat "$PIDFILE")
    echo "Matando gateway antigo (PID $OLD_PID)..."
    kill -9 "$OLD_PID" 2>/dev/null
    sleep 1
fi

# Remove containers órfãos
docker rm -f $(docker ps -aq --filter "label=docker-mcp=true") 2>/dev/null
sleep 1

# ── Exporta credenciais criptografadas do BD ──
eval $(python3 -c "
import os, sys
sys.path.insert(0, os.path.expanduser('~/Documentos/MCPs'))
from backend.adapters.credential_repo import SqliteCredentialRepo
from backend.core.credential_manager import CredentialManager
db_path = os.path.expanduser('~/.docker/mcp/mcp-toolkit.db')
key_path = os.path.expanduser('~/.config/gmcp/credentials.key')
cm = CredentialManager(SqliteCredentialRepo(db_path), key_path=key_path)
for k, v in cm.get_env_dict().items():
    print(f'export {k}={v!r}')
" 2>/dev/null) || echo "⚠️ Nenhuma credencial encontrada no BD"

# Sobe gateway usando profile
docker mcp gateway run \
  --profile profile \
  --transport sse \
  --port 3099 \
  --long-lived &
GATEWAY_PID=$!
echo "$GATEWAY_PID" > "$PIDFILE"
echo "Gateway iniciado (PID $GATEWAY_PID)"

wait "$GATEWAY_PID"
```

- [ ] **Step 2: Make script executable**

Run: `chmod +x start-gateway.sh && echo "OK"`
Expected: OK

- [ ] **Step 3: Commit**

```bash
git add start-gateway.sh
git commit -m "fix: add credential injection to start-gateway.sh"
```

---

### Task 9: Update TUI — add credentials tab

**Files:**
- Modify: `mcp-tui.py`

- [ ] **Step 1: Understand current TUI structure**

The TUI has 5 tabs (0-4): Home, MCPS, Market, Integrations, Logs.

The credentials tab will be tab 3 (replacing integrations at 3, pushing integrations to 4 and logs to 5).

Actually, looking at the current layout:
- Tab 0: Home
- Tab 1: MCPS
- Tab 2: Market
- Tab 3: Integrations
- Tab 4: Logs

We need to add credentials at tab 3:
- Tab 0: Home
- Tab 1: MCPS
- Tab 2: Market
- Tab 3: Credentials (NEW)
- Tab 4: Integrations (was 3)
- Tab 5: Logs (was 4)

- [ ] **Step 2: Modify tab_bar**

Change `tab_bar` to add "Credenciais 🔑" tab:

```python
def tab_bar(self):
    tabs=[_("tab.home"),_("tab.mcps"),_("tab.market"),_("tab.credentials"),_("tab.integrations"),_("tab.logs")]
    # ... rest stays the same (the loop handles any number of tabs)
```

- [ ] **Step 3: Update tab indices handling**

In `handle_input`, update which arrow keys (1-5 → 1-6) and add handling for the new tab.

In `run` method's draw loop:
```python
if self.tab==0: self.draw_home()
elif self.tab==1: self.draw_mcps()
elif self.tab==2: self.draw_market()
elif self.tab==3: self.draw_credentials()
elif self.tab==4: self.draw_integrations()
elif self.tab==5: self.draw_logs()
```

In `_status_msg`:
```python
if self.tab==3: return _("status.credentials")
if self.tab==4: ...
if self.tab==5: ...
```

- [ ] **Step 4: Add draw_credentials method**

Add before `draw_integrations`:

```python
def draw_credentials(self):
    self.draw_header()
    y = 10
    self.sa(y, 2, _("credentials.title"), curses.A_BOLD)
    self.sa(y, 22, _("credentials.hint"), curses.A_DIM)
    y += 1

    # ── Server cards grid ──
    schema = {
        "neon":       ["NEON_API_KEY"],
        "exa":        ["EXA_API_KEY"],
        "sentry":     ["SENTRY_AUTH_TOKEN"],
        "github":     ["GITHUB_PERSONAL_ACCESS_TOKEN"],
        "dockerhub":  ["HUB_PAT_TOKEN", "dockerhub.username"],
        "filesystem": ["filesystem.paths"],
    }
    servers = sorted(schema.keys())
    card_w = 16
    card_h = 4
    cols = max(1, (self.w - 4) // (card_w + 2))
    row = y
    for idx, server in enumerate(servers):
        cx = 2 + (idx % cols) * (card_w + 2)
        cy = row + (idx // cols) * (card_h + 1)
        # Fill status
        filled = 0
        total = len(schema[server])
        for k in schema[server]:
            v = None
            try:
                cm = _svc.cred_manager
                if cm:
                    v = cm.get(server, k)
            except Exception:
                pass
            if v is not None:
                filled += 1
        # Draw card
        selected = (idx == self.cred_cursor)
        if selected:
            self.stdscr.attron(curses.color_pair(4))
        self.sa(cy, cx, f"┌{'─' * (card_w - 2)}┐")
        self.sa(cy + 1, cx, f"│ {server[:14].ljust(14)} │")
        lock_str = " ".join(["🔒" if filled > i else "🔓" for i in range(total)])
        self.sa(cy + 2, cx, f"│ {lock_str.ljust(card_w - 3)}│")
        self.sa(cy + 3, cx, f"└{'─' * (card_w - 2)}┘")
        if selected:
            self.stdscr.attroff(curses.color_pair(4))

    # ── Detail form ──
    form_y = row + ((len(servers) - 1) // cols + 1) * (card_h + 1) + 1
    if form_y < self.h - 6 and servers and 0 <= self.cred_cursor < len(servers):
        sel_server = servers[self.cred_cursor]
        sel_keys = schema[sel_server]
        self.sa(form_y, 2, "─" * (self.w - 6), curses.A_DIM)
        form_y += 1
        self.sa(form_y, 4, f" {sel_server}", curses.A_BOLD | curses.color_pair(3))
        form_y += 1

        for ki, key in enumerate(sel_keys):
            label = key
            current_val = ""
            try:
                cm = _svc.cred_manager
                if cm:
                    cv = cm.get(sel_server, key)
                    if cv:
                        current_val = "********"
            except Exception:
                pass
            # Key label
            self.sa(form_y, 6, label, curses.A_DIM)
            # Value field
            field = self.cred_fields.get(key, current_val or "")
            display = field if field else "(vazio)"
            is_editing = (ki == self.cred_field_idx and self.cred_editing)
            if is_editing:
                self.sa(form_y, 6 + len(label) + 2, f" {display} ", curses.A_REVERSE)
            else:
                self.sa(form_y, 6 + len(label) + 2, f" {display} ", curses.A_NORMAL)
            form_y += 1

        # Save button hint
        self.sa(form_y, 6, "[Ctrl+S] Salvar  [Del] Limpar  [Esc] Sair", curses.A_DIM)
```

- [ ] **Step 5: Add credential-specific instance variables**

Add to `__init__`:
```python
self.cred_cursor = 0
self.cred_fields: dict[str, str] = {}
self.cred_field_idx = 0
self.cred_editing = False
```

- [ ] **Step 6: Add credential key handling**

In `handle_input`, add credential tab handling (before integrations tab):

```python
elif self.tab == 3:
    schema_list = sorted([k for k in {
        "neon": ["NEON_API_KEY"], "exa": ["EXA_API_KEY"],
        "sentry": ["SENTRY_AUTH_TOKEN"], "github": ["GITHUB_PERSONAL_ACCESS_TOKEN"],
        "dockerhub": ["HUB_PAT_TOKEN", "dockerhub.username"],
        "filesystem": ["filesystem.paths"],
    }.keys()])
    if not schema_list:
        return True
    if key == curses.KEY_UP and self.cred_cursor > 0:
        self.cred_cursor -= 1
        self.cred_field_idx = 0
        self.cred_editing = False
    elif key == curses.KEY_DOWN and self.cred_cursor < len(schema_list) - 1:
        self.cred_cursor += 1
        self.cred_field_idx = 0
        self.cred_editing = False
    elif key == ord('\t') or key == curses.KEY_RIGHT:
        self.cred_editing = False
        self.cred_field_idx += 1
    elif key == curses.KEY_LEFT:
        self.cred_editing = False
        self.cred_field_idx = max(0, self.cred_field_idx - 1)
    elif key == ord('\n') or key == ord(' '):
        self.cred_editing = not self.cred_editing
    elif key == 127 or key == curses.KEY_BACKSPACE:
        if self.cred_editing:
            server = schema_list[self.cred_cursor]
            keys = {
                "neon": ["NEON_API_KEY"], "exa": ["EXA_API_KEY"],
                "sentry": ["SENTRY_AUTH_TOKEN"], "github": ["GITHUB_PERSONAL_ACCESS_TOKEN"],
                "dockerhub": ["HUB_PAT_TOKEN", "dockerhub.username"],
                "filesystem": ["filesystem.paths"],
            }[server]
            if self.cred_field_idx < len(keys):
                k = keys[self.cred_field_idx]
                self.cred_fields[k] = self.cred_fields.get(k, "")[:-1]
    elif 32 <= key < 127 and self.cred_editing:
        server = schema_list[self.cred_cursor]
        keys = {
            "neon": ["NEON_API_KEY"], "exa": ["EXA_API_KEY"],
            "sentry": ["SENTRY_AUTH_TOKEN"], "github": ["GITHUB_PERSONAL_ACCESS_TOKEN"],
            "dockerhub": ["HUB_PAT_TOKEN", "dockerhub.username"],
            "filesystem": ["filesystem.paths"],
        }[server]
        if self.cred_field_idx < len(keys):
            k = keys[self.cred_field_idx]
            self.cred_fields[k] = self.cred_fields.get(k, "") + chr(key)
    elif key == 27:  # ESC
        self.cred_fields = {}
        self.cred_editing = False
    elif key in (ord('s'), ord('S')) and not self.cred_editing:
        # Save all fields for current server
        self._save_credentials(schema_list[self.cred_cursor])
    elif key == ord('d'):
        # Delete all fields for current server
        self._delete_credentials(schema_list[self.cred_cursor])
```

- [ ] **Step 7: Add save/delete helper methods**

```python
def _save_credentials(self, server: str):
    schema = {
        "neon": ["NEON_API_KEY"], "exa": ["EXA_API_KEY"],
        "sentry": ["SENTRY_AUTH_TOKEN"], "github": ["GITHUB_PERSONAL_ACCESS_TOKEN"],
        "dockerhub": ["HUB_PAT_TOKEN", "dockerhub.username"],
        "filesystem": ["filesystem.paths"],
    }
    keys = schema.get(server, [])
    cm = _svc.cred_manager
    if cm is None:
        self.msg = "Credential manager unavailable"
        self.msg_tick = time.time() + 3
        return
    saved = 0
    for k in keys:
        val = self.cred_fields.get(k, "").strip()
        if val:
            cm.set(server, k, val)
            saved += 1
    self.cred_fields = {}
    self.msg = _("credentials.saved") if saved else _("credentials.empty_skip")
    self.msg_tick = time.time() + 3

def _delete_credentials(self, server: str):
    schema = {
        "neon": ["NEON_API_KEY"], "exa": ["EXA_API_KEY"],
        "sentry": ["SENTRY_AUTH_TOKEN"], "github": ["GITHUB_PERSONAL_ACCESS_TOKEN"],
        "dockerhub": ["HUB_PAT_TOKEN", "dockerhub.username"],
        "filesystem": ["filesystem.paths"],
    }
    keys = schema.get(server, [])
    cm = _svc.cred_manager
    if cm is None:
        return
    for k in keys:
        cm.delete(server, k)
    self.cred_fields = {}
    self.msg = _("credentials.cleared")
    self.msg_tick = time.time() + 3
```

- [ ] **Step 8: Update tab count in input handler**

Update tab switching keys:
```python
elif key==ord('1'): self.tab=0; self.cursor=0
elif key==ord('2'): self.tab=1; self.cursor=0
elif key==ord('3'): self.tab=2; self.market_cursor=0
elif key==ord('4'): self.tab=3
elif key==ord('5'): self.tab=4
elif key==ord('6'): self.tab=5
```

Also in mouse click handler, update tab positions:
```python
if my==0:
    xs=[2,10,18,26,34,42]
    for i,x in enumerate(xs):
        if x<=mx<x+8: self.tab=i
    return True
```

- [ ] **Step 9: Verify TUI syntax**

Run: `python3 -c "import py_compile; py_compile.compile('mcp-tui.py', doraise=True)"`
Expected: No errors

- [ ] **Step 10: Commit**

```bash
git add mcp-tui.py
git commit -m "feat: add credentials tab to TUI"
```

---

### Task 10: Create Vue 3 credentials store and types

**Files:**
- Create: `src/stores/credentials.ts`
- Modify: `src/types/index.ts`
- Modify: `src/api/index.ts`

- [ ] **Step 1: Add CredentialEntry type**

Add to `src/types/index.ts`:
```typescript
export interface CredentialEntry {
  server: string
  key: string
  has_value: boolean
}
```

- [ ] **Step 2: Add API methods**

Add to `src/api/index.ts`:
```typescript
credentials: {
  list: () => request<Record<string, Record<string, boolean>>>('/credentials'),
  set: (server: string, key: string, value: string) =>
    request<{ ok: boolean }>(`/credentials/${encodeURIComponent(server)}`, {
      method: 'PUT',
      body: JSON.stringify({ key, value }),
    }),
  delete: (server: string, key: string) =>
    request<{ ok: boolean }>(`/credentials/${encodeURIComponent(server)}/${encodeURIComponent(key)}`, {
      method: 'DELETE',
    }),
},
```

- [ ] **Step 3: Create Pinia store**

`src/stores/credentials.ts`:
```typescript
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '@/api'

export const useCredentialsStore = defineStore('credentials', () => {
  const credentials = ref<Record<string, Record<string, boolean>>>({})
  const saving = ref(false)
  const message = ref<string | null>(null)

  async function fetchCredentials() {
    try {
      credentials.value = await api.credentials.list()
    } catch (e) {
      credentials.value = {}
      message.value = e instanceof Error ? e.message : 'Failed to fetch'
    }
  }

  async function setCredential(server: string, key: string, value: string) {
    saving.value = true
    try {
      await api.credentials.set(server, key, value)
      await fetchCredentials()
      message.value = 'Credencial salva!'
    } catch (e) {
      message.value = e instanceof Error ? e.message : 'Error saving'
      throw e
    } finally {
      saving.value = false
    }
  }

  async function deleteCredential(server: string, key: string) {
    saving.value = true
    try {
      await api.credentials.delete(server, key)
      await fetchCredentials()
      message.value = 'Credencial removida!'
    } catch (e) {
      message.value = e instanceof Error ? e.message : 'Error deleting'
      throw e
    } finally {
      saving.value = false
    }
  }

  function clearMessage() {
    message.value = null
  }

  return {
    credentials,
    saving,
    message,
    fetchCredentials,
    setCredential,
    deleteCredential,
    clearMessage,
  }
})
```

- [ ] **Step 4: Verify TypeScript compilation**

Run: `cd /home/viniciusfigueiredo/Documentos/MCPs && npx vue-tsc --noEmit 2>&1 | head -20`
Expected: No errors (or minor type issues)

- [ ] **Step 5: Commit**

```bash
git add src/types/index.ts src/api/index.ts src/stores/credentials.ts
git commit -m "feat: add credentials store and API methods"
```

---

### Task 11: Create CredentialsView.vue

**Files:**
- Create: `src/views/CredentialsView.vue`

- [ ] **Step 1: Create the Vue component**

```vue
<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useCredentialsStore } from '@/stores/credentials'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
const store = useCredentialsStore()

const CREDENTIAL_SCHEMA: Record<string, string[]> = {
  neon: ['NEON_API_KEY'],
  exa: ['EXA_API_KEY'],
  sentry: ['SENTRY_AUTH_TOKEN'],
  github: ['GITHUB_PERSONAL_ACCESS_TOKEN'],
  dockerhub: ['HUB_PAT_TOKEN', 'dockerhub.username'],
  filesystem: ['filesystem.paths'],
}

const selectedServer = ref('')
const selectedKey = ref('')
const inputValue = ref('')
const showValue = ref(false)
const editing = ref(false)

const servers = computed(() => Object.keys(CREDENTIAL_SCHEMA))

function selectServer(server: string) {
  selectedServer.value = server
  selectedKey.value = CREDENTIAL_SCHEMA[server][0]
  inputValue.value = ''
  showValue.value = false
  editing.value = false
}

function selectKey(key: string) {
  selectedKey.value = key
  inputValue.value = ''
  showValue.value = false
  editing.value = false
}

async function save() {
  if (!selectedServer.value || !selectedKey.value || !inputValue.value.trim()) return
  try {
    await store.setCredential(selectedServer.value, selectedKey.value, inputValue.value)
    inputValue.value = ''
    editing.value = false
  } catch { /* message handled by store */ }
}

async function remove() {
  if (!selectedServer.value || !selectedKey.value) return
  try {
    await store.deleteCredential(selectedServer.value, selectedKey.value)
    inputValue.value = ''
  } catch { /* message handled by store */ }
}

function hasValue(server: string, key: string): boolean {
  return store.credentials[server]?.[key] ?? false
}

onMounted(() => {
  store.fetchCredentials()
})
</script>

<template>
  <div class="p-6 max-w-5xl mx-auto">
    <h1 class="text-2xl font-bold mb-2">{{ t('credentials.title') }}</h1>
    <p class="text-sm text-gray-500 dark:text-gray-400 mb-6">{{ t('credentials.hint') }}</p>

    <!-- Message toast -->
    <div v-if="store.message"
      class="mb-4 px-4 py-2 rounded bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 flex justify-between items-center">
      <span>{{ store.message }}</span>
      <button @click="store.clearMessage()" class="ml-2 font-bold">&times;</button>
    </div>

    <!-- Loading -->
    <div v-if="store.saving" class="text-sm text-gray-400 mb-4">{{ t('loading') }}</div>

    <!-- Server cards grid -->
    <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4 mb-8">
      <button v-for="server in servers" :key="server" @click="selectServer(server)"
        :class="[
          'border rounded-lg p-4 text-center transition-all cursor-pointer',
          selectedServer === server
            ? 'border-blue-500 ring-2 ring-blue-300 dark:ring-blue-700'
            : 'border-gray-200 dark:border-gray-700 hover:border-blue-300'
        ]">
        <div class="font-medium text-sm mb-1">{{ server }}</div>
        <div class="flex justify-center gap-1 text-sm">
          <span v-for="key in CREDENTIAL_SCHEMA[server]" :key="key">
            {{ hasValue(server, key) ? '🔒' : '🔓' }}
          </span>
        </div>
      </button>
    </div>

    <!-- Detail form -->
    <div v-if="selectedServer" class="border border-gray-200 dark:border-gray-700 rounded-lg p-6">
      <h3 class="text-lg font-semibold mb-2">{{ selectedServer }}</h3>

      <!-- Key selector -->
      <div class="flex gap-2 mb-4 flex-wrap">
        <button v-for="key in CREDENTIAL_SCHEMA[selectedServer]" :key="key"
          @click="selectKey(key)"
          :class="[
            'px-3 py-1 rounded text-sm border transition-colors',
            selectedKey === key
              ? 'bg-blue-500 text-white border-blue-500'
              : 'bg-gray-100 dark:bg-gray-800 border-gray-300 dark:border-gray-600'
          ]">
          {{ key }}
          <span class="ml-1">{{ hasValue(selectedServer, key) ? '🔒' : '🔓' }}</span>
        </button>
      </div>

      <!-- Input field -->
      <div class="flex items-center gap-2 mb-4">
        <input :type="showValue ? 'text' : 'password'"
          v-model="inputValue"
          :placeholder="t('credentials.value_placeholder')"
          @focus="editing = true"
          class="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-800 text-sm" />
        <button @click="showValue = !showValue" class="px-2 py-1 text-sm border rounded hover:bg-gray-100 dark:hover:bg-gray-700">
          {{ showValue ? '🙈' : '👁️' }}
        </button>
      </div>

      <!-- Action buttons -->
      <div class="flex gap-2">
        <button @click="save" :disabled="!inputValue.trim() || store.saving"
          class="px-4 py-2 bg-blue-500 text-white rounded text-sm hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed">
          {{ t('credentials.save') }}
        </button>
        <button @click="remove" :disabled="!hasValue(selectedServer, selectedKey) || store.saving"
          class="px-4 py-2 bg-red-500 text-white rounded text-sm hover:bg-red-600 disabled:opacity-50 disabled:cursor-not-allowed">
          {{ t('credentials.clear') }}
        </button>
      </div>
    </div>

    <!-- Empty state -->
    <div v-else class="text-center py-12 text-gray-400">
      {{ t('credentials.select_hint') }}
    </div>
  </div>
</template>
```

- [ ] **Step 2: Verify component compiles**

Run: `cd /home/viniciusfigueiredo/Documentos/MCPs && npx vue-tsc --noEmit 2>&1 | head -20`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add src/views/CredentialsView.vue
git commit -m "feat: add CredentialsView Vue component"
```

---

### Task 12: Add route and navigation

**Files:**
- Modify: `src/router/index.ts`

- [ ] **Step 1: Add credentials route**

```typescript
{ path: '/credentials', name: 'credentials', component: () => import('@/views/CredentialsView.vue') },
```

- [ ] **Step 2: Verify routing works**

The active nav items in other components should be updated if there's a navigation bar. Check if there's a shared nav component.

Run: `grep -r "CredentialsView\|/credentials" src/ --include="*.vue" --include="*.ts"`
Expected: No existing reference

- [ ] **Step 3: Commit**

```bash
git add src/router/index.ts
git commit -m "feat: add /credentials route"
```

---

### Task 13: Update i18n

**Files:**
- Modify: `src/locales/pt-BR.json`
- Modify: `src/locales/en-US.json`

- [ ] **Step 1: Add pt-BR translations**

Add to `src/locales/pt-BR.json`:
```json
"tab.credentials": "Credenciais 🔑",
"tab.logs": "Logs",
"credentials.title": "Gerenciar Credenciais",
"credentials.hint": "Configure API keys e tokens dos servidores MCP",
"credentials.value_placeholder": "Digite o valor da credencial...",
"credentials.save": "Salvar",
"credentials.clear": "Limpar",
"credentials.select_hint": "Selecione um servidor acima para gerenciar suas credenciais",
"credentials.saved": "Credenciais salvas com sucesso!",
"credentials.cleared": "Credenciais removidas!",
"credentials.empty_skip": "Nenhum valor para salvar (campos vazios ignorados)",
"status.credentials": "Use Tab/setas para navegar, Enter para editar, Ctrl+S salvar, Del limpar"
```

- [ ] **Step 2: Add en-US translations**

Add to `src/locales/en-US.json`:
```json
"tab.credentials": "Credentials 🔑",
"tab.logs": "Logs",
"credentials.title": "Manage Credentials",
"credentials.hint": "Configure API keys and tokens for MCP servers",
"credentials.value_placeholder": "Enter credential value...",
"credentials.save": "Save",
"credentials.clear": "Clear",
"credentials.select_hint": "Select a server above to manage its credentials",
"credentials.saved": "Credentials saved successfully!",
"credentials.cleared": "Credentials removed!",
"credentials.empty_skip": "No value to save (empty fields skipped)",
"status.credentials": "Tab/arrows to navigate, Enter to edit, Ctrl+S save, Del clear"
```

- [ ] **Step 3: Add TUI i18n keys to backend/core/i18n.py**

Add to the `pt-BR` dict in `backend/core/i18n.py`:
```python
"tab.credentials": "Credenciais 🔑",
"credentials.title": "Gerenciar Credenciais",
"credentials.hint": "Use Tab/setas para navegar, Enter para editar, Ctrl+S para salvar, Del para limpar",
"credentials.saved": "Credenciais salvas!",
"credentials.cleared": "Credenciais removidas!",
"credentials.empty_skip": "Nenhum valor para salvar",
"status.credentials": "Credenciais — [Tab/setas] navega  [Enter] edita  [Ctrl+S] salvar  [Del] limpar",
```

Add to the `en-US` dict in `backend/core/i18n.py`:
```python
"tab.credentials": "Credentials 🔑",
"credentials.title": "Manage Credentials",
"credentials.hint": "Tab/arrows to navigate, Enter to edit, Ctrl+S to save, Del to clear",
"credentials.saved": "Credentials saved!",
"credentials.cleared": "Credentials removed!",
"credentials.empty_skip": "No value to save",
"status.credentials": "Credentials — [Tab/arrows] nav  [Enter] edit  [Ctrl+S] save  [Del] clear",
```

Also update the `__init__` of the `I18n` class? No — the dict-based locale system handles new keys automatically (they get looked up via `.get()`).

- [ ] **Step 4: Commit**

```bash
git add src/locales/pt-BR.json src/locales/en-US.json
git commit -m "feat: add credentials i18n translations"
```

---

### Task 14: Full integration test

**Files:**
- N/A (verification)

- [ ] **Step 1: Run all backend tests**

Run: `cd /home/viniciusfigueiredo/Documentos/MCPs/backend && python3 -m pytest tests/ -v`
Expected: All tests pass

- [ ] **Step 2: Run frontend tests**

Run: `cd /home/viniciusfigueiredo/Documentos/MCPs && npx vitest run 2>&1`
Expected: All tests pass

- [ ] **Step 3: Verify backend starts**

Run: `cd /home/viniciusfigueiredo/Documentos/MCPs && timeout 5 python3 -m uvicorn backend.main:app --port 8001 2>&1 | head -5`
Expected: FastAPI starts on port 8001

- [ ] **Step 4: Verify the credential endpoints**

Run:
```bash
# Test set
curl -s -X PUT http://localhost:8001/api/credentials/neon \
  -H "Content-Type: application/json" \
  -d '{"key":"NEON_API_KEY","value":"sk-test"}' | python3 -m json.tool

# Test list
curl -s http://localhost:8001/api/credentials | python3 -m json.tool
```
Expected: Both succeed and show the credential is set

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "feat: complete credentials management with encrypted storage, TUI and Web UIs"
```

---

## Verification Checklist

- [ ] All backend tests pass
- [ ] All frontend tests pass
- [ ] `GET /api/credentials` returns servers with key status
- [ ] `PUT /api/credentials/{server}` encrypts and stores value
- [ ] `DELETE /api/credentials/{server}/{key}` removes value
- [ ] TUI shows credential tab with server cards and edit form
- [ ] Web UI shows credential view at `/credentials`
- [ ] `start-gateway.sh` exports credentials as env vars
- [ ] Credentials are encrypted at rest (Fernet AES-256)
- [ ] Master key is auto-generated at `~/.config/gmcp/credentials.key`
- [ ] API never returns plaintext credential values
