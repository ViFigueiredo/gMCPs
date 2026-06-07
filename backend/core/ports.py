"""Ports — abstract interfaces (hexagonal driven ports)."""

from abc import ABC, abstractmethod
from backend.core.entities import ServerInfo, GatewayState, LogEntry, ContainerRecord


class CatalogRepository(ABC):
    """Reads available MCP servers from the Docker MCP catalog."""

    @abstractmethod
    def list_all(self) -> list[ServerInfo]:
        ...


class StateRepository(ABC):
    """Persists installed/enabled server state."""

    @abstractmethod
    def load(self) -> GatewayState:
        ...

    @abstractmethod
    def save(self, state: GatewayState) -> None:
        ...


class ProfileSync(ABC):
    """Syncs enabled servers into the Docker MCP profile."""

    @abstractmethod
    def sync(self, enabled: set[str]) -> None:
        ...


class GatewayController(ABC):
    """Controls the Docker MCP gateway process."""

    @abstractmethod
    def restart(self) -> bool:
        ...

    @abstractmethod
    def restart_async(self) -> None:
        ...

    @abstractmethod
    def recent_logs(self, n: int = 5) -> list[str]:
        ...

    @abstractmethod
    def get_logs(self) -> list[LogEntry]:
        ...


class ConnectionRepository(ABC):
    """Reads MCP container connections from Docker."""

    @abstractmethod
    def list_connections(
        self,
        mcp_filter: list[str] | None = None,
        date_start: str | None = None,
        date_end: str | None = None,
    ) -> list[ContainerRecord]:
        ...

    @abstractmethod
    def get_filter_tags(self) -> list[dict]:
        """Returns list of {mcp_name, active_count, total_count}."""
        ...
