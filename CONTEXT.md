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
         Fix: downgrade fallow para ^2.88.3 + adiciona packageManager no package.json
         para compatibilidade com pnpm (safe-chain bloqueava 2.89.0)
         Migra para pnpm: packageManager pnpm@11.1.1, package-lock.json removido,
         pnpm-lock.yaml, .gitignore atualizado
44904bd Migra para pnpm: packageManager pnpm@11.1.1, remove package-lock.json
aec4da8 Fix: lowercase image names no docker profile sync (mcp/sqlite nao mcp/SQLite)
<próximo> Web: adiciona status bar animada no footer com lazy loading
         (ping animation + status message i18n). Store refatorada com
         withStatus() para tracking de operação atual.
021e70a Web: footer status bar animada com lazy loading (ping + i18n status messages)
<próximo> Fix: MarketView agora usa store.install() sequencial (não mais
         api.servers.installMany com Promise.all) para atualizar o
         reativo após cada instalação. Garante que a página sempre
         reflita o estado mais recente.
3dc4768 Fix: MarketView usa store.install() sequencial para atualizar pagina apos instalar
a485d31 Auto-restart gateway apos install/uninstall/toggle + filtro All/Installed/Available no Market
a06c6c5 Add pb-14 to main content so list items arent hidden behind fixed footer
9425262 Fix: filter/search/header row sticky no topo em McpsView e MarketView, apenas a listagem rola
0c115a4 Atualiza CONTEXT.md com commits recentes e novas features
57f8895 Add OBRIGATORIO: atualizar CONTEXT.md a cada commit como instrucao em INSTRUCTIONS.md
200215a Fix: TUI crash (UnboundLocalError xs). Fix: IntegrationsView vazia (usa api module). Adiciona seletor de idioma (L no TUI, dropdown Web). Adiciona dark/light mode no Web. TUI lingua dinâmica via i18n_mod._() + set_lang().
3b97095 Chore: publish @vifigueiredo/gmcps@1.0.0 no npm
bc41a3d Fix: npm publish config — .npmignore, dist build, gmcp-web production server
3374a0f Feat: install via npm (gmcp + gmcp-web CLI), postinstall pip deps
1833a81 Feat: modulo de logs com conexoes MCP, integracoes auto-add/remove, tema azul tecnologico, resource monitoring, health check ping, navegacao fluida sem loading
e56aedf feat: add resource monitoring (/api/resources) with RAM/CPU/storage of gateway + containers, connections table with filter/stop, theme overhaul with tech-blue palette and gMCP brand title, integrations auto-add with remove, health check via connected ref
ecf36c1 Fix: detect installed Kilo Code (binary=kilo). Integrations agents expandiveis (dropdown) com ▶/▼. Add catalog server dropdown no modal add-server. Language hint no TUI ([L] mudar idioma).
daf50a0 Fix: Claude Code auto-add remove entrada antiga do .claude.json antes de criar .mcp.json
87be54f Fix: Claude Code usa .mcp.json (local stdio) em vez de HTTP SSE — conexao com gateway falhava
0f2dcfa Fix: Codex CLI command como string + args array separados (sh -c wrapper)
5a74c2b Fix: Codex CLI usa docker run (stdio) em vez de remote SSE
110a4ad Fix: Claude Code auto-add usa type=http, detecta mcpServers em projetos
414c53a Feat: Claude Code agent detect + Codex TOML inline table fix
54c72bd Feat: compatibilidade macOS — ps/lsof alternativos para /proc/ e ss nos adapters
```

---

## Features Implementadas

### TUI curses (`mcp-tui.py`)
- 5 abas: Home (recursos + logs + restart), MCPs, Market, Integrações, Logs (conexões)
- Logs/Conexões: tabela com agent/MCP/container/status, filtros tag [1-9], data [d/D], stop [s]
- Navegação por teclado (setas, shortcuts) e mouse (clicks, scroll via xterm)
- Diálogos de confirmação antes de ações destrutivas
- Internacionalização pt-BR/en-US via `backend/core/i18n.py`
- Scroll livre (sem trava no min())

### Backend Hexagonal (`backend/`)
- `core/entities.py`: ServerInfo, ServerStatus, GatewayState, Stats, LogEntry, ContainerRecord (dataclasses)
- `core/ports.py`: CatalogRepository, StateRepository, ProfileSync, GatewayController, ConnectionRepository (ABCs)
- `core/services.py`: GatewayService com injeção de dependência
- `core/i18n.py`: I18n class com dicionários pt-BR/en-US
- `adapters/sqlite_catalog.py`: leitura do SQLite Docker (timeout 15s + WAL)
- `adapters/file_state.py`: persistência em `~/.config/gmcp/state.json`
- `adapters/docker_profile.py`: sync profile Docker + controle gateway via subprocess
- `main.py`: FastAPI REST (14+ endpoints) com CORS, incluindo /api/resources, /api/connections, /api/connections/tags, /api/connections/{name}/stop
- `adapters/docker_containers.py`: lê containers MCP do Docker + detecta agentes conectados
- 27 testes (pytest) — core + API com adapters in-memory

### Frontend Vue 3 (`src/`)
- 5 views: HomeView, McpsView, MarketView, IntegrationsView, LogsView
- LogsView: tabela de conexões MCP com filtros tag + data + stop
- IntegrationsView: auto-add de MCPs ausentes + remove
- Componentes: StatsBar, ConfirmDialog
- Pinia store (gateway.ts): servers, stats, resources, install/uninstall/toggle/restart, withStatus() wrapper, health check, fetchResources
- Todo search/filter + column header sticky no topo em McpsView e MarketView
- Footer status bar com ping animado + connected/disconnected reativo + i18n status messages
- vue-i18n com locale JSONs (pt-BR.json, en-US.json)
- Tailwind CSS v4, Vite 8, TypeScript 6
- Tema custom: paleta azul tecnológico (#0B8DFF) + prata, dark/light mode com CSS vars
- 5 testes (Vitest) + Playwright e2e

### Monorepo
- `npm run dev:all`: gateway + backend + frontend em paralelo
- `concurrently` com prefixos coloridos (gw, api, web)
- Publicado como `@figcodessolucoes/gmcps@1.0.0` no npm
- CLI: `gmcps` (TUI) e `gmcps-web` (servidor web production)

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

### Footer Escondido
- **Problema**: final das listagens (McpsView/MarketView) ficava atrás do footer fixo
- **Solução**: `pb-14` no `<main>` para dar espaço ao footer

### Filter + Header Sticky
- **Problema**: ao scrollar listagens longas, o filtro e cabeçalho das colunas sumiam
- **Solução**: `sticky top-0 z-10 bg-neutral-950 -mx-4 px-4` no wrapper do search/filter + header row em ambas as views

### Integrações
- **Módulo**: `backend/core/integrations.py` — detecta 5 agentes (OpenCode, Kilo Code, Codex CLI, Claude Code, OpenClaude)
- **Leitura**: lê MCP servers configurados nos respectivos config files (JSON/TOML)
- **Escrita**: adiciona novos MCP servers aos agentes via API
- **TOML**: parser mínimo para Codex CLI (`~/.codex/config.toml`), suporte a inline tables (`headers = {...}`)
- **Claude Code**: usa `.mcp.json` local (stdio) em vez de `.claude.json` global
- **Codex**: comando `sh -c exec docker run` com `command` string + `args` array separados
- **Web**: `IntegrationsView.vue` com auto-add de MCPs ausentes + botão remover
- **TUI**: aba "Integrações" (tecla [4]) com listagem dos agentes e servidores
- **i18n**: pt-BR/en-US no backend (TUI) e frontend (Vue)

### Language Switcher
- **TUI**: tecla `L` alterna entre pt-BR e en-US, i18n dinâmico via `i18n_mod._()` + `set_lang()`
- **Web**: dropdown na navbar com locale salvo em localStorage
- **Inicialização**: vue-i18n lê `localStorage.getItem('locale')` antes de fallback para `navigator.language`

### Theme Toggle (Web UI)
- Botão ☀/☾ na navbar alterna dark/light mode
- CSS override de `--color-neutral-*` + `--color-white`/`--color-black` para inverter paleta sem mudar templates
- Preferência salva em `localStorage`

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
