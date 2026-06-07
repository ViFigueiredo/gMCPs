# AGENTS.md — Contexto do Projeto

## Projeto
**gmcp** (Gateway MCP Manager) — Gerencia servidores MCP do Docker MCP Gateway via TUI curses e Web Vue 3.

## Estrutura

```
/
├── backend/              # Core hexagonal + adapters + FastAPI
│   ├── core/             # entities, ports, services, i18n
│   ├── adapters/         # sqlite_catalog, file_state, docker_profile
│   ├── main.py           # FastAPI entry point
│   └── tests/            # Pytest (27 testes)
├── src/                  # Vue 3 SPA
│   ├── views/            # HomeView, McpsView, MarketView
│   ├── components/       # StatsBar, ConfirmDialog
│   ├── stores/           # Pinia: gateway.ts
│   ├── locales/          # pt-BR.json, en-US.json
│   └── __tests__/        # Vitest (5 testes)
├── mcp-tui.py            # TUI curses (383 linhas)
├── e2e/                  # Playwright tests
├── docs/                 # Documentação
├── start-gateway.sh      # Script de inicialização do gateway
├── docker-compose.yml    # Referência (não usado em runtime)
└── package.json          # Scripts monorepo
```

## Arquitetura
Hexagonal (Ports & Adapters). GatewayService em `backend/core/services.py` consumido tanto pela TUI quanto pela API REST. Portas abstratas em `backend/core/ports.py`.

## Estado Atual

### Concluído
- TUI curses completa (3 abas, mouse, teclado, i18n)
- Backend hexagonal + FastAPI REST
- Frontend Vue 3 + TypeScript + Tailwind CSS v4
- i18n pt-BR/en-US (TUI e Web)
- Testes backend (27) e frontend (5)
- Monorepo com `npm run dev:all`
- Sincronização com Docker profile
- WAL mode + timeout SQLite para evitar lock
- Fallow codebase intelligence (health score 92 A, 0 dead code, 0% dupes)

### Em Andamento
- *Nenhum*

### Bloqueado
- Docker secrets engine socket indisponível — API keys (exa, sentry, github) não são injetadas nos containers via `--profile`

### Pendente
- *Nenhum — todas as features planejadas foram implementadas*

## Comandos Essenciais

```bash
# Desenvolvimento
npm run dev:all            # Gateway + backend + frontend
npm run dev:backend        # Apenas backend (:8000)
npm run dev                # Apenas frontend (:5173)
./start-gateway.sh         # Iniciar gateway Docker

# Testes
npm run test:unit          # Vitest (frontend)
npx vitest run             # Vitest
cd backend && python3 -m pytest  # Pytest (backend)

# Codebase Intelligence (Fallow)
npm run fallow              # Full analysis
npm run fallow:audit        # PR risk gate
npm run fallow:health       # Health score

# Security (Snyk)
npm run snyk:test           # Dependency vulnerabilities
npm run snyk:monitor        # Continuous monitoring
npm run snyk:iac            # IaC security scan

# Lint
npm run lint               # Oxlint + ESLint
npm run format             # Prettier

# TUI
gmcp                       # Atalho
python3 mcp-tui.py         # Direto
```

## Portas
| Serviço | Porta |
|---------|-------|
| Gateway MCP | 3099 |
| Backend API | 8000 |
| Frontend (Vite) | 5173 |

## Variáveis Críticas
- `MCP_GATEWAY_AUTH_TOKEN=mcp-local-token` — token de autenticação do gateway
- `~/.config/gmcp/state.json` — estado: installed + enabled
- `~/.docker/mcp/mcp-toolkit.db` — SQLite com profile + catálogo
- `/tmp/gateway.log` — log do gateway

## i18n
- Detecção: `LANG` env (TUI), `navigator.language` (web)
- Fallback: pt-BR
- TUI usa `backend/core/i18n.py` (I18n class)
- Web usa `vue-i18n` com locale JSONs

## Regras
- Testes antes de implementar (TDD/SDD)
- Código em inglês, UI/localização em pt-BR/en-US
- Sem dependências externas para TUI (stdlib only)
- Hexagonal: adapters trocáveis (in-memory para testes)
