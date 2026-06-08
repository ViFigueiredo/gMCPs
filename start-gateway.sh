#!/bin/bash

export MCP_GATEWAY_AUTH_TOKEN="mcp-local-token"

# Mata gateway anterior e containers órfãos (ativos + parados)
pkill -9 -f "docker mcp gateway run" 2>/dev/null
docker rm -f $(docker ps -aq --filter "label=docker-mcp=true") 2>/dev/null
sleep 1

# Sobe gateway usando profile (carrega servidores + tools do banco SQLite)
docker mcp gateway run \
  --profile profile \
  --transport sse \
  --port 3099 \
  --long-lived
