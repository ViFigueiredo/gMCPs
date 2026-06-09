"""Core credential management — encryption/decryption orchestration."""

import os
from pathlib import Path
from cryptography.fernet import Fernet
from backend.core.ports import CredentialRepository


CREDENTIAL_SCHEMA: dict[str, list[str]] = {
    "neon":         ["NEON_API_KEY"],
    "exa":          ["EXA_API_KEY"],
    "sentry":       ["SENTRY_AUTH_TOKEN"],
    "github":       ["GITHUB_PERSONAL_ACCESS_TOKEN"],
    "dockerhub":    ["HUB_PAT_TOKEN", "dockerhub.username"],
    "filesystem":   ["filesystem.paths"],
}


class CredentialManager:
    """Encrypts/decrypts credentials and delegates storage to a repository."""

    def __init__(self, repo: CredentialRepository, key_path: str):
        self._repo = repo
        self._key_path = key_path
        self._fernet = self._load_or_create_key()

    def set(self, server: str, key: str, value: str) -> None:
        encrypted = self._fernet.encrypt(value.encode())
        self._repo.upsert(server, key, encrypted.decode())

    def get(self, server: str, key: str) -> str | None:
        encrypted = self._repo.get(server, key)
        if encrypted is None:
            return None
        return self._fernet.decrypt(encrypted.encode()).decode()

    def get_all(self, server: str) -> dict[str, str]:
        result = {}
        for key in self._repo.list_keys(server):
            val = self.get(server, key)
            if val is not None:
                result[key] = val
        return result

    def get_env_dict(self) -> dict[str, str]:
        env = {}
        for server in self._repo.list_servers():
            for key, val in self.get_all(server).items():
                env[key] = val
        return env

    def delete(self, server: str, key: str) -> None:
        self._repo.delete(server, key)

    def _load_or_create_key(self) -> Fernet:
        path = Path(self._key_path)
        if not path.exists() or path.stat().st_size == 0:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(Fernet.generate_key().decode())
            path.chmod(0o600)
        return Fernet(path.read_text().encode())

    @staticmethod
    def is_allowed(server: str, key: str) -> bool:
        return key in CREDENTIAL_SCHEMA.get(server, [])

    @staticmethod
    def get_schema() -> dict[str, list[str]]:
        return dict(CREDENTIAL_SCHEMA)