# Plano de Implementação: Módulo de Logs no GMCP

## Objetivo
Adicionar um módulo de Logs para permitir a visualização e filtragem de logs gerados pelo Docker MCP Gateway.

## Etapas de Implementação

### 1. Definição da Estrutura de Logs
- Alterar `LogEntry` em `backend/core/entities.py`:
  ```python
  @dataclass
  class LogEntry:
      level: str  # INFO, WARNING, ERROR, DEBUG
      message: str
      source: str = "gateway"
  ```

### 2. Aprimoramento do Backend (Adapter Layer)
- Modificar `SubprocessGateway` em `backend/adapters/docker_profile.py`:
  - Implementar parsing de `/tmp/gateway.log` em objetos `LogEntry`.
- Atualizar interface `GatewayController` em `backend/core/ports.py` para método `get_logs(query=None, level=None, limit=50)`.

### 3. Atualização do GatewayService
- Adicionar lógica de filtragem no `GatewayService` (`backend/core/services.py`) usando os parâmetros de busca.

### 4. API (Web Adapter)
- Adicionar endpoint `GET /api/logs` em `backend/main.py`.
  - Parâmetros: `query` (string), `level` (filtro de nível), `limit` (número de linhas).

### 5. Frontend Web (Vue 3)
- Criar `src/views/LogsView.vue`.
- Componente de busca/filtro (input text, select para nível).

### 6. TUI (curses)
- Adicionar visualização de logs em `mcp-tui.py`.

---

## Estratégia de Validação
- Backend: Criar teste em `backend/tests/test_logs.py` para validar o parsing e filtragem.
- UI: Verificar se os logs aparecem na interface web e se o filtro de nível (Warning, Error) funciona.
- TUI: Garantir renderização correta de logs no terminal.
