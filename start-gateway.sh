#!/bin/bash

export MCP_GATEWAY_AUTH_TOKEN="mcp-local-token"
PIDFILE="/tmp/gmcp-gateway.pid"
CONN_DB="$HOME/.config/gmcp/connections.db"

# Mata qualquer processo segurando a porta 3099 (incluindo docker-mcp real)
fuser -k 3099/tcp 2>/dev/null
sleep 1

# Remove containers órfãos MCP
docker rm -f $(docker ps -aq --filter "label=docker-mcp=true") 2>/dev/null
sleep 1

# Limpa registros zumbis de conexões de sessões anteriores
rm -f "$CONN_DB"

# ── Exporta credenciais criptografadas do BD ──
eval $(python3 -c "
import os, sys
sys.path.insert(0, os.path.expanduser('~/Documentos/MCPs'))
from backend.adapters.credential_repo import SqliteCredentialRepo
from backend.core.credential_manager import CredentialManager
db_path = os.path.expanduser('~/.docker/mcp/mcp-toolkit.db')
key_path = os.path.expanduser('~/.config/gmcp/credentials.key')
cm = CredentialManager(SqliteCredentialRepo(db_path), key_path=key_path)
for k, v in cm.get_env_dict().items():
    print(f'export {k}={v!r}')
" 2>/dev/null) || echo "⚠️ Nenhuma credencial encontrada no BD"

# Sobe gateway usando profile (on-demand: containers sobem apenas quando usados)
docker mcp gateway run \
  --profile profile \
  --transport sse \
  --port 3099 &
GATEWAY_PID=$!
echo "$GATEWAY_PID" > "$PIDFILE"
echo "Gateway iniciado (PID $GATEWAY_PID)"

# Aguarda o gateway
wait "$GATEWAY_PID"
