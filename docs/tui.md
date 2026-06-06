# TUI (Terminal)

## Stack
- **Python 3.14+** — runtime
- **curses** — interface terminal (stdlib)
- **Zero dependências externas** — apenas biblioteca padrão

## Arquivo
`mcp-tui.py` (383 linhas)

## Uso

```bash
gmcp                          # via symlink
python3 mcp-tui.py            # direto
MCP_GATEWAY_AUTH_TOKEN=xxx gmcp  # com token customizado
```

## Navegação

### Teclado
| Tecla | Ação |
|-------|------|
| `←` / `→` | Navegar entre abas |
| `↑` / `↓` | Navegar na lista |
| `Enter` | Ação primária (toggle/install) |
| `d` | Detalhes (Market) |
| `r` | Remover (MCPs/Market) |
| `R` | Restart (Home) |
| `q` / `ESC` | Sair |
| `/` | Foco na busca |

### Mouse
| Ação | Efeito |
|------|--------|
| Click na tab | Muda aba |
| Click em item | Seleciona |
| Scroll vertical | Rola lista |
| Click em botão | Executa ação |

Scroll via xterm alternate scroll mode (`\033[?1007h`) + button-event tracking (`\033[?1002h`).

## Abas

### Home
- Logs recentes do gateway (últimas 5 linhas)
- Atalho: `R` para restart
- Notificação de sucesso/erro

### MCPs
- Filtro: All (padrão), Active, Inactive
- Busca textual inline
- Ações: `Enter` toggle, `r` remover
- Asterisco amarelo (*) indica servidor que requer API key

### Market
- Busca textual
- `Enter` para instalar, `d` para detalhes, `r` para remover (se instalado)
- Modal de detalhes com informações completas

## Internacionalização
Usa `backend/core/i18n.py` — detecção automática via `LANG` env.
```python
from backend.core.i18n import _
_( 'tab.home' )   # "Início" (pt-BR) / "Home" (en-US)
```

## Build
Não requer build — Python interpretado diretamente.
