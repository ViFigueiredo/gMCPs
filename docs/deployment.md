# Deployment

## Formas de execução

| Método | Gateway | API | Frontend | Ideal para |
|--------|---------|-----|----------|------------|
| `gmcps` (CLI) | ✅ automático | ❌ | ❌ | Uso via terminal |
| `gmcps-web` (produção) | ✅ automático | ✅ | ✅ | Uso via navegador |
| `npm run dev:all` | ✅ manual | ✅ | ✅ | Desenvolvimento |
| Docker Compose | ✅ automático | ✅ | ✅ | Deploy containerizado |

## Execução Local

### CLI (TUI)

```bash
gmcps
# Inicia gateway + TUI curses. Gateway morre ao fechar a TUI.
```

### Servidor Web (produção)

```bash
gmcps-web
# Inicia gateway + API (:8000) + Frontend (:8173)
# Gateway watchdog: reinicia automaticamente se morrer

# Via PM2 (recomendado para produção)
pm2 start gmcps-web --name gmcps-web
pm2 save
pm2 startup
```

### Desenvolvimento

```bash
# Tudo junto
npm run dev:all

# Individual
npm run dev:backend            # API (:8000)
npm run dev                    # Frontend (:5173)
```

## Docker Compose

```bash
# Build + start
docker compose up -d

# Logs
docker compose logs -f

# Parar
docker compose down

# Acessar
# http://localhost:8173
```

### docker-compose.yml

```yaml
services:
  gmcp:
    build: .
    container_name: gmcp
    restart: unless-stopped
    ports:
      - "8000:8000"   # API
      - "8173:8173"   # Web UI
      - "3099:3099"   # Gateway SSE
    environment:
      - MCP_GATEWAY_AUTH_TOKEN=mcp-local-token
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - /usr/lib/docker/cli-plugins/docker-mcp:/usr/lib/docker/cli-plugins/docker-mcp:ro
      - gmcp-state:/root/.config/gmcp
      - mcp-profile:/root/.docker/mcp
```

### Dockerfile

O container inclui Python 3.14, Node.js 22, Docker CLI e o plugin `docker-mcp` (copiado do host).

## Gateway MCP

O gateway Docker MCP é o ponto de entrada único para todos os clientes MCP. Tanto `gmcps` quanto `gmcps-web` o iniciam automaticamente:

```bash
docker mcp gateway run \
  --profile profile \
  --transport sse \
  --port 3099 \
  --long-lived
```

### start-gateway.sh

Para uso manual ou debug:

```bash
./start-gateway.sh
# 1. Mata gateway anterior (pkill)
# 2. Remove containers MCP órfãos (docker rm -f todas as labels)
# 3. Sobe gateway com --long-lived
```

## PM2 (Produção)

```bash
npm install -g @figcodessolucoes/gmcps
pm2 start gmcps-web --name gmcps-web --update-env
pm2 save
pm2 startup  # Configura auto-início no boot

# Comandos úteis
pm2 logs gmcps-web
pm2 restart gmcps-web
pm2 stop gmcps-web
pm2 monit
```

O `gmcps-web` gerencia 3 processos:

```
pm2: gmcps-web
  ├── Gateway (docker mcp gateway run) — watchdog a cada 15s
  ├── API (uvicorn backend.main:app)
  └── Frontend (servidor HTTP Node.js)
```

## Modo Compartilhado

Cada MCP pode ser compartilhado entre múltiplos agentes via relay dedicado:

```bash
# API
curl -X POST localhost:8000/api/servers/memory/share
curl -X POST localhost:8000/api/servers/memory/unshare

# TUI: aba MCPs → tecla [s]
# Web: aba MCPs → botão Share
```

Portas: 3100+ (um relay por MCP compartilhado).

## Variáveis de Ambiente

| Variável | Obrigatório | Padrão | Descrição |
|----------|-------------|--------|-----------|
| `MCP_GATEWAY_AUTH_TOKEN` | Sim | `mcp-local-token` | Token de autenticação do gateway |
| `LANG` | Não | `pt_BR.UTF-8` | Idioma da TUI |
| `EXA_API_KEY` | Para exa | — | API key Exa |
| `SENTRY_AUTH_TOKEN` | Para sentry | — | Token Sentry |
| `GITHUB_PERSONAL_ACCESS_TOKEN` | Para github | — | Token GitHub |

## Portas

| Serviço | Porta |
|---------|-------|
| Gateway MCP | 3099 |
| Backend API | 8000 |
| Frontend (Web) | 8173 |
| Shared relays | 3100+ |
| Frontend (dev/Vite) | 5173 |

## Arquivos de Estado

| Arquivo | Propósito |
|---------|-----------|
| `~/.config/gmcp/state.json` | Servidores instalados + ativos + compartilhados |
| `~/.config/gmcp/connections.db` | Histórico persistente de conexões |
| `~/.config/gmcp/log_marker.txt` | Marcador de posição do log do gateway |
| `~/.docker/mcp/mcp-toolkit.db` | Profile Docker + catálogo |
| `/tmp/gateway.log` | Log do gateway |

## Notas de Produção

- **CORS**: atualmente aberto (`allow_origins=["*"]`); restrinja em produção
- **Token**: `mcp-local-token` é o padrão; troque por um valor seguro em produção
- **Containers órfãos**: o `start-gateway.sh` limpa containers com label `docker-mcp=true` ao iniciar
- **Watchdog**: o gateway é monitorado a cada 15s pelo `gmcps-web`; reinicia automaticamente se morrer
- **Histórico de conexões**: retido em SQLite mesmo após restart do gateway
- **Docker socket**: necessário para que o gateway dentro do container possa spawnar containers MCP
