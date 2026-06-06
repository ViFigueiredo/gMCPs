"""TDD: Core service tests with in-memory adapters."""

import pytest
from backend.core.entities import ServerInfo, GatewayState, Stats
from backend.core.ports import (
    CatalogRepository,
    StateRepository,
    ProfileSync,
    GatewayController,
)
from backend.core.services import GatewayService


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
        self.logs = ["log1", "log2"]

    def restart(self) -> bool:
        self.restart_called = True
        return True

    def recent_logs(self, n: int = 5) -> list[str]:
        return self.logs[-n:]


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
        logs = svc.get_logs(2)
        assert len(logs) == 2
        assert logs == ["log1", "log2"]
