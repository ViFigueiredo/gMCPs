# Deployment

## Gateway MCP

O gateway Docker MCP é o ponto de entrada único para todos os clientes MCP.

```bash
# Início rápido
./start-gateway.sh

# Manualmente
docker mcp gateway run \
  --profile profile \
  --transport sse \
  --port 3099 \
  --long-lived
```

### start-gateway.sh
1. Mata processo gateway anterior (`pkill -9 -f "docker mcp gateway run"`)
2. Remove containers MCP órfãos (`docker rm -f $(docker ps -q --filter "label=docker-mcp=true")`)
3. Aguarda 1s
4. Sobe gateway com `--profile profile --transport sse --port 3099 --long-lived`

## Backend (FastAPI)

```bash
# Desenvolvimento (com reload)
uvicorn backend.main:app --reload --port 8000

# Produção
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## Frontend (Vue 3)

```bash
# Desenvolvimento
npx vite

# Build produção
npx vite build

# Preview produção
npx vite preview
```

O build gera arquivos estáticos em `dist/`.

## Monorepo

```bash
# Tudo junto (desenvolvimento)
npm run dev:all    # Gateway + Backend + Frontend
```

## Variáveis de Ambiente

| Variável | Obrigatório | Descrição |
|----------|-------------|-----------|
| `MCP_GATEWAY_AUTH_TOKEN` | Sim | Token de autenticação do gateway |
| `EXA_API_KEY` | Para exa | API key Exa |
| `SENTRY_AUTH_TOKEN` | Para sentry | Token Sentry |
| `GITHUB_PERSONAL_ACCESS_TOKEN` | Para github | Token GitHub |

## Portas

| Serviço | Porta |
|---------|-------|
| Gateway MCP | 3099 |
| Backend API | 8000 |
| Frontend (Vite) | 5173 |

## Arquivos de Estado

| Arquivo | Propósito |
|---------|-----------|
| `~/.config/gmcp/state.json` | Servidores instalados + ativos |
| `~/.docker/mcp/mcp-toolkit.db` | Profile Docker + catálogo |
| `/tmp/gateway.log` | Log do gateway |

## Notas de Produção

- CORS: atualmente aberto (`allow_origins=["*"]`); restrinja em produção
- SQLite: não escala para múltiplos processos concorrentes; considere PostgreSQL se necessário
- Token de autenticação do gateway (`mcp-local-token`): troque por um valor seguro em produção
- O arquivo `.env` contém API keys reais — **nunca commitar**
- O gateway `--long-lived` mantém containers rodando entre requisições
