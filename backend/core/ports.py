"""Ports — abstract interfaces (hexagonal driven ports)."""

from abc import ABC, abstractmethod
from backend.core.entities import ServerInfo, GatewayState


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
        """Fire-and-forget restart — returns immediately."""

    @abstractmethod
    def recent_logs(self, n: int = 5) -> list[str]:
        ...
