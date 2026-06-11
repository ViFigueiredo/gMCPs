"""Adapter: persists app config in a JSON file."""
import json
import os
from dataclasses import dataclass
from backend.core.ports import ConfigRepository

DEFAULT_CONFIG = {
    "theme": "dark",
    "language": "pt-BR",
    "share_default": False,
    "tool_name_prefix": True,
}

CONFIG_PATH = os.path.expanduser("~/.config/gmcp/config.json")


class JsonConfigRepo(ConfigRepository):
    def load(self) -> dict:
        try:
            with open(CONFIG_PATH) as f:
                return {**DEFAULT_CONFIG, **json.load(f)}
        except (FileNotFoundError, json.JSONDecodeError):
            return dict(DEFAULT_CONFIG)

    def save(self, config: dict) -> None:
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        merged = {**DEFAULT_CONFIG, **config}
        with open(CONFIG_PATH, "w") as f:
            json.dump(merged, f, indent=2)
            f.write("\n")
