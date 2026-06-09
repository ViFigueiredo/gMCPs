#!/bin/bash

export MCP_GATEWAY_AUTH_TOKEN="mcp-local-token"
PIDFILE="/tmp/gmcp-gateway.pid"

# Se já existe um gateway rodando, mata ele primeiro
if [ -f "$PIDFILE" ] && kill -0 $(cat "$PIDFILE") 2>/dev/null; then
    OLD_PID=$(cat "$PIDFILE")
    echo "Matando gateway antigo (PID $OLD_PID)..."
    kill -9 "$OLD_PID" 2>/dev/null
    sleep 1
fi

# Remove containers órfãos
docker rm -f $(docker ps -aq --filter "label=docker-mcp=true") 2>/dev/null
sleep 1

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

# Sobe gateway usando profile
docker mcp gateway run \
  --profile profile \
  --transport sse \
  --port 3099 \
  --long-lived &
GATEWAY_PID=$!
echo "$GATEWAY_PID" > "$PIDFILE"
echo "Gateway iniciado (PID $GATEWAY_PID)"

# Aguarda o gateway (não faz pkill, pois mataria a si mesmo)
wait "$GATEWAY_PID"
