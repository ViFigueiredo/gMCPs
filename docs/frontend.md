# Frontend (Web)

## Stack
- **Vue 3.5** — framework
- **Vite 8** — build tool
- **TypeScript 6** — linguagem
- **Pinia 3** — gerenciamento de estado
- **Vue Router 5** — roteamento SPA
- **Tailwind CSS 4** — utilitários CSS
- **vue-i18n 10** — internacionalização
- **Vitest 4** — testes unitários
- **Playwright 1.59** — testes e2e

## Estrutura

```
src/
├── App.vue                    # Componente raiz (tabs + status bar)
├── main.ts                    # Bootstrap (app, pinia, router, i18n)
├── main.css                   # Import Tailwind CSS
├── api/
│   └── index.ts               # Cliente HTTP para API backend
├── router/
│   └── index.ts               # 3 rotas: /, /mcps, /market
├── stores/
│   └── gateway.ts             # Pinia store (servers, stats, ações)
├── types/
│   └── index.ts               # Interfaces TypeScript
├── components/
│   ├── StatsBar.vue           # Barra de estatísticas
│   └── ConfirmDialog.vue      # Modal de confirmação reutilizável
├── views/
│   ├── HomeView.vue           # Home: logs + restart
│   ├── McpsView.vue           # MCPs instalados: toggle + remove
│   └── MarketView.vue         # Catálogo: multi-select + install + detail modal
├── locales/
│   ├── pt-BR.json             # Traduções português
│   └── en-US.json             # Traduções inglês
└── __tests__/
    └── gateway.test.ts        # Testes Vitest da store
```

## Páginas

### Home (`/`)
- Logs recentes do gateway
- Ações rápidas (restart)
- Diálogo de confirmação para restart

### MCPs (`/mcps`)
- Filtro: All / Active / Inactive
- Busca textual
- Lista de servidores instalados com status, toggle, remover
- Diálogo de confirmação antes de toggle/remover

### Market (`/market`)
- Busca textual no catálogo
- Seleção múltipla (checkboxes + select-all)
- Botão "Instalar (N)" — desabilitado sem seleção
- Botão "Detalhes" abre modal com:
  - Nome, título, descrição
  - Status (instalado/disponível)
  - Requerimento de API key
  - Activate/Deactivate/Remove (se instalado)

## Componentes

### StatsBar
```vue
<StatsBar />
```
Grid 3 colunas: Installed, Active, Catalog. Cores cyan/green/yellow.

### ConfirmDialog
```vue
<ConfirmDialog
  :show="boolean"
  :title="string"
  :message="string"
  :confirm-label="string"
  :cancel-label="string"
  @confirm="handler"
  @cancel="handler"
/>
```
Modal via Teleport com overlay escuro.

## Store (Pinia)

```typescript
// src/stores/gateway.ts
const store = useGatewayStore()
store.servers           // Server[] (full list + status)
store.stats             // { catalog, installed, enabled }
store.installedServers  // Computed: only installed
store.availableServers  // Computed: not installed
store.fetchServers()    // GET /api/servers + /api/stats
store.install(name)     // POST /api/servers/{name}/install
store.uninstall(name)   // POST /api/servers/{name}/uninstall
store.toggle(name)      // POST /api/servers/{name}/toggle
store.restartGateway()  // POST /api/gateway/restart
store.fetchLogs(n?)     // GET /api/gateway/logs
```

## i18n

```typescript
const { t } = useI18n()
t('tab.home')     // "Início" (pt-BR) ou "Home" (en-US)
t('mcps.search')  // "Buscar servidor..." / "Search server..."
```

Detecção automática via `navigator.language`. Fallback pt-BR.

## Testes

```bash
npm run test:unit        # Vitest
npx playwright test      # E2E
```

- Vitest: testa store Pinia com api mockada
- Playwright: testa navegação básica
