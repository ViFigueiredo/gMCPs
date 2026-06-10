# Credentials Management — Design Document

**Date:** 2026-06-09
**Project:** gmcp (Gateway MCP Manager)
**Status:** Approved

## 1. Problem

MCP servers like `neon`, `github`, `dockerhub`, `exa`, `sentry`, and `filesystem` require API keys, tokens, or configuration values (collectively "credentials") to function. Currently these must be set as environment variables or via the Docker secrets engine — which is unavailable (`engine.sock` not found). There is no UI to manage these credentials.

## 2. Architecture

```
Frontend (Vue 3) / TUI (curses)
        │ PUT /api/credentials/{server}
        ▼
FastAPI Backend (:8000)
        │
        ▼
CredentialManager (core/credential_manager.py)
        │ • encrypt with Fernet (AES-256-CBC + HMAC)
        │ • decrypt on read
        ▼
CredentialRepo (adapters/credential_repo.py)
        │ • SQLite table: credential_store
        ▼
~/.docker/mcp/mcp-toolkit.db  +  ~/.config/gmcp/credentials.key
        │
        ▼
start-gateway.sh reads → decrypts → exports as env vars → starts gateway
```

## 3. Data Model

Table `credential_store` in the existing SQLite catalog database:

```sql
CREATE TABLE IF NOT EXISTS credential_store (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    server_name TEXT    NOT NULL,
    key         TEXT    NOT NULL,
    value       TEXT    NOT NULL,
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE(server_name, key)
);
```

## 4. Credential Schema

Hardcoded mapping of which keys each server accepts:

| Server       | Keys                                        |
|------------- |---------------------------------------------|
| `neon`       | `NEON_API_KEY`                              |
| `exa`        | `EXA_API_KEY`                               |
| `sentry`     | `SENTRY_AUTH_TOKEN`                         |
| `github`     | `GITHUB_PERSONAL_ACCESS_TOKEN`              |
| `dockerhub`  | `HUB_PAT_TOKEN`, `dockerhub.username`       |
| `filesystem` | `filesystem.paths`                          |

## 5. Encryption

- **Library:** `cryptography.fernet` (AES-256-CBC + HMAC-SHA256)
- **Master key:** `~/.config/gmcp/credentials.key` (auto-generated, chmod 600)
- **Per-value:** Each credential is encrypted individually with `Fernet.encrypt()`
- **Decryption:** Only occurs in `start-gateway.sh` (for env var export) and internal gateway restart
- **API never returns decrypted values** — only `true`/`false` for "has value"

## 6. API Endpoints

| Method   | Path                              | Description                        |
|----------|-----------------------------------|------------------------------------|
| `GET`    | `/api/credentials`                | List servers + which keys are set  |
| `PUT`    | `/api/credentials/{server}`       | Set/update a credential (encrypted) |
| `DELETE` | `/api/credentials/{server}/{key}` | Remove a credential                |

Request body (PUT): `{ "key": "NEON_API_KEY", "value": "..." }`

## 7. Core — CredentialManager

New file: `backend/core/credential_manager.py`

```python
class CredentialManager:
    def __init__(self, repo: CredentialRepo, key_path: str): ...
    def set(self, server, key, value): ...
    def get(self, server, key) -> str | None: ...
    def get_all(self, server) -> dict: ...
    def get_env_dict(self) -> dict[str, str]: ...
    def delete(self, server, key): ...
    def _load_or_create_key(self) -> Fernet: ...
```

## 8. Adapter — CredentialRepo

New file: `backend/adapters/credential_repo.py`

SQLite persistence layer with `upsert`, `get`, `list_keys`, `list_servers`, `delete`.

## 9. FastAPI Routes

Added to `backend/main.py`:
- `GET /api/credentials`
- `PUT /api/credentials/{server}`
- `DELETE /api/credentials/{server}/{key}`

## 10. TUI — 4th Tab "Credenciais 🔑"

- Grid of server cards with 🔒/🔓 indicators per key
- Detail panel below with input fields
- Keys: Tab/arrows to navigate, Enter to select, Ctrl+S save, Del clear

## 11. Vue 3 — CredentialsView

- Server cards grid with lock icons
- Form panel with password inputs + visibility toggle
- Save / Clear / Restart Gateway buttons
- Pinia store `credentials.ts`
- Route `/credentials`

## 12. Gateway Restart with Credentials

`start-gateway.sh` updated to:
1. Read credentials from SQLite
2. Decrypt using Fernet
3. Export as environment variables
4. Start Docker MCP gateway

## 13. Files to Create/Modify

| File | Action |
|------|--------|
| `backend/core/credential_manager.py` | NEW |
| `backend/adapters/credential_repo.py` | NEW |
| `backend/main.py` | MODIFY — add routes + credential schema |
| `backend/core/services.py` | MODIFY — add `cred_manager` property, `restart_with_credentials` |
| `backend/core/ports.py` | MODIFY — add `CredentialRepository` abstract port |
| `backend/core/entities.py` | MODIFY — add `CredentialStatus` entity |
| `mcp-tui.py` | MODIFY — add 4th tab + credential editing |
| `src/views/CredentialsView.vue` | NEW |
| `src/stores/credentials.ts` | NEW |
| `src/router/index.ts` | MODIFY — add `/credentials` route |
| `src/locales/pt-BR.json` | MODIFY — add i18n keys |
| `src/locales/en-US.json` | MODIFY — add i18n keys |
| `start-gateway.sh` | MODIFY — add credential export |
| `requirements.txt` | MODIFY — add `cryptography` |

## 14. Security Considerations

- Master key file: `chmod 600`, stored outside repo
- API never exposes decrypted values
- Fernet provides authenticated encryption (tamper-proof)
- SQLite WAL mode ensures concurrent read safety
- Keys validated against hardcoded schema before storage
