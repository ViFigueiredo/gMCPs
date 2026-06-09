"""Application services — hexagonal use-case layer."""

from backend.core.ports import (
    CatalogRepository,
    StateRepository,
    ProfileSync,
    GatewayController,
    ConnectionRepository,
)
from backend.core.entities import (
    ServerInfo,
    ServerStatus,
    GatewayState,
    Stats,
    LogEntry,
    ContainerRecord,
)
from backend.core.credential_manager import CredentialManager


class GatewayService:
    """Centralised business logic used by both API and TUI."""

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

    @property
    def cred_manager(self) -> CredentialManager | None:
        return self._cred_manager

    # ── Read ────────────────────────────────────────────────────────

    def list_servers(self) -> list[ServerStatus]:
        state = self._state_repo.load()
        installed = set(state.installed)
        enabled = set(state.enabled)
        return [
            ServerStatus(
                name=s.name,
                installed=s.name in installed,
                enabled=s.name in enabled,
            )
            for s in self._catalog.list_all()
        ]

    def list_catalog(self) -> list[ServerInfo]:
        from backend.core.i18n import _
        items = self._catalog.list_all()
        for item in items:
            item.desc = _.translate_desc(item.name, item.desc)
        return items

    def get_state(self) -> GatewayState:
        return self._state_repo.load()

    def get_stats(self) -> Stats:
        state = self._state_repo.load()
        catalog = self._catalog.list_all()
        return Stats(
            catalog=len(catalog),
            installed=len(state.installed),
            enabled=len(state.enabled),
        )

    # ── Write ───────────────────────────────────────────────────────

    def _save_and_sync(self, state: GatewayState) -> None:
        self._state_repo.save(state)
        self._profile.sync(set(state.enabled))
        self._gateway.restart_async()

    def install(self, name: str) -> ServerStatus:
        state = self._state_repo.load()
        if name not in state.installed:
            state.installed.append(name)
        if name not in state.enabled:
            state.enabled.append(name)
        self._save_and_sync(state)
        return ServerStatus(name=name, installed=True, enabled=True)

    def uninstall(self, name: str) -> ServerStatus:
        state = self._state_repo.load()
        state.installed = [x for x in state.installed if x != name]
        state.enabled = [x for x in state.enabled if x != name]
        self._save_and_sync(state)
        return ServerStatus(name=name, installed=False, enabled=False)

    def toggle(self, name: str) -> ServerStatus:
        state = self._state_repo.load()
        if name in state.enabled:
            state.enabled.remove(name)
        else:
            state.enabled.append(name)
        self._save_and_sync(state)
        return ServerStatus(
            name=name,
            installed=name in state.installed,
            enabled=name in state.enabled,
        )

    # ── Shared mode ─────────────────────────────────────────────────

    def list_shared(self) -> dict[str, int]:
        return dict(self._state_repo.load().shared_servers)

    def enable_shared(self, name: str) -> dict:
        from backend.adapters.mcp_relay import start_shared_server, get_next_port
        state = self._state_repo.load()
        if name not in state.installed:
            raise ValueError(f"MCP '{name}' not installed")
        if name in state.shared_servers:
            port = state.shared_servers[name]
        else:
            port = get_next_port()
            state.shared_servers[name] = port
            self._state_repo.save(state)
        info = start_shared_server(name, port)
        return info

    def disable_shared(self, name: str) -> bool:
        from backend.adapters.mcp_relay import stop_shared_server
        state = self._state_repo.load()
        removed = state.shared_servers.pop(name, None)
        if removed is not None:
            self._state_repo.save(state)
        stop_shared_server(name)
        return removed is not None

    # ── Gateway ─────────────────────────────────────────────────────

    def restart_gateway(self) -> bool:
        return self._gateway.restart()

    def get_logs(self, level: str | None = None) -> list[LogEntry]:
        logs = self._gateway.get_logs()
        if level:
            return [l for l in logs if l.level == level.upper()]
        return logs

    # ── Connections (containers) ────────────────────────────────────

    def list_connections(
        self,
        mcp_filter: list[str] | None = None,
        date_start: str | None = None,
        date_end: str | None = None,
    ) -> list[ContainerRecord]:
        if not self._conn_repo:
            return []
        return self._conn_repo.list_connections(mcp_filter, date_start, date_end)

    def get_connection_tags(self) -> list[dict]:
        if not self._conn_repo:
            return []
        return self._conn_repo.get_filter_tags()
