#!/bin/bash
export MCP_GATEWAY_AUTH_TOKEN="mcp-local-token"
cd /home/viniciusfigueiredo/Documentos/MCPs
# Cleanup containers
docker rm -f $(docker ps -aq --filter "label=docker-mcp=true") 2>/dev/null
# Start gateway in foreground
exec docker mcp gateway run --profile profile --transport sse --port 3099
