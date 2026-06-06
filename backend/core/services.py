"""Application services — hexagonal use-case layer."""

from backend.core.ports import (
    CatalogRepository,
    StateRepository,
    ProfileSync,
    GatewayController,
)
from backend.core.entities import ServerInfo, ServerStatus, GatewayState, Stats, LogEntry


class GatewayService:
    """Centralised business logic used by both API and TUI."""

    def __init__(
        self,
        catalog: CatalogRepository,
        state_repo: StateRepository,
        profile: ProfileSync,
        gateway: GatewayController,
    ):
        self._catalog = catalog
        self._state_repo = state_repo
        self._profile = profile
        self._gateway = gateway

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
        return self._catalog.list_all()

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

    # ── Gateway ─────────────────────────────────────────────────────

    def restart_gateway(self) -> bool:
        return self._gateway.restart()

    def get_logs(self, n: int = 5) -> list[str]:
        return self._gateway.recent_logs(n)
