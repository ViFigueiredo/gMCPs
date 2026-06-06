# Documentação gmcp

Bem-vindo à documentação do **gmcp** (Gateway MCP Manager).

## Conteúdo

| Documento | Descrição |
|-----------|-----------|
| [Arquitetura](architecture.md) | Hexagonal (Ports & Adapters), fluxo de dados |
| [Backend](backend.md) | FastAPI, core, adapters, testes |
| [Frontend](frontend.md) | Vue 3, componentes, stores, testes |
| [TUI](tui.md) | Curses, navegação, internacionalização |
| [Deployment](deployment.md) | Docker, gateway, produção |
| [Development](development.md) | Setup, comandos, workflow |

## Visão Geral

```
gmcp — Gerencia servidores MCP do Docker MCP Gateway
├── Interfaces
│   ├── TUI curses (terminal)
│   └── Web Vue 3 (navegador)
└── Backend compartilhado (hexagonal)
    ├── Core: entidades, portas, serviços
    ├── Adapters: SQLite, File, Docker, FastAPI
    └── Testes: Pytest (27)
```
