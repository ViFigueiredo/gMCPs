"""Internationalization — shared translation module for TUI and backend."""

import os

LOCALES: dict[str, dict[str, str]] = {
    "pt-BR": {
        # ── App ──
        "app.title": "gmcp — Gerenciador de MCPs do Gateway",
        "app.subtitle": "Instale, ative e gerencie MCPs para seu Gateway Docker",
        "app.quit": "[q] sair",
        # ── Tabs ──
        "tab.home": "Home",
        "tab.mcps": "MCPs",
        "tab.market": "Market",
        "tab.integrations": "Integrações",
        # ── Stats ──
        "stats.installed": "Instalados",
        "stats.active": "Ativos",
        "stats.catalog": "Catálogo",
        # ── Home ──
        "home.recent": "Últimas atividades",
        "home.no_logs": "(sem registros)",
        "home.quick_actions": "Ações rápidas",
        "home.restart": "Reiniciar Gateway",
        "home.edit_script": "Abrir script",
        "home.restart_title": "Reiniciar",
        "home.restart_msg": "Reiniciar o gateway agora?",
        "home.restart_ok": "Gateway reiniciado!",
        "home.restart_err": "Erro ao reiniciar gateway",
        # ── Integrations ──
        "integrations.title": "Integrações",
        "integrations.not_installed": "(não instalado)",
        "integrations.no_servers": "Nenhum servidor MCP configurado",
        "integrations.config_file": "Arquivo",
        "integrations.agent": "Ferramenta",
        "integrations.servers": "Servidores MCP",
        "integrations.add": "Adicionar MCP",
        "integrations.add_btn": "Adicionar",
        "integrations.add_title": "Adicionar servidor MCP em %s",
        "integrations.name": "Nome",
        "integrations.type": "Tipo",
        "integrations.command": "Comando",
        "integrations.url": "URL",
        "integrations.env": "Variáveis de ambiente",
        "integrations.server_added": "Servidor MCP adicionado!",
        "integrations.error": "Erro: %s",
        "integrations.not_found": "Config não encontrada para %s",
        "integrations.more": "(mais...)",
        # ── MCPs tab ──
        "mcps.search": "Buscar:",
        "mcps.filter_all": "Todos",
        "mcps.filter_active": "Ativos",
        "mcps.filter_inactive": "Inativos",
        "mcps.status": "Status",
        "mcps.server": "Servidor",
        "mcps.description": "Descrição",
        "mcps.actions": "Ações",
        "mcps.active": "[ ativo ]",
        "mcps.inactive": "[inativo]",
        "mcps.activate": "Ativar",
        "mcps.deactivate": "Desativar",
        "mcps.remove": "Remover",
        "mcps.empty": "Nenhum MCP instalado — vá na aba Market",
        "mcps.toggle_title_act": "Ativar",
        "mcps.toggle_title_dea": "Desativar",
        "mcps.toggle_msg_act": "Ativar '%s'?",
        "mcps.toggle_msg_dea": "Desativar '%s'?",
        "mcps.remove_title": "Remover",
        "mcps.remove_msg": "Remover '%s' permanentemente?",
        "mcps.needs_key": "Requer API key",
        # ── Market tab ──
        "market.search": "Buscar servidores...",
        "market.install_btn": "Instalar",
        "market.details": "Detalhes",
        "market.close": "Fechar",
        "market.status_installed": "[instalado]",
        "market.status_available": "[disponível]",
        "market.empty": "Catálogo vazio — verifique conexão Docker",
        "market.no_results": "Nenhum servidor encontrado",
        "market.install_title": "Instalar",
        "market.install_msg": "Instalar '%s' no gateway?",
        "market.remove_title": "Remover",
        "market.remove_msg": "Remover '%s' do gateway?",
        "market.detail_title_inst": "instalado",
        "market.detail_title_avail": "disponível",
        "market.detail_desc": "Descrição",
        "market.detail_status": "Status",
        "market.detail_api_key": "API Key",
        "market.detail_required": "Requerida",
        "market.detail_not_required": "Não requerida",
        "market.detail_no_desc": "(sem descrição)",
        "market.detail_activate": "Ativar",
        "market.detail_deactivate": "Desativar",
        "market.detail_remove": "Remover",
        # ── Confirm dialog ──
        "dialog.confirm": "Confirmar",
        "dialog.cancel": "Cancelar",
        # ── Status bar ──
        "status.home": "Home — %d ativos · %d instalados · %d catálogo",
        "status.mcps": "MCPs — %d ativos · %d inativos  | [Espaço] toggle  [1-3] filtro  [Esc] busca  [r] remover",
        "status.market": "Market — %d servidores  | [Enter] instalar/remover  [Esc] busca",
        "status.integrations": "Integrações — %d MCPs configurados",
        # ── Misc ──
        "loading": "Carregando...",
        "error.prefix": "Erro",
    },
    "en-US": {
        "app.title": "gmcp — MCP Gateway Manager",
        "app.subtitle": "Install, activate and manage MCPs for your Docker Gateway",
        "app.quit": "[q] quit",
        "tab.home": "Home",
        "tab.mcps": "MCPs",
        "tab.market": "Market",
        "tab.integrations": "Integrations",
        # ── Stats ──
        "stats.installed": "Installed",
        "stats.active": "Active",
        "stats.catalog": "Catalog",
        # ── Home ──
        "home.recent": "Recent activity",
        "home.no_logs": "(no logs)",
        "home.quick_actions": "Quick actions",
        "home.restart": "Restart Gateway",
        "home.edit_script": "Edit script",
        "home.restart_title": "Restart",
        "home.restart_msg": "Restart the gateway now?",
        "home.restart_ok": "Gateway restarted!",
        "home.restart_err": "Error restarting gateway",
        # ── Integrations ──
        "integrations.title": "Integrations",
        "integrations.not_installed": "(not installed)",
        "integrations.no_servers": "No MCP servers configured",
        "integrations.config_file": "Config file",
        "integrations.agent": "Tool",
        "integrations.servers": "MCP servers",
        "integrations.add": "Add MCP",
        "integrations.add_btn": "Add",
        "integrations.add_title": "Add MCP server to %s",
        "integrations.name": "Name",
        "integrations.type": "Type",
        "integrations.command": "Command",
        "integrations.url": "URL",
        "integrations.env": "Environment variables",
        "integrations.server_added": "MCP server added!",
        "integrations.error": "Error: %s",
        "integrations.not_found": "Config not found for %s",
        "integrations.more": "(more...)",
        # ── MCPs tab ──
        "mcps.search": "Search:",
        "mcps.filter_all": "All",
        "mcps.filter_active": "Active",
        "mcps.filter_inactive": "Inactive",
        "mcps.status": "Status",
        "mcps.server": "Server",
        "mcps.description": "Description",
        "mcps.actions": "Actions",
        "mcps.active": "[ active ]",
        "mcps.inactive": "[inactive]",
        "mcps.activate": "Activate",
        "mcps.deactivate": "Deactivate",
        "mcps.remove": "Remove",
        "mcps.empty": "No MCP installed — go to Market tab",
        "mcps.toggle_title_act": "Activate",
        "mcps.toggle_title_dea": "Deactivate",
        "mcps.toggle_msg_act": "Activate '%s'?",
        "mcps.toggle_msg_dea": "Deactivate '%s'?",
        "mcps.remove_title": "Remove",
        "mcps.remove_msg": "Remove '%s' permanently?",
        "mcps.needs_key": "Requires API key",
        "market.search": "Search servers...",
        "market.install_btn": "Install",
        "market.details": "Details",
        "market.close": "Close",
        "market.status_installed": "[installed]",
        "market.status_available": "[available]",
        "market.empty": "Catalog is empty — check Docker connection",
        "market.no_results": "No servers found",
        "market.install_title": "Install",
        "market.install_msg": "Install '%s' to the gateway?",
        "market.remove_title": "Remove",
        "market.remove_msg": "Remove '%s' from the gateway?",
        "market.detail_title_inst": "installed",
        "market.detail_title_avail": "available",
        "market.detail_desc": "Description",
        "market.detail_status": "Status",
        "market.detail_api_key": "API Key",
        "market.detail_required": "Required",
        "market.detail_not_required": "Not required",
        "market.detail_no_desc": "(no description)",
        "market.detail_activate": "Activate",
        "market.detail_deactivate": "Deactivate",
        "market.detail_remove": "Remove",
        "dialog.confirm": "Confirm",
        "dialog.cancel": "Cancel",
        "status.home": "Home — %d active · %d installed · %d catalog",
        "status.mcps": "MCPs — %d active · %d inactive  | [Space] toggle  [1-3] filter  [Esc] search  [r] remove",
        "status.market": "Market — %d servers  | [Enter] install/remove  [Esc] search",
        "status.integrations": "Integrations — %d MCPs configured",
        "loading": "Loading...",
        "error.prefix": "Error",
    },
}


def detect_lang() -> str:
    lang = os.environ.get("LANG", "pt_BR.UTF-8")
    if "en_US" in lang:
        return "en-US"
    return "pt-BR"


class I18n:
    """Simple i18n helper — callable as `_(key)`."""

    def __init__(self, lang: str | None = None):
        self.lang = lang or detect_lang()
        self._strings = LOCALES.get(self.lang, LOCALES["pt-BR"])

    def t(self, key: str, *args: str | int) -> str:
        val = self._strings.get(key, key)
        if args:
            return val % args
        return val

    def __call__(self, key: str, *args: str | int) -> str:
        return self.t(key, *args)


_: I18n = I18n()
