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
          ┌────────────────────┼────────────────────┐
          ▼                    ▼                    ▼
   ┌──────────────┐   ┌─────────────┐   ┌────────────────┐
   │SqliteCatalog │   │FileStateRepo│   │SqliteProfileSync│
   │(SQLite DB)   │   │(state.json) │   │(Docker profile) │
   └──────────────┘   └─────────────┘   └────────────────┘
          ▲                    ▲                    ▲
          │                    │                    │
   ┌──────┴──────┐   ┌────────┴───────┐   ┌────────┴───────┐
   │ mcp-toolkit │   │ ~/.config/gmcp/ │   │ Docker CLI     │
   │ .db         │   │ state.json      │   │ + profile SQLite│
   └─────────────┘   └────────────────┘   └────────────────┘
```

### Camadas

#### Core (`backend/core/`)
- **entities.py**: Dataclasses de domínio (`ServerInfo`, `ServerStatus`, `GatewayState`, `Stats`)
- **ports.py**: Interfaces abstratas (`CatalogRepository`, `StateRepository`, `ProfileSync`, `GatewayController`)
- **services.py**: `GatewayService` — orquestra lógica de negócio, recebe portas por injeção de dependência
- **i18n.py**: Internacionalização compartilhada entre TUI e backend

Regra: **core nunca importa adapters ou frameworks**.

#### Adapters (`backend/adapters/`)
- **sqlite_catalog.py**: Lê catálogo de servidores do banco SQLite do Docker
- **file_state.py**: Persiste estado (installed + enabled) em `state.json`
- **docker_profile.py**: Sincroniza servidores ativos com profile Docker + controla gateway via subprocess

#### Web Adapter (`backend/main.py`)
- FastAPI REST API que expõe o `GatewayService` via HTTP
- Endpoints em `/api/*`
- CORS configurado para desenvolvimento

## Fluxo de Dados

### Instalação de Servidor
```
Usuário → TUI/Web → API → GatewayService.install(name)
  → StateRepository.save() (adiciona ao JSON)
  → ProfileSync.sync() (atualiza profile Docker)
  → GatewayController.restart() (reinicia gateway)
```

### Listagem de Servidores
```
Usuário → TUI/Web → API → GatewayService.list_servers()
  → CatalogRepository.list_all() (lê SQLite)
  → StateRepository.load() (lê JSON)
  → Merge: catálogo + estado installed/enabled
```

## Dependências

```
backend/
├── core/         → entities, ports, services, i18n  (sem dependências externas)
├── adapters/     → sqlite3, json, subprocess, os     (stdlib + sqlite3)
├── main.py       → fastapi, uvicorn                  (framework)
└── tests/        → pytest, httpx/TestClient          (teste)
```

O core é **puro Python stdlib** — pode ser testado sem frameworks.
