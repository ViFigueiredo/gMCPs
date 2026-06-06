# CONTEXT.md — Sumário do Projeto

## Projeto
**gmcp** (Gateway MCP Manager) — Gerencia servidores MCP do Docker MCP Gateway via TUI curses e Web Vue 3.

---

## Git Log — Commits

```
e076171 Adiciona configuração inicial do projeto com Vue 3 e Vite, incluindo
        arquivos de configuração, estrutura de diretórios e exemplos de testes.
badc057 Adiciona arquivos de configuração e scripts para gerenciamento de MCPs
c7f0d61 Refatora monorepo: move frontend para raiz, adiciona backend hexagonal,
        FastAPI REST, TUI curses, i18n, testes, docs, Fallow e Snyk.
<próximo> Fix: alinhamento grid McpsView/MarketView (minmax(0,1fr) + min-w-0)
         Remove pnpm-lock.yaml e re-instala dependências (npm install)
```

---

## Features Implementadas

### TUI curses (`mcp-tui.py`)
- 3 abas: Home (logs + restart), MCPs (toggle + remove), Market (install + detail modal)
- Navegação por teclado (setas, shortcuts) e mouse (clicks, scroll via xterm)
- Diálogos de confirmação antes de ações destrutivas
- Internacionalização pt-BR/en-US via `backend/core/i18n.py`
- Scroll livre (sem trava no min())

### Backend Hexagonal (`backend/`)
- `core/entities.py`: ServerInfo, ServerStatus, GatewayState, Stats (dataclasses)
- `core/ports.py`: CatalogRepository, StateRepository, ProfileSync, GatewayController (ABCs)
- `core/services.py`: GatewayService com injeção de dependência
- `core/i18n.py`: I18n class com dicionários pt-BR/en-US
- `adapters/sqlite_catalog.py`: leitura do SQLite Docker (timeout 15s + WAL)
- `adapters/file_state.py`: persistência em `~/.config/gmcp/state.json`
- `adapters/docker_profile.py`: sync profile Docker + controle gateway via subprocess
- `main.py`: FastAPI REST (10 endpoints) com CORS
- 27 testes (pytest) — core + API com adapters in-memory

### Frontend Vue 3 (`src/`)
- 3 views: HomeView (logs + restart), McpsView (filtro + toggle), MarketView (multi-select + modal)
- Componentes: StatsBar, ConfirmDialog
- Pinia store (gateway.ts): servers, stats, install/uninstall/toggle/restart
- vue-i18n com locale JSONs (pt-BR.json, en-US.json)
- Tailwind CSS v4, Vite 8, TypeScript 6
- 5 testes (Vitest) + Playwright e2e

### Monorepo
- `npm run dev:all`: gateway + backend + frontend em paralelo
- `concurrently` com prefixos coloridos (gw, api, web)

---

## Fixes & Refactors

### SQLite Database Lock
- **Problema**: `sqlite3.OperationalError: database is locked` quando backend e gateway acessavam o mesmo banco
- **Solução**: `timeout=15` + `PRAGMA journal_mode=WAL` em todos os adapters SQLite

### TUI Scroll Bug
- **Problema**: scroll travava no final da lista
- **Solução**: removido `self.scroll` da fórmula `min()`

### Web i18n Crash
- **Problema**: página web em branco — `v-for="t in tabs"` sombreava função `t()` do i18n
- **Solução**: renomeado loop variable para `tab`

---

## Upgrades & Integrações

### Fallow (Codebase Intelligence)
- Health score 92 A, 0 dead code, 0% duplication
- Config `.fallowrc.json` + baselines em `fallow-baselines/`
- Scripts npm: `fallow`, `fallow:audit`, `fallow:health`, `fallow:dead-code`, `fallow:fix`

### Snyk (Security)
- Scan automático de vulnerabilidades em dependências JS/Python
- Config `.snyk` com políticas de severidade e paths ignorados
- Scripts npm: `snyk:test`, `snyk:monitor`, `snyk:iac`

---

## Portas & Serviços

| Serviço | Porta | Comando |
|---------|-------|---------|
| Gateway MCP | 3099 | `./start-gateway.sh` |
| Backend API | 8000 | `npm run dev:backend` |
| Frontend Vite | 5173 | `npm run dev` |

## Links Úteis

- [Documentação](docs/index.md)
- [README](README.md)
- [AGENTS.md](AGENTS.md) — contexto para IAs
- [INSTRUCTIONS.md](INSTRUCTIONS.md) — diretrizes para IAs
