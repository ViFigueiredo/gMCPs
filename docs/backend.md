# Backend

## Stack
- **Python 3.14+** — runtime
- **FastAPI** — framework REST
- **Uvicorn** — servidor ASGI
- **SQLite 3** — banco de dados (catálogo Docker, histórico de conexões)
- **Pytest** — testes (27 testes)

## Estrutura

```
backend/
├── core/
│   ├── entities.py      # ServerInfo, ServerStatus, GatewayState, Stats, LogEntry, ContainerRecord
│   ├── ports.py          # CatalogRepository, StateRepository, ProfileSync, GatewayController, ConnectionRepository
│   ├── services.py       # GatewayService (lógica de negócio central)
│   ├── i18n.py           # I18n class (tradução pt-BR/en-US + descrições de MCPs)
│   └── integrations.py   # Detecção de agentes (OpenCode, Kilo Code, Claude Code, Codex CLI, OpenClaude)
├── adapters/
│   ├── sqlite_catalog.py     # SqliteCatalogRepo → lê catalog_server do mcp-toolkit.db
│   ├── file_state.py         # FileStateRepo → persiste state.json (inclui shared_servers)
│   ├── docker_profile.py     # SqliteProfileSync + SubprocessGateway
│   ├── docker_containers.py  # DockerConnectionRepo → lê containers MCP + detecta agentes
│   ├── connection_db.py      # SQLite → histórico persistente de conexões
│   └── mcp_relay.py          # McpRelay → SSE proxy para modo compartilhado (1 container, N clientes)
├── main.py               # FastAPI app (adapter web)
└── tests/
    ├── test_core.py      # Testes do core
    └── test_api.py       # Testes da API
```

## API Endpoints

### Servidores e Catálogo
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/servers` | Lista servidores (catálogo + status) |
| GET | `/api/servers/{name}` | Detalhes de um servidor |
| POST | `/api/servers/{name}/install` | Instala um servidor |
| POST | `/api/servers/{name}/uninstall` | Remove um servidor |
| POST | `/api/servers/{name}/toggle` | Ativa/desativa um servidor |
| GET | `/api/catalog` | Lista servidores disponíveis (traduzidos) |
| GET | `/api/state` | Estado atual (installed + enabled) |
| GET | `/api/stats` | Estatísticas |

### Gateway
| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/api/gateway/restart` | Reinicia o gateway |
| GET | `/api/logs` | Retorna logs do gateway |

### Recursos
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/resources` | RAM, CPU, storage, active_servers, gateway_online |

### Modo Compartilhado
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/shared` | Lista servidores compartilhados |
| GET | `/api/shared/status` | Status dos relays ativos |
| POST | `/api/servers/{name}/share` | Ativa relay compartilhado |
| POST | `/api/servers/{name}/unshare` | Desativa relay compartilhado |

### Conexões
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/connections` | Lista conexões (com histórico SQLite) |
| GET | `/api/connections/tags` | Tags para filtro |
| POST | `/api/connections/{name}/stop` | Para container de um MCP |
| POST | `/api/connections/clear` | Para containers em massa (filtro MCP/período) |

### Integrações
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/integrations` | Lista agentes detectados + MCPs configurados |
| POST | `/api/integrations/add-server` | Adiciona servidor a um agente |
| POST | `/api/integrations/remove-server/{agent}/{name}` | Remove servidor de um agente |
| POST | `/api/integrations/auto-add/{agent}/{mcp}` | Adiciona MCP do catálogo a um agente |

## GatewayService

```python
class GatewayService:
    def __init__(self, catalog, state, profile, gateway, conn_repo=None): ...

    # Leitura
    def list_servers(self) -> list[ServerStatus]: ...
    def list_catalog(self) -> list[ServerInfo]: ...
    def get_state(self) -> GatewayState: ...
    def get_stats(self) -> Stats: ...

    # Escrita
    def install(self, name: str) -> ServerStatus: ...
    def uninstall(self, name: str) -> ServerStatus: ...
    def toggle(self, name: str) -> ServerStatus: ...

    # Gateway
    def restart_gateway(self) -> bool: ...
    def get_logs(self, level: str | None = None) -> list[LogEntry]: ...

    # Conexões
    def list_connections(self, ...) -> list[ContainerRecord]: ...
    def get_connection_tags(self) -> list[dict]: ...

    # Shared mode
    def list_shared(self) -> dict[str, int]: ...
    def enable_shared(self, name: str) -> dict: ...
    def disable_shared(self, name: str) -> bool: ...
```

## Adapters

### SqliteCatalogRepo
- Conecta em `~/.docker/mcp/mcp-toolkit.db`
- Lê tabela `catalog_server` (coluna `snapshot` com JSON)
- Timeout 15s + WAL mode

### FileStateRepo
- Lê/escreve `~/.config/gmcp/state.json`
- Formato: `{"installed": [...], "enabled": [...], "shared_servers": {...}}`
- Bootstrap do profile Docker se arquivo não existe

### SqliteProfileSync
- Sincroniza servidores ativos na tabela `working_set`

### SubprocessGateway
- `restart()`: `pkill` + `nohup docker mcp gateway run ...`
- `get_logs()`: lê `/tmp/gateway.log`

### DockerConnectionRepo
- `list_connections()`: `docker ps -a` + parse log do gateway
- Persiste em `connection_db.py` (SQLite)
- Detecta agentes ativos via `ss`/`lsof`

### McpRelay
- Mantém 1 container rodando para N clientes SSE
- Porta 3100+ por MCP compartilhado
- stdin/stdout pipe entre container e múltiplos SSE clients

## Testes

```bash
.venv/bin/python3 -m pytest backend/tests/
```

- **test_core.py**: GatewayService com adapters in-memory (InMemoryCatalog, InMemoryState, SpyProfile, SpyGateway)
- **test_api.py**: TestClient do FastAPI com adapters in-memory
- 27 testes: list, install, uninstall, toggle, state, stats, logs, restart, 404
