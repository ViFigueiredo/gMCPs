"""Domain entities — pure data, no I/O."""

from dataclasses import dataclass, field


@dataclass
class ServerInfo:
    name: str
    title: str
    desc: str
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


@dataclass
class Stats:
    catalog: int = 0
    installed: int = 0
    enabled: int = 0


@dataclass
class LogEntry:
    lines: list[str] = field(default_factory=list)
