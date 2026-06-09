# Documentação gmcp

Bem-vindo à documentação do **gmcp** (Gateway MCP Manager).

## Conteúdo

| Documento | Descrição |
|-----------|-----------|
| [Arquitetura](architecture.md) | Hexagonal (Ports & Adapters), fluxo de dados, relay, conexões |
| [Backend](backend.md) | FastAPI, core, adapters, API endpoints, shared mode |
| [Frontend](frontend.md) | Vue 3, componentes, stores, testes |
| [TUI](tui.md) | Curses, navegação, internacionalização, compartilhamento |
| [Deployment](deployment.md) | gmcps, gmcps-web, PM2, Docker Compose, produção |
| [Development](development.md) | Setup, comandos, workflow |

## Visão Geral

```
gmcp — Gerencia servidores MCP do Docker MCP Gateway
├── Interfaces
│   ├── TUI curses (terminal) — tecla [s] para compartilhar
│   └── Web Vue 3 (navegador) — toggle Share integrado
├── Backend compartilhado (hexagonal)
│   ├── Core: entidades, portas, serviços, i18n
│   ├── Adapters: SQLite, File, Docker, Relay, Conexões
│   └── Testes: Pytest (27)
├── Modo Compartilhado
│   └── McpRelay → 1 container, N agentes, porta 3100+
└── Persistência
    └── SQLite → histórico de conexões sobrevive a restarts
```
