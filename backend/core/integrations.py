"""Integrations module — detect and configure MCP servers in agent tools."""

import json
import os
import shlex
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class McpServerDef:
    """An MCP server entry found in an agent's config."""
    name: str
    type: str          # "local", "remote", "command"
    command: Optional[str] = None
    args: list[str] = field(default_factory=list)
    url: Optional[str] = None
    env: dict = field(default_factory=dict)
    enabled: Optional[bool] = None


@dataclass
class AgentInfo:
    """Detected agent tool and its MCP config status."""
    id: str
    name: str
    config_path: Optional[str]
    config_format: str        # "json", "jsonc", "toml"
    mcp_key: str             # e.g. "mcp", "mcpServers", "mcp_servers"
    installed: bool
    is_openclaude: bool = False
    servers: list[McpServerDef] = field(default_factory=list)
    error: Optional[str] = None


AGENTS: list[dict] = [
    {
        "id": "opencode",
        "name": "OpenCode",
        "config_path": "~/.config/opencode/opencode.json",
        "config_format": "jsonc",
        "mcp_key": "mcp",
    },
    {
        "id": "kilocode",
        "name": "Kilo Code",
        "config_path": "~/.config/kilo/kilo.json",
        "config_format": "jsonc",
        "mcp_key": "mcp",
        "binary": "kilo",
    },
    {
        "id": "codex",
        "name": "Codex CLI",
        "config_path": "~/.codex/config.toml",
        "config_format": "toml",
        "mcp_key": "mcp_servers",
    },
    {
        "id": "claudecode",
        "name": "Claude Code",
        "config_path": "~/.claude.json",
        "config_format": "json",
        "mcp_key": "mcpServers",
        "binary": "claude",
    },
    {
        "id": "openclaude",
        "name": "OpenClaude",
        "config_path": "~/.openclaude.json",
        "config_format": "json",
        "mcp_key": "mcpServers",
        "is_openclaude": True,
    },
]


def _find_config(agent_cfg: dict) -> Optional[Path]:
    paths_to_try = [
        Path(os.path.expanduser(agent_cfg["config_path"])),
    ]
    if agent_cfg["id"] == "openclaude":
        paths_to_try.append(Path(os.path.expanduser("~/.openclaude/settings.json")))
    for p in paths_to_try:
        if p.exists():
            return p
    return None


def _detect_installed(agent_cfg: dict) -> bool:
    binary = agent_cfg.get("binary", agent_cfg["id"])
    return shutil.which(binary) is not None


def _parse_toml(text: str) -> dict:
    """Minimal TOML parser for MCP server configs only."""
    result: dict = {}
    current_table: Optional[str] = None
    current_data: dict = {}
    in_array = False
    array_key = ""
    array_values: list[str] = []

    for line in text.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and not line.startswith("[["):
            if current_table and current_table.startswith("mcp_servers."):
                parts = current_table.split(".", 1)
                if len(parts) == 2:
                    server_name = parts[1]
                    if "args" not in current_data:
                        current_data.setdefault("args", [])
                    result[server_name] = current_data
            current_table = line.strip("[]").strip()
            current_data = {}
            in_array = False
            continue
        if current_table and current_table.startswith("mcp_servers."):
            if in_array:
                if line.rstrip().endswith("]"):
                    val = line.rstrip().rstrip("]").strip().strip('"').strip("'")
                    if val:
                        array_values.append(val)
                    current_data[array_key] = array_values
                    in_array = False
                    array_values = []
                else:
                    val = line.strip().strip('"').strip("'").rstrip(",")
                    if val:
                        array_values.append(val)
                continue
            if "=" in line:
                key, _, val = line.partition("=")
                key = key.strip()
                val = val.strip()
                if val.startswith("{") and val.endswith("}"):
                    inline = {}
                    inner = val[1:-1].strip()
                    if inner:
                        for pair in inner.split(","):
                            pair = pair.strip()
                            if "=" in pair:
                                ik, _, iv = pair.partition("=")
                                inline[ik.strip().strip('"').strip("'")] = iv.strip().strip('"').strip("'")
                    current_data[key] = inline
                elif key == "args" and val == "[":
                    in_array = True
                    array_key = key
                    array_values = []
                elif val.startswith("[") and val.endswith("]"):
                    items = [v.strip().strip('"').strip("'") for v in val[1:-1].split(",") if v.strip()]
                    current_data[key] = items
                elif val.lower() == "true":
                    current_data[key] = True
                elif val.lower() == "false":
                    current_data[key] = False
                else:
                    val = val.strip('"').strip("'")
                    try:
                        current_data[key] = int(val)
                    except ValueError:
                        current_data[key] = val

    if current_table and current_table.startswith("mcp_servers."):
        parts = current_table.split(".", 1)
        if len(parts) == 2:
            server_name = parts[1]
            result[server_name] = current_data

    return result


def _read_config(path: Path, fmt: str, agent_cfg: dict) -> dict:
    if fmt == "toml":
        parsed = _parse_toml(path.read_text())
        return {agent_cfg["mcp_key"]: parsed}
    text = path.read_text()
    return json.loads(text)


def _build_servers(agent_cfg: dict, config: dict) -> list[McpServerDef]:
    mcp_key = agent_cfg["mcp_key"]
    mcp_data = config.get(mcp_key, {})
    servers: list[McpServerDef] = []
    for name, data in mcp_data.items():
        data = data or {}
        if isinstance(data, dict):
            env = data.get("environment") or data.get("env_vars") or data.get("env", {})
            extra = {k: v for k, v in data.items() if k not in ("type", "command", "args", "url", "environment", "env_vars", "env", "enabled")}
            if extra:
                env.update(extra)
            servers.append(McpServerDef(
                name=name,
                type=data.get("type", "local"),
                command=data.get("command") or data.get("url"),
                args=(
                    data.get("args", [])
                    if isinstance(data.get("args"), list)
                    else []
                ),
                url=data.get("url"),
                env=env,
                enabled=data.get("enabled", True),
            ))
    return servers


def detect_agents() -> list[AgentInfo]:
    agents: list[AgentInfo] = []
    for a in AGENTS:
        config_path = _find_config(a)
        installed = _detect_installed(a)
        info = AgentInfo(
            id=a["id"],
            name=a["name"],
            config_path=str(config_path) if config_path else None,
            config_format=a["config_format"],
            mcp_key=a["mcp_key"],
            installed=installed,
            is_openclaude=a.get("is_openclaude", False),
        )
        if config_path:
            try:
                config = _read_config(config_path, a["config_format"], a)
                info.servers = _build_servers(a, config)
            except (json.JSONDecodeError, OSError) as e:
                info.error = str(e)
        agents.append(info)
    return agents


def _add_server_json(config: dict, agent_cfg: dict, server: McpServerDef) -> dict:
    mcp_key = agent_cfg["mcp_key"]
    if mcp_key not in config:
        config[mcp_key] = {}
    entry: dict = {}
    if server.type == "remote" and server.url:
        entry["type"] = "remote"
        entry["url"] = server.url
    else:
        entry["type"] = "local"
        entry["command"] = [server.command] + server.args if server.command else []
    if server.env:
        for k, v in server.env.items():
            entry[k] = v
    if server.enabled is not None:
        entry["enabled"] = server.enabled
    config[mcp_key][server.name] = entry
    return config


def remove_server(agent_id: str, server_name: str) -> list[AgentInfo]:
    for a in AGENTS:
        if a["id"] == agent_id:
            config_path = _find_config(a)
            if not config_path:
                raise FileNotFoundError(f"Config not found for {a['name']}")
            config = _read_config(config_path, a["config_format"], a)
            mcp_key = a["mcp_key"]
            if mcp_key in config and server_name in config[mcp_key]:
                del config[mcp_key][server_name]
            with open(config_path, "w") as f:
                if a["config_format"] == "toml":
                    _write_toml(config, a["mcp_key"], f)
                else:
                    json.dump(config, f, indent=2)
                    f.write("\n")
            return detect_agents()
    raise ValueError(f"Unknown agent: {agent_id}")


def add_server(agent_id: str, server: McpServerDef) -> list[AgentInfo]:
    for a in AGENTS:
        if a["id"] == agent_id:
            config_path = _find_config(a)
            if not config_path:
                raise FileNotFoundError(f"Config not found for {a['name']}")
            config = _read_config(config_path, a["config_format"], a)
            config = _add_server_json(config, a, server)
            with open(config_path, "w") as f:
                if a["config_format"] == "toml":
                    _write_toml(config, a["mcp_key"], f)
                else:
                    json.dump(config, f, indent=2)
                    f.write("\n")
            return detect_agents()
    raise ValueError(f"Unknown agent: {agent_id}")


def _write_toml(config: dict, mcp_key: str, f):
    mcp_data = config.get(mcp_key, {})
    for name, data in mcp_data.items():
        f.write(f"[{mcp_key}.{name}]\n")
        for key, val in data.items():
            if isinstance(val, bool):
                f.write(f'{key} = {"true" if val else "false"}\n')
            elif isinstance(val, dict):
                items = ", ".join(f'{k} = "{v}"' for k, v in val.items())
                f.write(f"{key} = {{{items}}}\n")
            elif isinstance(val, list):
                items = ", ".join(f'"{v}"' for v in val)
                f.write(f"{key} = [{items}]\n")
            else:
                f.write(f'{key} = "{val}"\n')
        f.write("\n")
