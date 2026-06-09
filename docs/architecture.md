# Arquitetura

## Hexagonal (Ports & Adapters)

O gmcp segue o padrão **Hexagonal** (Alistair Cockburn), também conhecido como Ports & Adapters. O domínio central é isolado de frameworks e infraestrutura.

### Estrutura

```
                     ┌─────────────────────────────┐
                     │        Interfaces            │
                     │  ┌─────────┐ ┌──────────┐    │
                     │  │  TUI    │ │ Web API  │    │
                     │  │(curses) │ │(FastAPI) │    │
                     │  └────┬────┘ └────┬─────┘    │
                     │       │           │          │
                     │       ▼           ▼          │
                     │   ┌──────────────────┐       │
                     │   │  GatewayService  │       │
                     │   │   (core/service) │       │
                     │   └──┬──┬──┬──┬──┬──┘       │
                     │      │  │  │  │  │           │
                     │      ▼  ▼  ▼  ▼  ▼           │
                     │ ┌──┐ ┌──┐ ┌──┐ ┌──┐ ┌───┐   │
                     │ │Cat│ │St │ │Pr │ │Gw │ │i18│   │
                     │ └──┘ └──┘ └──┘ └──┘ └───┘   │
                     │  Ports (interfaces)            │
                     └──────────┬───────────────────┘
                                │
           ┌────────────────────┼────────────────────────────┐
           ▼                    ▼                    ▼       ▼
    ┌──────────────┐   ┌─────────────┐   ┌────────────────┐ ┌──────────┐
    │SqliteCatalog │   │FileStateRepo│   │SqliteProfileSync│ │DockerCon- │
    │(SQLite DB)   │   │(state.json) │   │(Docker profile) │ │nectionRepo│
    └──────────────┘   └─────────────┘   └────────────────┘ └─────┬────┘
           ▲                    ▲                    ▲            │
           │                    │                    │     ┌──────┴──────┐
    ┌──────┴──────┐   ┌────────┴───────┐   ┌────────┴───────┐ │connection_ │
    │ mcp-toolkit │   │ ~/.config/gmcp/ │   │ Docker CLI     │ │ db.py      │
    │ .db         │   │ state.json      │   │ + profile SQLite│ │(SQLite)    │
    └─────────────┘   └────────────────┘   └────────────────┘ └─────────────┘

                     ┌──────────────────┐
                     │   MCP Relay      │
                     │  (mcp_relay.py)  │
                     │  SSE proxy por   │
                     │  MCP compartilhado│
                     └────────┬─────────┘
                              │ porta 3100+

```

### Camadas

#### Core (`backend/core/`)
- **entities.py**: Dataclasses de domínio (`ServerInfo`, `ServerStatus`, `GatewayState`, `Stats`, `LogEntry`, `ContainerRecord`)
- **ports.py**: Interfaces abstratas (`CatalogRepository`, `StateRepository`, `ProfileSync`, `GatewayController`, `ConnectionRepository`)
- **services.py**: `GatewayService` — orquestra lógica de negócio, recebe portas por injeção de dependência
- **i18n.py**: Internacionalização compartilhada entre TUI e backend
- **integrations.py**: Detecção de agentes MCP (OpenCode, Kilo Code, Claude Code, Codex CLI, OpenClaude) + leitura/escrita de configs

Regra: **core nunca importa adapters ou frameworks** (exceção: `mcp_relay` e `connection_db` nos métodos de share — import lazy dentro da função).

#### Adapters (`backend/adapters/`)
- **sqlite_catalog.py**: Lê catálogo de servidores do banco SQLite do Docker
- **file_state.py**: Persiste estado (installed + enabled + shared_servers) em `state.json`
- **docker_profile.py**: Sincroniza servidores ativos com profile Docker + controla gateway via subprocess
- **docker_containers.py**: Lê containers MCP do `docker ps`, detecta agentes conectados, persiste histórico em SQLite
- **connection_db.py**: Banco SQLite para histórico de conexões (`~/.config/gmcp/connections.db`)
- **mcp_relay.py**: Relay SSE que mantém 1 container MCP rodando para N clientes (modo compartilhado)

#### Web Adapter (`backend/main.py`)
- FastAPI REST API que expõe o `GatewayService` via HTTP
- Endpoints em `/api/*`
- Recursos do sistema (`/api/resources`) com detecção de gateway online

## Fluxo de Dados

### Instalação de Servidor
```
Usuário → TUI/Web → API → GatewayService.install(name)
  → StateRepository.save() (adiciona ao JSON)
  → ProfileSync.sync() (atualiza profile Docker)
  → GatewayController.restart() (reinicia gateway)
```

### Histórico de Conexões
```
Web UI → /api/connections → DockerConnectionRepo.list_connections()
  → docker ps -a (containers atuais)
  → parse /tmp/gateway.log (logs de inicialização)
  → persist_records() → SQLite (~/.config/gmcp/connections.db)
  → load_history() → retorna merge
```

### Modo Compartilhado
```
Usuário → TUI [s] / Web Share → POST /api/servers/{name}/share
  → McpRelay.start()
    → docker run -i --rm mcp/SERVER (1 container)
    → HTTPServer na porta 3100+ (SSE)
    → stdin/stdout pipe para todos os clientes
  5 agentes conectam → 1 container atende todos
```

## Dependências

```
backend/
├── core/         → entities, ports, services, i18n, integrations  (stdlib)
├── adapters/     → sqlite3, json, subprocess, os, http.server     (stdlib)
├── main.py       → fastapi, uvicorn                               (framework)
└── tests/        → pytest, httpx/TestClient                       (teste)
```

O core é **puro Python stdlib** — pode ser testado sem frameworks.
