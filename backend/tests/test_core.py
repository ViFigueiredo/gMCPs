"""TDD: Core service tests with in-memory adapters."""

import pytest
from backend.core.entities import ServerInfo, GatewayState, Stats, LogEntry
from backend.core.ports import (
    CatalogRepository,
    StateRepository,
    ProfileSync,
    GatewayController,
    CredentialRepository,
)
from backend.core.services import GatewayService
from backend.core.credential_manager import CredentialManager


# ── In-memory adapters for testing ─────────────────────────────────


class InMemoryCatalog(CatalogRepository):
    def __init__(self, servers: list | None = None):
        self.servers = servers or []

    def list_all(self) -> list[ServerInfo]:
        return self.servers


class InMemoryState(StateRepository):
    def __init__(self, state: GatewayState | None = None):
        self.state = state or GatewayState()

    def load(self) -> GatewayState:
        return self.state

    def save(self, state: GatewayState) -> None:
        self.state = state


class SpyProfile(ProfileSync):
    def __init__(self):
        self.calls: list[set[str]] = []

    def sync(self, enabled: set[str]) -> None:
        self.calls.append(enabled)


class SpyGateway(GatewayController):
    def __init__(self):
        self.restart_called = False
        self.restart_async_called = False
        self.logs = ["log1", "log2"]

    def restart(self) -> bool:
        self.restart_called = True
        return True

    def restart_async(self) -> None:
        self.restart_async_called = True

    def recent_logs(self, n: int = 5) -> list[str]:
        return self.logs[-n:]

    def get_logs(self) -> list[LogEntry]:
        return [LogEntry(level="INFO", message=l, timestamp="") for l in self.logs]


# ── Fixtures ─────────────────────────────────────────────────────


@pytest.fixture
def catalog_servers():
    return [
        ServerInfo(name="memory", title="Memory", desc="In-memory storage"),
        ServerInfo(name="fetch", title="Fetch", desc="URL fetcher"),
        ServerInfo(name="exa", title="Exa", desc="Search API", secrets=True),
    ]


@pytest.fixture
def empty_state():
    return GatewayState()


@pytest.fixture
def populated_state():
    return GatewayState(installed=["memory", "fetch"], enabled=["memory"])


@pytest.fixture
def svc(catalog_servers, populated_state):
    return GatewayService(
        catalog=InMemoryCatalog(catalog_servers),
        state_repo=InMemoryState(populated_state),
        profile=SpyProfile(),
        gateway=SpyGateway(),
        conn_repo=None,
    )


# ── Tests ────────────────────────────────────────────────────────


class TestListServers:
    def test_returns_all_servers(self, svc: GatewayService):
        result = svc.list_servers()
        assert len(result) == 3

    def test_marks_installed_and_enabled(self, svc: GatewayService):
        result = {s.name: s for s in svc.list_servers()}
        assert result["memory"].installed is True
        assert result["memory"].enabled is True
        assert result["fetch"].installed is True
        assert result["fetch"].enabled is False
        assert result["exa"].installed is False
        assert result["exa"].enabled is False


class TestListCatalog:
    def test_returns_all(self, svc: GatewayService, catalog_servers):
        result = svc.list_catalog()
        assert result == catalog_servers

    def test_includes_secrets_flag(self, svc: GatewayService):
        result = {s.name: s for s in svc.list_catalog()}
        assert result["exa"].secrets is True
        assert result["memory"].secrets is False


class TestStats:
    def test_counts(self, svc: GatewayService):
        stats = svc.get_stats()
        assert stats.catalog == 3
        assert stats.installed == 2
        assert stats.enabled == 1


class TestInstall:
    def test_installs_new_server(self, svc: GatewayService):
        result = svc.install("exa")
        assert result.installed is True
        assert result.enabled is True
        state = svc.get_state()
        assert "exa" in state.installed
        assert "exa" in state.enabled

    def test_installs_already_installed(self, svc: GatewayService):
        result = svc.install("memory")
        assert result.installed is True

    def test_syncs_profile(self, svc: GatewayService):
        profile = svc._profile  # type: SpyProfile
        svc.install("exa")
        assert len(profile.calls) >= 1
        assert "exa" in profile.calls[-1]


class TestUninstall:
    def test_removes_server(self, svc: GatewayService):
        result = svc.uninstall("memory")
        assert result.installed is False
        assert result.enabled is False

    def test_syncs_profile(self, svc: GatewayService):
        profile = svc._profile  # type: SpyProfile
        svc.uninstall("memory")
        assert "memory" not in profile.calls[-1]


class TestToggle:
    def test_enables_disabled(self, svc: GatewayService):
        result = svc.toggle("fetch")
        assert result.enabled is True

    def test_disables_enabled(self, svc: GatewayService):
        result = svc.toggle("memory")
        assert result.enabled is False

    def test_toggle_twice(self, svc: GatewayService):
        svc.toggle("memory")
        result = svc.toggle("memory")
        assert result.enabled is True


class TestGateway:
    def test_restart(self, svc: GatewayService):
        assert svc.restart_gateway() is True
        assert svc._gateway.restart_called  # type: ignore

    def test_logs(self, svc: GatewayService):
        logs = svc.get_logs()
        assert len(logs) == 2
        assert logs[0].message == "log1"
        assert logs[1].message == "log2"


# ── In-memory credential repo for testing ────────────────────────────


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


class TestCredentialRepo:
    def test_upsert_get(self):
        repo = InMemoryCredentialRepo()
        repo.upsert("neon", "NEON_API_KEY", "sk-123")
        assert repo.get("neon", "NEON_API_KEY") == "sk-123"

    def test_get_nonexistent(self):
        repo = InMemoryCredentialRepo()
        assert repo.get("neon", "NONEXISTENT") is None

    def test_list_keys(self):
        repo = InMemoryCredentialRepo()
        repo.upsert("neon", "NEON_API_KEY", "v1")
        repo.upsert("neon", "OTHER_KEY", "v2")
        keys = repo.list_keys("neon")
        assert "NEON_API_KEY" in keys
        assert "OTHER_KEY" in keys

    def test_list_servers(self):
        repo = InMemoryCredentialRepo()
        repo.upsert("neon", "NEON_API_KEY", "v1")
        repo.upsert("github", "TOKEN", "v2")
        servers = repo.list_servers()
        assert "neon" in servers
        assert "github" in servers

    def test_delete(self):
        repo = InMemoryCredentialRepo()
        repo.upsert("neon", "KEY", "val")
        assert repo.get("neon", "KEY") == "val"
        repo.delete("neon", "KEY")
        assert repo.get("neon", "KEY") is None

    def test_upsert_overwrites(self):
        repo = InMemoryCredentialRepo()
        repo.upsert("neon", "KEY", "old")
        repo.upsert("neon", "KEY", "new")
        assert repo.get("neon", "KEY") == "new"

    def test_list_all(self):
        repo = InMemoryCredentialRepo()
        repo.upsert("neon", "KEY1", "v1")
        repo.upsert("github", "KEY2", "v2")
        all_items = repo.list_all()
        assert len(all_items) == 2
        assert ("neon", "KEY1", True) in all_items
        assert ("github", "KEY2", True) in all_items


class TestCredentialManager:
    def test_set_get(self):
        repo = InMemoryCredentialRepo()
        mgr = CredentialManager(repo, key_path="/tmp/test_cred.key")
        mgr.set("neon", "NEON_API_KEY", "sk-123")
        val = mgr.get("neon", "NEON_API_KEY")
        assert val == "sk-123"

    def test_get_nonexistent(self):
        repo = InMemoryCredentialRepo()
        mgr = CredentialManager(repo, key_path="/tmp/test_cred.key")
        assert mgr.get("neon", "NONEXISTENT") is None

    def test_encryption_at_rest(self):
        import tempfile, os
        with tempfile.NamedTemporaryFile(suffix=".key", delete=False) as f:
            key_path = f.name
        try:
            repo = InMemoryCredentialRepo()
            mgr = CredentialManager(repo, key_path=key_path)
            mgr.set("github", "TOKEN", "ghp_12345")
            stored = repo.get("github", "TOKEN")
            assert stored != "ghp_12345"
            assert stored is not None
            assert not stored.startswith("ghp_")
        finally:
            os.unlink(key_path)

    def test_get_env_dict(self):
        repo = InMemoryCredentialRepo()
        mgr = CredentialManager(repo, key_path="/tmp/test_cred.key")
        mgr.set("neon", "NEON_API_KEY", "sk-123")
        mgr.set("github", "GITHUB_TOKEN", "ghp-abc")
        env = mgr.get_env_dict()
        assert env["NEON_API_KEY"] == "sk-123"
        assert env["GITHUB_TOKEN"] == "ghp-abc"

    def test_delete(self):
        repo = InMemoryCredentialRepo()
        mgr = CredentialManager(repo, key_path="/tmp/test_cred.key")
        mgr.set("neon", "KEY", "val")
        assert mgr.get("neon", "KEY") == "val"
        mgr.delete("neon", "KEY")
        assert mgr.get("neon", "KEY") is None

    def test_get_all(self):
        repo = InMemoryCredentialRepo()
        mgr = CredentialManager(repo, key_path="/tmp/test_cred.key")
        mgr.set("neon", "NEON_API_KEY", "sk-1")
        mgr.set("neon", "OTHER", "val-2")
        all_creds = mgr.get_all("neon")
        assert all_creds == {"NEON_API_KEY": "sk-1", "OTHER": "val-2"}

    def test_persistent_key(self):
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

    def test_is_allowed(self):
        assert CredentialManager.is_allowed("neon", "NEON_API_KEY") is True
        assert CredentialManager.is_allowed("neon", "INVALID_KEY") is False
        assert CredentialManager.is_allowed("dockerhub", "HUB_PAT_TOKEN") is True
        assert CredentialManager.is_allowed("dockerhub", "dockerhub.username") is True

    def test_get_schema(self):
        schema = CredentialManager.get_schema()
        assert "neon" in schema
        assert "EXA_API_KEY" in schema["exa"]
        assert "SENTRY_AUTH_TOKEN" in schema["sentry"]
