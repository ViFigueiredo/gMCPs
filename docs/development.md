# Desenvolvimento

## Setup Inicial

```bash
# Clonar
git clone <repo>
cd gmcp

# Backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# Frontend
npm install
```

## Comandos

### Desenvolvimento
```bash
npm run dev:all        # Gateway + Backend + Frontend (concurrently)
npm run dev:backend    # Apenas backend (uvicorn :8000)
npm run dev            # Apenas frontend (vite :5173)
./start-gateway.sh     # Iniciar gateway Docker
```

### Testes
```bash
npm run test:unit              # Vitest (frontend, 5 testes)
cd backend && python3 -m pytest  # Pytest (backend, 27 testes)
npx playwright test            # E2E
```

### Lint & Formatação
```bash
npm run lint          # Oxlint + ESLint
npm run format        # Prettier
```

### Fallow — Análise de Codebase
[Fallow](https://docs.fallow.tools) é uma engine de inteligência de codebase para TypeScript/JavaScript. Analisa dead code, duplicação, complexidade, hotspots, arquitetura e dependências. Executado em Rust, zero-config, sem AI.

```bash
npm run fallow              # Análise completa
npm run fallow:audit        # PR risk gate (usar antes de commitar)
npm run fallow:health       # Health score + hotspots + refactor targets
npm run fallow:dead-code    # Cleanup opportunities
npm run fallow:fix          # Dry-run de autofix
```

**Estado atual**: health score **92 A**, 0 dead code, 0% duplicação, maintainability 91.9.

### Snyk — Segurança
```bash
npm run snyk:test       # Vulnerabilidades em dependências
npm run snyk:monitor    # Monitoramento contínuo
npm run snyk:iac        # IaC scan (Docker, docker-compose)
```

**Estado atual**: 0 vulnerabilidades em 84 dependências npm.



## Workflow

1. **Planejar**: ler AGENTS.md para entender estado atual
2. **Testar**: escrever testes primeiro (TDD/SDD)
3. **Implementar**: seguir arquitetura hexagonal + i18n
4. **Verificar**: `python3 -m pytest && npm run test:unit && npm run fallow:audit && npm run snyk:test && npm run lint`
5. **Documentar**: atualizar AGENTS.md e docs se necessário

## Convenções

- **Código**: inglês
- **UI/UX**: pt-BR e en-US via i18n
- **Commits**: mensagens descritivas em inglês
- **Testes**: pytest para backend, vitest para frontend
- **Arquitetura**: hexagonal (ports & adapters)

## Variáveis de Ambiente

```bash
export MCP_GATEWAY_AUTH_TOKEN=mcp-local-token
```

Ou use o `.env.example` como template:

```bash
cp .env.example .env
# Preencha as keys
```

## Debug

- Backend logs: stdout/stderr do uvicorn
- Gateway logs: `/tmp/gateway.log`
- Frontend: Vue DevTools (Alt+Shift+D no navegador)
- SQLite: `sqlite3 ~/.docker/mcp/mcp-toolkit.db`

## Troubleshooting

### Database is locked
Aguardar 15s (timeout configurado). Se persistir, reiniciar gateway.

### Porta ocupada
```bash
fuser -k 8000/tcp   # backend
fuser -k 5173/tcp   # frontend
fuser -k 3099/tcp   # gateway
```

### Gateway não inicia
Verificar Docker Desktop está rodando:
```bash
docker info
```
Verificar log: `cat /tmp/gateway.log`

### API keys não injetadas
Problema conhecido: Docker secrets engine socket indisponível. Servidores que requerem API key (exa, sentry, github) rodam sem as variáveis de ambiente necessárias.
