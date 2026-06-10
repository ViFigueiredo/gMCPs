"""Domain entities — pure data, no I/O."""

from dataclasses import dataclass, field


@dataclass
class ServerInfo:
    name: str
    title: str
    desc: str
    icon: str = ""
    category: str = ""
    secrets: bool = False


@dataclass
class ServerStatus:
    name: str
    installed: bool = False
    enabled: bool = False


@dataclass
class GatewayState:
    installed: list[str] = field(default_factory=list)
    enabled: list[str] = field(default_factory=list)
    shared_servers: dict[str, int] = field(default_factory=dict)  # mcp_name -> port


@dataclass
class Stats:
    catalog: int = 0
    installed: int = 0
    enabled: int = 0


@dataclass
class LogEntry:
    level: str
    message: str
    timestamp: str


@dataclass
class ContainerRecord:
    agent: str
    mcp_name: str
    container_id: str
    container_name: str
    started_at: str
    ended_at: str | None
    status: str  # "active" | "stopped"


@dataclass
class CredentialStatus:
    server: str
    key: str
    has_value: bool 
