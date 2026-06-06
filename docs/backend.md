# Backend

## Stack
- **Python 3.14+** — runtime
- **FastAPI** — framework REST
- **Uvicorn** — servidor ASGI
- **SQLite 3** — banco de dados (catálogo Docker)
- **Pytest** — testes

## Estrutura

```
backend/
├── core/
│   ├── __init__.py
│   ├── entities.py      # ServerInfo, ServerStatus, GatewayState, Stats
│   ├── ports.py          # CatalogRepository, StateRepository, ProfileSync, GatewayController
│   ├── services.py       # GatewayService (lógica de negócio central)
│   └── i18n.py           # I18n class (tradução pt-BR/en-US)
├── adapters/
│   ├── __init__.py
│   ├── sqlite_catalog.py # SqliteCatalogRepo → lê catalog_server do mcp-toolkit.db
│   ├── file_state.py     # FileStateRepo → persiste state.json
│   └── docker_profile.py # SqliteProfileSync + SubprocessGateway
├── main.py               # FastAPI app (adapter web)
└── tests/
    ├── test_core.py      # 13 testes do core
    └── test_api.py       # 14 testes da API
```

## API Endpoints

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/servers` | Lista todos os servidores (catálogo + status) |
| GET | `/api/servers/{name}` | Detalhes de um servidor |
| POST | `/api/servers/{name}/install` | Instala um servidor |
| POST | `/api/servers/{name}/uninstall` | Remove um servidor |
| POST | `/api/servers/{name}/toggle` | Ativa/desativa um servidor |
| GET | `/api/catalog` | Lista servidores disponíveis no catálogo |
| GET | `/api/state` | Estado atual do gateway |
| GET | `/api/stats` | Estatísticas (instalados, ativos, catálogo) |
| POST | `/api/gateway/restart` | Reinicia o gateway Docker |
| GET | `/api/gateway/logs` | Últimas N linhas do log |

## GatewayService

```python
class GatewayService:
    def __init__(self, catalog: CatalogRepository, state: StateRepository,
                 profile: ProfileSync, gateway: GatewayController):
        ...

    def list_servers(self) -> list[ServerStatus]: ...
    def list_catalog(self) -> list[ServerInfo]: ...
    def get_state(self) -> GatewayState: ...
    def get_stats(self) -> Stats: ...
    def install(self, name: str) -> None: ...
    def uninstall(self, name: str) -> None: ...
    def toggle(self, name: str) -> None: ...
    def restart_gateway(self) -> bool: ...
    def get_logs(self, n: int = 5) -> list[str]: ...
```

## Adapters

### SqliteCatalogRepo
- Conecta em `~/.docker/mcp/mcp-toolkit.db`
- Lê tabela `catalog_server` (coluna `snapshot` com JSON)
- Timeout 15s + WAL mode para evitar lock

### FileStateRepo
- Lê/escreve `~/.config/gmcp/state.json`
- Formato: `{"installed": [...], "enabled": [...]}`
- Se arquivo não existe, faz bootstrap do profile Docker existente

### SqliteProfileSync
- Conecta na tabela `working_set` do `mcp-toolkit.db`
- Sincroniza servidores ativos no profile Docker
- Cria entrada JSON com snapshot, secrets, imagem para cada servidor

### SubprocessGateway
- `restart()`: `pkill -9 -f "docker mcp gateway run"` + `nohup docker mcp gateway run ...`
- `recent_logs()`: lê `/tmp/gateway.log`

## Testes

```bash
cd backend && python3 -m pytest
```

- **test_core.py**: GatewayService com adapters in-memory (InMemoryCatalog, InMemoryState, SpyProfile, SpyGateway)
- **test_api.py**: TestClient do FastAPI com adapters in-memory
- Cobertura: list, install, uninstall, toggle, state, stats, logs, restart, 404
