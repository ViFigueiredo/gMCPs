# Docker

## Visão Geral

O gmcp pode rodar em container Docker usando `docker-compose.yml`. O container inclui:

- Python 3.14 (backend)
- Node.js 22 (frontend server)
- Docker CLI + plugin MCP (gateway)
- Todo o código do gmcp

## Pré-requisitos

- Docker Engine 24+
- Docker Desktop com **plugin MCP** instalado (`/usr/lib/docker/cli-plugins/docker-mcp`)
- Docker Compose v2

## Uso

```bash
# Build + start
docker compose up -d

# Ver logs
docker compose logs -f

# Parar
docker compose down

# Acessar
# http://localhost:8173
```

## Volumes

| Volume montado | Função |
|---|---|
| `/var/run/docker.sock` | Socket Docker (obrigatório) |
| `/usr/lib/docker/cli-plugins/docker-mcp:ro` | Plugin MCP (read-only, obrigatório) |
| `gmcp-state:/root/.config/gmcp` | state.json + connections.db (persistente) |
| `mcp-profile:/root/.docker/mcp` | Profile Docker (persistente) |
| `/tmp/gateway.log` | Log do gateway |

## Portas expostas

| Porta | Serviço |
|---|---|
| 8000 | API FastAPI |
| 8173 | Frontend Web |
| 3099 | Gateway SSE |

## Variáveis de ambiente

| Variável | Padrão | Descrição |
|---|---|---|
| `MCP_GATEWAY_AUTH_TOKEN` | `mcp-local-token` | Token do gateway |
| `LANG` | `pt_BR.UTF-8` | Idioma |

## Arquitetura do container

```
┌──────────────────────────────────────────────┐
│  Container gmcp                               │
│                                                │
│  ┌──────────┐  ┌──────────┐  ┌─────────────┐ │
│  │ Frontend │  │  API     │  │ Gateway MCP  │ │
│  │ :8173    │  │ :8000    │  │ :3099        │ │
│  │ (Node.js)│  │(uvicorn) │  │(docker ps -a)│ │
│  └──────────┘  └──────────┘  └──────┬──────┘ │
│                                      │        │
│                                      ▼        │
│                             /var/run/docker   │
│                             .sock              │
└──────────────────────────────┼───────────────┘
                               │
                    ┌──────────┴──────────┐
                    │   Host Docker        │
                    │   (spawna containers │
                    │    mcp/memory, etc)  │
                    └─────────────────────┘
```

## Construção manual

```bash
docker build -t gmcp .
docker run -d \
  --name gmcp \
  -p 8000:8000 \
  -p 8173:8173 \
  -p 3099:3099 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v /usr/lib/docker/cli-plugins/docker-mcp:/usr/lib/docker/cli-plugins/docker-mcp:ro \
  -v gmcp-state:/root/.config/gmcp \
  -v mcp-profile:/root/.docker/mcp \
  -e MCP_GATEWAY_AUTH_TOKEN=mcp-local-token \
  gmcp
```

## Notas

- O `docker-mcp` CLI plugin é copiado do host no build (`COPY` no Dockerfile)
- A imagem precisa ser rebuildada se o plugin MCP for atualizado
- O gateway dentro do container usa o socket Docker do host para spawnar containers MCP
- O estado (state.json, connections.db) é persistido em volumes nomeados
