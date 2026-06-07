# gmcp — Gateway MCP Manager

Gerencia servidores MCP (Model Context Protocol) do Docker MCP Gateway com duas interfaces: **TUI curses** e **Web Vue 3**.

## Visão Geral

O Docker MCP Gateway expõe servidores MCP via SSE em `http://localhost:3099/sse`. O gmcp gerencia o ciclo de vida desses servidores — instala, ativa/desativa, remove — sincronizando com o profile Docker subjacente.

```
┌─────────────────────────────────────────────┐
│                gmcp                          │
│  ┌─────────┐  ┌──────────┐  ┌────────────┐  │
│  │ TUI     │  │ Web UI   │  │ API REST   │  │
│  │(curses) │  │ (Vue 3)  │  │(FastAPI)   │  │
│  └────┬────┘  └────┬─────┘  └─────┬──────┘  │
│       └────────────┼──────────────┘          │
│                    ▼                         │
│           ┌────────────────┐                 │
│           │ GatewayService │ (hexagonal)     │
│           └───┬────┬────┬──┘                 │
│  ┌────────┐ ┌──┴──┐ ┌──┴──┐ ┌───────────┐  │
│  │ SQLite │ │File │ │Docker│ │Subprocess │  │
│  │Catalog │ │State│ │Profile││Gateway    │  │
│  └────┬───┘ └─────┘ └──┬───┘ └─────┬─────┘  │
│       ▼                ▼           ▼         │
│  mcp-toolkit.db   state.json   docker CLI    │
└─────────────────────────────────────────────┘
```

## Interfaces

| Interface | Caminho | Tecnologia |
|-----------|---------|------------|
| **TUI** | `gmcp` (symlink) | Python curses |
| **Web** | `http://localhost:5173` | Vue 3 + Vite + Tailwind |
| **API** | `http://localhost:8000/api` | FastAPI + Uvicorn |

## Funcionalidades

- **Home**: Estatísticas do gateway, logs recentes, restart
- **MCPs**: Servidores instalados com filtro All/Active/Inactive, busca, toggle, remoção
- **Market**: Catálogo de servidores disponíveis, seleção múltipla para instalação, modal de detalhes
- **i18n**: pt-BR e en-US (detecção automática via `LANG`/`navigator.language`)
- **Confirmação**: Diálogos antes de ações destrutivas

## Suporte a Plataformas

| SO | TUI | Web | API | Observação |
|----|-----|-----|-----|------------|
| 🐧 **Linux** | ✅ | ✅ | ✅ | Alvo principal |
| 🪟 **Windows (WSL2)** | ✅ | ✅ | ✅ | Necessita Docker Desktop com integração WSL2 |
| 🍎 **macOS** | ✅ | ✅ | ✅ | TUI funcional (curses nativo via Darwin). `/proc/` e `free/ss` não existem, mas `docker-mcp` e Docker Desktop com VM Linux funcionam |
| 🪟 **Windows nativo** | ❌ | ✅ | ❌ | Sem suporte a `curses` e `/proc/` |

> O **Docker MCP Gateway** (`docker-mcp`) e os comandos de monitoramento (`/proc/`, `free`, `df`) são específicos do kernel Linux. No Windows, utilize **WSL2** para funcionamento completo.

### Windows com WSL2

```bash
# 1. Instalar Docker Desktop e ativar integração WSL2
# 2. No terminal WSL2 (Ubuntu/Debian):
sudo apt install python3 nodejs npm
npm install -g @figcodessolucoes/gmcps

# 3. Iniciar gateway
./start-gateway.sh

# 4. Usar
gmcps           # TUI
gmcps-web       # Servidor web (API :8000 + frontend :8173)
# Acessar a web UI do Windows em http://localhost:8173/
```

## Quick Start

### Instalação via npm (recomendado)

```bash
npm install -g @figcodessolucoes/gmcps

gmcps           # TUI curses
gmcps-web       # Servidor web (API :8000 + frontend :8173)
```

### Desenvolvimento (repositório clonado)

```bash
# 1. Iniciar o gateway Docker MCP
./start-gateway.sh

# 2. Iniciar backend + frontend
npm run dev:all

# 3. Abrir interfaces
gmcp                          # TUI
firefox http://localhost:5173  # Web

# Ou individualmente:
npm run dev:backend            # Apenas API (:8000)
npm run dev                    # Apenas frontend (:5173)
```

## Stack

### Backend
- **Python 3.14+** — runtime
- **FastAPI + Uvicorn** — REST API
- **SQLite** — catálogo MCP Docker (`mcp-toolkit.db`)
- **Pytest** — testes unitários (27 testes)

### Frontend (Web)
- **Vue 3.5** — framework SPA
- **Vite 8** — bundler
- **TypeScript 6** — tipagem
- **Pinia 3** — estado global
- **Vue Router 5** — navegação
- **Tailwind CSS 4** — estilização
- **vue-i18n 10** — internacionalização
- **Vitest 4** — testes unitários
- **Playwright 1.59** — testes e2e

### TUI
- **Python curses** — terminal UI
- **stdlib apenas** — sem dependências externas

### DevOps
- **Docker** — runtime dos servidores MCP
- **concurrently** — dev server paralelo
- **Oxlint + ESLint** — linting
- **Prettier** — formatação

## Arquitetura

**Hexagonal (Ports & Adapters)** — todo o core está em `backend/core/` com interfaces abstratas em `ports.py`, implementações concretas em `adapters/`, e o `GatewayService` orquestrando a lógica de negócio. Tanto a TUI quanto a API REST FastAPI consomem o mesmo serviço.

```
backend/
├── core/
│   ├── entities.py    # Dataclasses de domínio
│   ├── ports.py       # Interfaces abstratas
│   ├── services.py    # Lógica de negócio
│   └── i18n.py        # Internacionalização compartilhada
├── adapters/
│   ├── sqlite_catalog.py   # Leitura do catálogo Docker
│   ├── file_state.py       # Persistência em state.json
│   └── docker_profile.py   # Sincronia profile + controle gateway
├── main.py            # FastAPI (adapter web)
└── tests/
    ├── test_core.py   # Testes do core
    └── test_api.py    # Testes da API
```

## Estado Atual

O estado dos servidores é gerenciado via `~/.config/gmcp/state.json`:

```json
{
  "installed": ["exa", "memory", "playwright"],
  "enabled": ["memory", "playwright"]
}
```

A sincronização com o Docker profile acontece automaticamente em toda alteração.

## Comandos Úteis

```bash
# Gateway
./start-gateway.sh                                    # Iniciar gateway
docker mcp gateway run --profile profile --transport sse --port 3099 --long-lived

# Backend
uvicorn backend.main:app --reload --port 8000

# Frontend
npx vite
npx vitest run
npx playwright test

# TUI
python3 mcp-tui.py
gmcp

# Codebase Intelligence
npm run fallow              # Full analysis (health 92 A)
npm run fallow:audit        # PR risk gate

# Security
npm run snyk:test           # Vulnerability scan (0 vulns)
npm run snyk:monitor        # Continuous monitoring

# Lint/Format
npm run lint
npm run format
```
