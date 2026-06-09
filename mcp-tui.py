#!/usr/bin/env python3
"""gmcp — Gerenciador de MCPs do Gateway"""

import os, curses, time, textwrap, sys
from backend.core.services import GatewayService
from backend.adapters.sqlite_catalog import SqliteCatalogRepo
from backend.adapters.file_state import FileStateRepo
from backend.adapters.docker_profile import SqliteProfileSync, SubprocessGateway
from backend.core.i18n import I18n
from backend.core import i18n as i18n_mod

def _(key, *args):
    return i18n_mod._.t(key, *args)
from backend.core.integrations import detect_agents

_svc = GatewayService(
    catalog=SqliteCatalogRepo(os.path.expanduser("~/.docker/mcp/mcp-toolkit.db")),
    state_repo=FileStateRepo(os.path.expanduser("~/.config/gmcp/state.json"),
                             os.path.expanduser("~/.docker/mcp/mcp-toolkit.db")),
    profile=SqliteProfileSync(os.path.expanduser("~/.docker/mcp/mcp-toolkit.db"),
                               lambda: _svc.list_catalog()),
    gateway=SubprocessGateway(),
)

# ─── curses app ──────────────────────────────────────────────────────────

class App:
    def __init__(self, stdscr):
        self.stdscr=stdscr
        self.tab=0; self.cursor=0; self.scroll=0; self.filter=0; self.log_filter="ALL"
        self.search=""; self.market_search=""; self.market_scroll=0; self.market_cursor=0
        self.dialog=None; self.msg=""; self.msg_tick=0; self.lang_idx=0
        self.integrations_cursor=0; self.integrations_expanded={}
        self.shared_servers={}
        self.connections=[]; self.conn_tags=[]; self.conn_cursor=0; self.conn_scroll=0
        self.conn_filter_mcp=set(); self.conn_date_start=""; self.conn_date_end=""
        self._setup()

    def _setup(self):
        curses.curs_set(0); curses.use_default_colors()
        curses.mousemask(curses.ALL_MOUSE_EVENTS)
        sys.stderr.write("\033[?1007h\033[?1002h"); sys.stderr.flush()
        curses.init_pair(1,curses.COLOR_GREEN,-1)
        curses.init_pair(2,curses.COLOR_YELLOW,-1)
        curses.init_pair(3,curses.COLOR_CYAN,-1)
        curses.init_pair(4,curses.COLOR_WHITE,curses.COLOR_BLUE)
        curses.init_pair(5,curses.COLOR_BLACK,curses.COLOR_WHITE)
        curses.init_pair(6,curses.COLOR_RED,-1)
        self.h,self.w=self.stdscr.getmaxyx()
        self.refresh_data()

    def refresh_data(self):
        state = _svc.get_state()
        self.installed = set(state.installed)
        self.enabled = set(state.enabled)
        self.catalog_items = [
            {"name": s.name, "title": s.title, "desc": s.desc, "secrets": s.secrets}
            for s in _svc.list_catalog()
        ]
        self.log_lines = _svc.get_logs()
        self.integrations = detect_agents()
        self.connections = _svc.list_connections(mcp_filter=list(self.conn_filter_mcp) if self.conn_filter_mcp else None, date_start=self.conn_date_start or None, date_end=self.conn_date_end or None)
        self.conn_tags = _svc.get_connection_tags()
        # Shared mode status
        try:
            import json, os
            sp = os.path.expanduser("~/.config/gmcp/state.json")
            if os.path.exists(sp):
                self.shared_servers = json.load(open(sp)).get("shared_servers", {})
            else:
                self.shared_servers = {}
        except Exception:
            self.shared_servers = {}

    # ─── helpers ─────────────────────────────────────────────────────

    def tab_bar(self):
        for i,t in enumerate([f" {_('tab.home')} ",f" {_('tab.mcps')} ",f" {_('tab.market')} ",f" {_('tab.integrations')} ",f" {_('tab.logs')} "]):
            s=curses.color_pair(4) if i==self.tab else curses.A_DIM
            x=2+i*8
            self.sa(0,x,f" {t.strip()} ",s)
        h=f"[1] [2] [3] [4]  {_('app.quit')}  [L]Lang={i18n_mod._.lang}"
        self.sa(0,self.w-len(h)-2,h,curses.A_DIM)

    def status_bar(self,m=""):
        self.stdscr.attron(curses.A_REVERSE)
        self.sa(self.h-1,0,f" {m} ".ljust(self.w-1))
        self.stdscr.attroff(curses.A_REVERSE)

    def center(self,r,t,a=0):
        self.sa(r,max(0,(self.w-len(t))//2),t[:max(1,self.w-1)],a)

    def show_dialog(self,t,m,y=None,n=None):
        lines=textwrap.wrap(m,self.w-12) if len(m)>self.w-12 else [m]
        dh=len(lines)+5; dw=min(60,self.w-8)
        self.dialog={"y":(self.h-dh)//2,"x":(self.w-dw)//2,"h":dh,"w":dw,"title":t,"lines":lines,"cb_yes":y,"cb_no":n}

    def draw_dialog(self):
        if not self.dialog: return
        d=self.dialog
        for i in range(d["h"]): self.sa(d["y"]+i,d["x"]," "*d["w"],curses.A_REVERSE)
        self.sa(d["y"],d["x"],"┌"+"─"*(d["w"]-2)+"┐",curses.A_REVERSE)
        self.sa(d["y"]+d["h"]-1,d["x"],"└"+"─"*(d["w"]-2)+"┘",curses.A_REVERSE)
        self.center(d["y"],d["title"],curses.A_REVERSE|curses.A_BOLD)
        for i,l in enumerate(d["lines"]): self.sa(d["y"]+2+i,d["x"]+2,l[:d["w"]-4],curses.A_REVERSE)
        by=d["y"]+d["h"]-2; bw=d["w"]
        btn_yes = f" [Y] {_('dialog.confirm')} "
        btn_no = f" [N] {_('dialog.cancel')} "
        total = len(btn_yes) + 1 + len(btn_no)
        bx = d["x"] + (bw - total) // 2
        d["btn_yes_x"] = bx
        d["btn_yes_w"] = len(btn_yes)
        d["btn_no_x"] = bx + len(btn_yes) + 1
        d["btn_no_w"] = len(btn_no)
        self.sa(by, bx, btn_yes, curses.A_REVERSE|curses.A_BOLD)
        self.sa(by, bx + len(btn_yes) + 1, btn_no, curses.A_REVERSE|curses.A_BOLD)

    def sa(self, y, x, s, attr=0):
        try:
            if y < 0 or y >= self.h or x < 0 or x >= self.w:
                return
            self.stdscr.addstr(y, min(x, self.w - 2), s[:max(1, self.w - x - 1)], attr)
        except curses.error:
            pass

    def close_dialog(self): self.dialog=None

    def notify(self,m,s=2): self.msg=m; self.msg_tick=time.time()+s

    # ─── shared header (shown on ALL tabs) ───────────────────────────

    def draw_header(self):
        ni=len(self.installed); ne=len(self.enabled); ct=len(self.catalog_items)
        self.center(2,_("app.title"),curses.A_BOLD|curses.color_pair(3))
        self.center(3,_("app.subtitle"),curses.A_DIM)
        stats=[(f" {_('stats.installed')} ",ni,curses.color_pair(3)),(f" {_('stats.active')} ",ne,curses.color_pair(1)),(f" {_('stats.catalog')} ",ct,curses.color_pair(2))]
        bw=18; gap=2; sx=max(2,(self.w-(len(stats)*(bw+gap)-gap))//2)
        for i,(l,v,c) in enumerate(stats):
            x=sx+i*(bw+gap)
            for r in range(4):
                b="┌"+"─"*(bw-2)+"┐" if r==0 else "│"+" "*(bw-2)+"│" if r<3 else "└"+"─"*(bw-2)+"┘"
                self.sa(5+r,x,b,curses.A_DIM)
            self.sa(6,x+(bw-len(l))//2,l,curses.A_DIM)
            vs=str(v)
            self.sa(7,x+(bw-len(vs))//2,vs,curses.A_BOLD|c)
        self.sa(9,2,"─"*max(2,self.w-6),curses.A_DIM)

    def draw_logs(self):
        self.draw_header()
        r = 10
        # ── Tag filters ──
        self.sa(r, 2, _("mcps.filter_all"), curses.A_BOLD if not self.conn_filter_mcp else curses.A_DIM)
        x = 2 + len(_("mcps.filter_all")) + 1
        for tag in self.conn_tags:
            label = f"{tag['mcp_name']}({tag['active']})"
            sel = tag['mcp_name'] in self.conn_filter_mcp
            self.sa(r, x, label, curses.color_pair(4) if sel else curses.A_NORMAL)
            x += len(label) + 1
        r += 1
        # ── Date filters ──
        self.sa(r, 2, f"[d] Data inicio: {self.conn_date_start or '-'}", curses.A_DIM)
        self.sa(r, max(35, self.w//2), f"[D] Data fim: {self.conn_date_end or '-'}", curses.A_DIM)
        r += 1
        self.sa(r, 2, "─" * max(2, self.w - 6), curses.A_DIM)
        r += 1
        # ── Table header ──
        hdr = f"{'AGENTE'.ljust(16)}{'MCP'.ljust(14)}{'CONTAINER'.ljust(14)}{'INICIO'.ljust(22)}{'FIM'.ljust(22)}{'STATUS'}"
        self.sa(r, 2, hdr[:max(1, self.w-4)], curses.A_BOLD | curses.A_UNDERLINE)
        r += 1
        self.sa(r, 2, "─" * max(2, self.w - 6), curses.A_DIM)
        r += 1
        # ── Table rows ──
        items = self.connections
        mv = max(3, self.h - r - 2)
        self.conn_cursor = max(0, min(self.conn_cursor, len(items) - 1)) if items else 0
        self.conn_scroll = max(0, min(self.conn_cursor - mv + 1, len(items) - mv))
        vis = items[self.conn_scroll:self.conn_scroll + mv]
        for idx, c in enumerate(vis):
            row = r + idx
            cur = self.conn_scroll + idx == self.conn_cursor
            if cur: self.stdscr.attron(curses.color_pair(4))
            agent = c.agent[:14].ljust(14)
            mcp = c.mcp_name[:12].ljust(12)
            cid = c.container_id[:12].ljust(12)
            start = c.started_at[:20]
            end = c.ended_at[:20] if c.ended_at else "-" + " " * 19
            st = c.status[:8]
            line = f"{agent} {mcp} {cid} {start} {end} {st}"
            self.sa(row, 2, line[:max(1, self.w-4)], 
                curses.color_pair(1) if c.status == "active" else curses.A_DIM)
            if cur: self.stdscr.attroff(curses.color_pair(4))
        if self.conn_scroll > 0:
            self.sa(r, self.w - 10, f"▲ {self.conn_scroll}", curses.A_DIM)
        if items and len(items) > self.conn_scroll + mv:
            rm = len(items) - self.conn_scroll - mv
            self.sa(r + mv, self.w - 10, f"▼ {rm}", curses.A_DIM)
        if not items:
            self.center(self.h // 2, "Nenhuma conexao encontrada", curses.A_DIM)


    def draw_home(self):
        if self.w < 30 or self.h < 15:
            self.center(self.h//2, "Terminal muito pequeno — redimensione", curses.A_BOLD | curses.color_pair(6))
            return
        self.draw_header()
        ry=11
        self.sa(ry,2,"─"*max(2,self.w-6),curses.A_DIM)
        self.sa(ry+1,2,_("home.recent"),curses.A_BOLD)
        for i,l in enumerate(self.log_lines[:5]): self.sa(ry+2+i,4,l.message.strip()[:max(1,self.w-10)],curses.A_DIM)
        if not self.log_lines: self.sa(ry+2,4,_("home.no_logs"),curses.A_DIM)
        ay=ry+8
        self.sa(ay,2,"─"*max(2,self.w-6),curses.A_DIM)
        self.sa(ay+1,2,_("home.quick_actions"),curses.A_BOLD)
        self.sa(ay+2,6,f" {_('home.restart')} [R] ",curses.color_pair(4))
        self.sa(ay+2,32,f" {_('home.edit_script')} [O] ",curses.color_pair(4))

    # ─── mcps tab ────────────────────────────────────────────────────

    def draw_mcps(self):
        self.draw_header()
        # search + filter
        self.sa(10,2,_("mcps.search"),curses.A_DIM)
        self.sa(10,10,f" {self.search} ",curses.A_NORMAL)
        flt=[f" {_('mcps.filter_all')} ",f" {_('mcps.filter_active')} ",f" {_('mcps.filter_inactive')} "]
        x=max(24,len(self.search)+14)
        self.sa(10,x,"|",curses.A_DIM)
        for i,f in enumerate(flt):
            self.sa(10,x+2,f,curses.color_pair(4) if i==self.filter else curses.A_DIM)
            x+=len(f)+1
        # header
        self.sa(11,2,"    Status     Servidor               Descricao",curses.A_BOLD|curses.A_UNDERLINE)
        self.sa(12,2,"─"*(self.w-6),curses.A_DIM)
        # items
        items=[]
        for s in self.catalog_items:
            if s["name"] not in self.installed: continue
            if self.filter==1 and s["name"] not in self.enabled: continue
            if self.filter==2 and s["name"] in self.enabled: continue
            if self.search and self.search.lower() not in s["name"].lower(): continue
            items.append(s)
        mv=max(3,self.h-16); self.cursor=max(0,min(self.cursor,len(items)-1)) if items else 0
        self.scroll=max(0,min(self.cursor-mv+1,len(items)-mv))
        vis=items[self.scroll:self.scroll+mv]
        for idx,s in enumerate(vis):
            row=idx+13; i=self.scroll+idx; act=s["name"] in self.enabled; cur=i==self.cursor
            if cur: self.stdscr.attron(curses.color_pair(4))
            if act: self.sa(row,2,f"{_('mcps.active')}  ",curses.color_pair(1)|curses.A_BOLD)
            else: self.sa(row,2,f"{_('mcps.inactive')}  ",curses.A_DIM)
            self.sa(row,13,s["name"][:22].ljust(22),curses.A_BOLD if act else curses.A_NORMAL)
            self.sa(row,36,s["desc"][:self.w-56])
            shared_port = self.shared_servers.get(s["name"])
            if shared_port:
                self.sa(row,self.w-9,f"S:{shared_port}",curses.color_pair(1)|curses.A_BOLD)
            elif s["secrets"]: self.sa(row,self.w-5,"*",curses.color_pair(2)|curses.A_BOLD)
            if cur: self.stdscr.attroff(curses.color_pair(4))
        if self.scroll>0:
            self.sa(13,2,f"\u25b2 {self.scroll} mais",curses.A_DIM)
        if items and len(items)>self.scroll+mv:
            rm=len(items)-self.scroll-mv; rw=min(self.h-3,13+mv)
            self.sa(rw,2,f"{rm} \u25bc",curses.A_DIM)
        if not items: self.center(self.h//2+3,_("mcps.empty"),curses.A_DIM)
        # detail
        if items and 0<=self.cursor<len(items):
            sel=items[self.cursor]; dy=self.h-3
            self.sa(dy,2,"─"*(self.w-6),curses.A_DIM)
            st="ATIVO" if sel["name"] in self.enabled else "INATIVO"
            sc=curses.color_pair(1) if sel["name"] in self.enabled else curses.color_pair(6)
            self.sa(dy+1,2,f" {sel['name']}: {sel['desc'][:self.w-70]}",curses.A_DIM)
            self.sa(dy+1,self.w-14,f"[{st}]",sc|curses.A_BOLD)

    # ─── market tab ──────────────────────────────────────────────────

    def draw_market(self):
        self.draw_header()
        self.sa(10,2,_("mcps.search"),curses.A_BOLD)
        self.sa(10,10,f" {self.market_search} ",curses.A_NORMAL)
        self.sa(11,2,"    Status     Servidor               Descricao",curses.A_BOLD|curses.A_UNDERLINE)
        self.sa(12,2,"─"*(self.w-6),curses.A_DIM)
        items=self.catalog_items
        if self.market_search: items=[s for s in items if self.market_search.lower() in s["name"].lower()]
        mv=max(3,self.h-16); self.market_cursor=max(0,min(self.market_cursor,len(items)-1)) if items else 0
        self.market_scroll=max(0,min(self.market_cursor-mv+1,len(items)-mv))
        vis=items[self.market_scroll:self.market_scroll+mv]
        for idx,s in enumerate(vis):
            row=idx+13; i=self.market_scroll+idx; inst=s["name"] in self.installed; cur=i==self.market_cursor
            if cur: self.stdscr.attron(curses.color_pair(4))
            self.sa(row,2,_("market.status_installed") if inst else _("market.status_available"),curses.color_pair(1)|curses.A_DIM if inst else curses.A_DIM)
            self.sa(row,14,s["name"][:22].ljust(22),curses.A_BOLD if inst else curses.A_NORMAL)
            self.sa(row,37,s["desc"][:self.w-50])
            if s["secrets"]: self.sa(row,self.w-5,"*",curses.color_pair(2)|curses.A_BOLD)
            if cur: self.stdscr.attroff(curses.color_pair(4))
        if self.market_scroll>0:
            self.sa(13,2,f"\u25b2 {self.market_scroll} mais",curses.A_DIM)
        if vis and len(items)>self.market_scroll+mv:
            rm=len(items)-self.market_scroll-mv; rw=min(self.h-3,13+mv)
            self.sa(rw,2,f"{rm} \u25bc",curses.A_DIM)
        if not vis: self.center(self.h//2+3,_("market.empty"),curses.A_DIM)
        if vis and 0<=self.market_cursor<len(items):
            sel=items[self.market_cursor]; dy=self.h-3
            self.sa(dy,2,"─"*(self.w-6),curses.A_DIM)
            st=_("market.detail_title_inst") if sel["name"] in self.installed else _("market.detail_title_avail")
            self.sa(dy+1,2,f" {sel['name']}: {sel['desc'][:self.w-74]}  [{st}]",curses.A_DIM)

    # ─── integrations tab ─────────────────────────────────────────────

    def _build_integrations_lines(self):
        lines = []
        self._int_map = []
        for a in self.integrations:
            idx = len(lines)
            self._int_map.append(("agent", idx))
            lines.append(("agent", a))
            if self.integrations_expanded.get(a.id):
                if a.config_path:
                    lines.append(("config", a.config_path))
                if a.error:
                    lines.append(("error", a.error))
                if a.servers:
                    for s in a.servers:
                        lines.append(("server", s))
                else:
                    lines.append(("noservers", True))
                lines.append(("spacer", True))
        return lines

    def draw_integrations(self):
        self.draw_header()
        self.sa(10,2,_("integrations.title"),curses.A_BOLD)
        self.sa(10,18,f"  {_('integrations.lang_hint')}",curses.A_DIM)
        lines = self._build_integrations_lines()
        mv = max(2, self.h - 16)
        total = len(lines)
        self.integrations_cursor = max(0, min(self.integrations_cursor, total - 1)) if lines else 0
        int_scroll = max(0, min(self.integrations_cursor - mv + 1, total - mv)) if lines else 0
        vis = lines[int_scroll:int_scroll + mv]
        for idx, (typ, data) in enumerate(vis):
            row = idx + 11
            cur = int_scroll + idx == self.integrations_cursor
            if cur:
                self.stdscr.attron(curses.color_pair(4))
            if typ == "agent":
                icon = "\u25bc" if self.integrations_expanded.get(data.id) else "\u25b6"
                inst = "" if data.installed else f" {_('integrations.not_installed')} "
                self.sa(row, 2, f" {icon} {data.name}  ({len(data.servers)}) ", curses.A_BOLD | curses.color_pair(3))
                if not data.installed:
                    self.sa(row, self.w - 22, inst, curses.color_pair(2))
            elif typ == "config":
                self.sa(row, 4, f"{_('integrations.config_file')}: {data}", curses.A_DIM)
            elif typ == "error":
                self.sa(row, 4, f"  {_('integrations.error', data)}", curses.color_pair(6))
            elif typ == "server":
                onoff = f"[on]" if data.enabled else "[off]" if data.enabled is not None else ""
                self.sa(row, 6, data.name, curses.A_NORMAL)
                self.sa(row, 28, data.type, curses.A_DIM)
                if onoff:
                    self.sa(row, self.w - 10, onoff, curses.color_pair(1) if data.enabled else curses.A_DIM)
            elif typ == "noservers":
                self.sa(row, 4, f"  {_('integrations.no_servers')}", curses.A_DIM)
            if cur:
                self.stdscr.attroff(curses.color_pair(4))
        if not lines:
            self.center(self.h // 2 + 3, _("integrations.no_servers"), curses.A_DIM)

    def run(self):
        self.refresh_data()
        while True:
            self.h,self.w=self.stdscr.getmaxyx(); self.stdscr.clear()
            self.tab_bar(); self.sa(1,0,"─"*(self.w-1),curses.A_DIM)
            if self.tab==0: self.draw_home()
            elif self.tab==1: self.draw_mcps()
            elif self.tab==2: self.draw_market()
            elif self.tab==3: self.draw_integrations()
            elif self.tab==4: self.draw_logs()
            if self.dialog: self.draw_dialog()
            if self.msg and time.time()<self.msg_tick: self.center(self.h-2,self.msg,curses.color_pair(1)|curses.A_BOLD)
            self.status_bar(self._status_msg())
            self.stdscr.refresh()
            if not self.handle_input(): break
        sys.stderr.write("\033[?1007l\033[?1002l"); sys.stderr.flush()

    def _status_msg(self):
        if self.tab==0: return _("status.home") % (len(self.enabled), len(self.installed), len(self.catalog_items))
        if self.tab==1:
            a=sum(1 for s in self.catalog_items if s["name"] in self.enabled and s["name"] in self.installed)
            i=sum(1 for s in self.catalog_items if s["name"] not in self.enabled and s["name"] in self.installed)
            shared=len(self.shared_servers)
            base=_("status.mcps") % (a, i)
            if shared: base += f"  | [s] shared={shared}"
            else: base += "  | [s] share"
            return base
        if self.tab==2: return _("status.market") % len(self.catalog_items)
        if self.tab==3:
            configured=sum(len(a.servers) for a in self.integrations)
            return _("status.integrations") % configured
        if self.tab==4: return _("status.logs") % len(self.connections)
        return ""

    # ─── input ───────────────────────────────────────────────────────

    def handle_input(self):
        key=self.stdscr.getch()
        # mouse
        if key==curses.KEY_MOUSE:
            try:
                _,mx,my,_,b=curses.getmouse()
            except: return True
            b4=getattr(curses,'BUTTON4_PRESSED',0); b5=getattr(curses,'BUTTON5_PRESSED',0)
            if (b&b4 or b&b5) and self.tab in (1,2):
                items=self._filtered_mcps() if self.tab==1 else self._filtered_market()
                mv=max(3,self.h-16); step=3
                if b&b4:
                    if self.tab==1: self.scroll=max(0,self.scroll-step)
                    else: self.market_scroll=max(0,self.market_scroll-step)
                else:
                    if self.tab==1: self.scroll=min(len(items)-mv,self.scroll+step)
                    else: self.market_scroll=min(len(items)-mv,self.market_scroll+step)
                if self.tab==1: self.cursor=min(self.cursor,self.scroll+mv-1)
                else: self.market_cursor=min(self.market_cursor,self.market_scroll+mv-1)
                return True
            if not (b&curses.BUTTON1_CLICKED): return True
            if self.dialog:
                d=self.dialog; by=d["y"]+d["h"]-2
                if my==by and "btn_yes_x" in d:
                    if d["btn_yes_x"]<=mx<d["btn_yes_x"]+d["btn_yes_w"]:
                        cb=d["cb_yes"]; self.dialog=None; cb and cb()
                    elif d["btn_no_x"]<=mx<d["btn_no_x"]+d["btn_no_w"]:
                        cb=d["cb_no"]; self.dialog=None; cb and cb()
                return True
            if my==0:
                xs=[2,10,18,26,34]
                for i,x in enumerate(xs):
                    if x<=mx<x+8: self.tab=i
                return True
            if self.tab==1 and my==10:
                ft=[(f" {_('mcps.filter_all')} ",24),(f" {_('mcps.filter_active')} ",30),(f" {_('mcps.filter_inactive')} ",39)]
                for l,fx in ft:
                    if fx<=mx<fx+len(l): self.filter=ft.index((l,fx)); self.cursor=0; return True
            if my>=13 and my<self.h-3:
                ii=my-13
                if self.tab==1:
                    items=self._filtered_mcps()
                    mv=self.h-16; vis=items[self.scroll:self.scroll+mv]
                    if 0<=ii<len(vis):
                        i=self.scroll+ii; self.cursor=i
                        self._confirm_toggle(vis[ii]["name"])
                elif self.tab==2:
                    items=self._filtered_market()
                    mv=self.h-16; vis=items[self.market_scroll:self.market_scroll+mv]
                    if 0<=ii<len(vis):
                        i=self.market_scroll+ii; self.market_cursor=i
                        n=vis[ii]["name"]
                        if n in self.installed:
                            self.show_dialog(_("market.remove_title"),_("market.remove_msg") % n,lambda n=n:self._uninstall(n),self.close_dialog)
                        else:
                            self.show_dialog(_("market.install_title"),_("market.install_msg") % n,lambda n=n:self._install(n),self.close_dialog)
            return True
        # dialog keys
        if self.dialog:
            if key in (ord('y'),ord('Y'),10):
                cb=self.dialog["cb_yes"]; self.dialog=None; cb and cb()
            elif key in (ord('n'),ord('N'),27):
                cb=self.dialog["cb_no"]; self.dialog=None; cb and cb()
            return True
        # tabs
        if key==ord('1'): self.tab=0; self.cursor=0
        elif key==ord('2'): self.tab=1; self.cursor=0
        elif key==ord('3'): self.tab=2; self.market_cursor=0
        elif key==ord('4'): self.tab=3
        elif key==ord('5'): self.tab=4
        elif key in (ord('l'),ord('L')):
            self.lang_idx = 1 - self.lang_idx
            i18n_mod.set_lang(["pt-BR", "en-US"][self.lang_idx])
            self.refresh_data()
        elif key==ord('q'): return False
        elif self.tab==4:
            if key==curses.KEY_UP and self.conn_cursor>0: self.conn_cursor-=1
            elif key==curses.KEY_DOWN and self.conn_cursor<len(self.connections)-1: self.conn_cursor+=1
            elif key in (ord('r'),ord('R')): self.refresh_data()
            elif key==ord(' '): self.conn_filter_mcp=set(); self.conn_date_start=""; self.conn_date_end=""; self.refresh_data()
            elif key==ord('d'):
                import subprocess
                ds = subprocess.run(["date","+%Y-%m-%d"],capture_output=True,text=True).stdout.strip()
                self.conn_date_start=ds; self.refresh_data()
            elif key==ord('D'):
                import subprocess
                de = subprocess.run(["date","+%Y-%m-%d"],capture_output=True,text=True).stdout.strip()
                self.conn_date_end=de; self.refresh_data()
            elif ord('1')<=key<=ord('9'):
                idx=key-ord('1'); tags=list(self.conn_tags)
                if idx<len(tags):
                    tn=tags[idx]['mcp_name']
                    if tn in self.conn_filter_mcp: self.conn_filter_mcp.discard(tn)
                    else: self.conn_filter_mcp.add(tn)
                    self.refresh_data()
        elif self.tab==0:
            if key in (ord('r'),ord('R')): self.show_dialog(_("home.restart"),_("home.restart_msg"),self._do_restart,self.close_dialog)
            elif key in (ord('o'),ord('O')): os.system(f"$EDITOR ~/Documentos/MCPs/start-gateway.sh &")
        elif self.tab==1:
            items=self._filtered_mcps()
            if key==curses.KEY_UP and self.cursor>0: self.cursor-=1
            elif key==curses.KEY_DOWN and self.cursor<len(items)-1: self.cursor+=1
            elif key==ord(' '):
                if items: self._confirm_toggle(items[self.cursor]["name"])
            elif key in (ord('r'),ord('R')):
                if items: self.show_dialog(_("mcps.remove_title"),_("mcps.remove_msg") % items[self.cursor]["name"],lambda n=items[self.cursor]["name"]:self._uninstall(n),self.close_dialog)
            elif key in (ord('s'),ord('S')):
                if items:
                    n=items[self.cursor]["name"]
                    if n in self.shared_servers:
                        self.show_dialog("Desativar Compartilhado",f"Desativar modo compartilhado para '{n}'?",lambda x=n:self._unshare(x),self.close_dialog)
                    else:
                        self._share(n)
            elif key==ord('1'): self.filter=0; self.cursor=0
            elif key==ord('2'): self.filter=1; self.cursor=0
            elif key==ord('3'): self.filter=2; self.cursor=0
            elif key==27: self.search=""; self.cursor=0
            elif key in (127,curses.KEY_BACKSPACE): self.search=self.search[:-1]; self.cursor=0
            elif 32<=key<127: self.search+=chr(key); self.cursor=0
        elif self.tab==2:
            items=self._filtered_market()
            if key==curses.KEY_UP and self.market_cursor>0: self.market_cursor-=1
            elif key==curses.KEY_DOWN and self.market_cursor<len(items)-1: self.market_cursor+=1
            elif key==10:
                if items:
                    n=items[self.market_cursor]["name"]
                    if n in self.installed:
                        self.show_dialog(_("market.remove_title"),_("market.remove_msg") % n,lambda n=n:self._uninstall(n),self.close_dialog)
                    else:
                        self.show_dialog(_("market.install_title"),_("market.install_msg") % n,lambda n=n:self._install(n),self.close_dialog)
            elif key==27: self.market_search=""; self.market_cursor=0
            elif key in (127,curses.KEY_BACKSPACE): self.market_search=self.market_search[:-1]; self.market_cursor=0
            elif 32<=key<127: self.market_search+=chr(key); self.market_cursor=0
        elif self.tab==4:
            if key==curses.KEY_UP and self.conn_cursor>0: self.conn_cursor-=1
            elif key==curses.KEY_DOWN and self.conn_cursor<len(self.connections)-1: self.conn_cursor+=1
            elif key in (ord('r'),ord('R')): self.refresh_data()
            elif key==ord(' '): self.conn_filter_mcp=set(); self.conn_date_start=""; self.conn_date_end=""; self.refresh_data()
            elif key==ord('d'):
                import subprocess
                ds = subprocess.run(["date","+%Y-%m-%d"],capture_output=True,text=True).stdout.strip()
                self.conn_date_start=ds; self.refresh_data()
            elif key==ord('D'):
                import subprocess
                de = subprocess.run(["date","+%Y-%m-%d"],capture_output=True,text=True).stdout.strip()
                self.conn_date_end=de; self.refresh_data()
            elif key in (ord('s'),ord('S')):
                if 0<=self.conn_cursor<len(self.connections):
                    c=self.connections[self.conn_cursor]
                    import subprocess
                    # Try label first, then image name, then kill gateway
                    r=subprocess.run(["docker","ps","--no-trunc","--format","{{.ID}}","--filter",f"label=docker-mcp-name={c.mcp_name}","--filter","label=docker-mcp=true"],capture_output=True,text=True,timeout=10)
                    ids=[x.strip() for x in r.stdout.strip().split("\n") if x.strip()]
                    if not ids:
                        r=subprocess.run(["docker","ps","--no-trunc","--format","{{.ID}}\t{{.Image}}"],capture_output=True,text=True,timeout=10)
                        for ln in r.stdout.strip().split("\n"):
                            pts=ln.split("\t")
                            if len(pts)==2 and c.mcp_name.lower() in pts[1].lower():
                                ids=[pts[0]]
                                break
                    if ids:
                        for cid in ids:
                            subprocess.run(["docker","stop",cid],capture_output=True,timeout=15)
                            subprocess.run(["docker","rm","-f",cid],capture_output=True,timeout=15)
                        self.notify(f"{c.mcp_name} stopped")
                    else:
                        subprocess.run(["pkill","-9","-f","docker mcp gateway run"],capture_output=True,timeout=5)
                        self.notify("Gateway restarted (no container found)")
                    self.refresh_data()
            elif ord('1')<=key<=ord('9'):
                idx=key-ord('1')
                tags=list(self.conn_tags)
                if idx<len(tags):
                    tn=tags[idx]['mcp_name']
                    if tn in self.conn_filter_mcp: self.conn_filter_mcp.discard(tn)
                    else: self.conn_filter_mcp.add(tn)
                    self.refresh_data()
        elif self.tab==3:
            lines = self._build_integrations_lines()
            if key == curses.KEY_UP and self.integrations_cursor > 0:
                self.integrations_cursor -= 1
            elif key == curses.KEY_DOWN and self.integrations_cursor < len(lines) - 1:
                self.integrations_cursor += 1
            elif key in (10, ord(' ')):
                if lines and 0 <= self.integrations_cursor < len(lines):
                    typ, data = lines[self.integrations_cursor]
                    if typ == "agent":
                        a_id = data.id
                        self.integrations_expanded[a_id] = not self.integrations_expanded.get(a_id)
        return True

    def _filtered_mcps(self):
        items=[]
        for s in self.catalog_items:
            if s["name"] not in self.installed: continue
            if self.filter==1 and s["name"] not in self.enabled: continue
            if self.filter==2 and s["name"] in self.enabled: continue
            if self.search and self.search.lower() not in s["name"].lower(): continue
            items.append(s)
        return items

    def _filtered_market(self):
        items=self.catalog_items
        if self.market_search: items=[s for s in items if self.market_search.lower() in s["name"].lower()]
        return items

    def _confirm_toggle(self,n):
        act=n in self.enabled
        self.show_dialog(_("mcps.toggle_title_dea") if act else _("mcps.toggle_title_act"),(_("mcps.toggle_msg_dea") if act else _("mcps.toggle_msg_act")) % n,lambda x=n:self._toggle(x),self.close_dialog)

    def _toggle(self,n):
        _svc.toggle(n); self.refresh_data(); self.notify(f"{_('mcps.activate') if n in self.enabled else _('mcps.deactivate')} {n}")

    def _install(self,n):
        _svc.install(n); self.refresh_data(); self.notify(f"{_('market.install_title')} {n}")

    def _uninstall(self,n):
        _svc.uninstall(n); self.refresh_data(); self.notify(f"{_('mcps.remove_title')} {n}")

    def _do_restart(self):
        self.notify(_("home.restart") + "...",10)
        if _svc.restart_gateway(): self.notify(_("home.restart_ok"))
        else: self.notify(_("home.restart_err"),3)

    def _share(self, n):
        try:
            _svc.enable_shared(n)
            self.notify(f"Compartilhado: {n}")
        except Exception as e:
            self.notify(f"Erro: {e}",3)
        self.refresh_data()

    def _unshare(self, n):
        try:
            _svc.disable_shared(n)
            self.notify(f"Compartilhamento desativado: {n}")
        except Exception as e:
            self.notify(f"Erro: {e}",3)
        self.refresh_data()

def main():
    try: curses.wrapper(lambda s: App(s).run())
    except KeyboardInterrupt: pass

if __name__=="__main__":
    main()
