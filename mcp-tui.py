#!/usr/bin/env python3
"""gmcp — Gerenciador de MCPs do Gateway"""

import json, sqlite3, subprocess, os, curses, time, textwrap, sys

DB = os.path.expanduser("~/.docker/mcp/mcp-toolkit.db")
LOG = "/tmp/gateway.log"
STATE = os.path.expanduser("~/.config/gmcp/state.json")
SECRETS_MAP = {"neon":"NEON_API_KEY","exa":"EXA_API_KEY","sentry":"SENTRY_AUTH_TOKEN","github":"GITHUB_PERSONAL_ACCESS_TOKEN"}

def qs(sql):
    conn=sqlite3.connect(DB); r=conn.execute(sql).fetchall(); conn.close(); return r

def get_profile():
    r=qs("SELECT servers FROM working_set WHERE id='profile'")
    return json.loads(r[0][0]) if r else []

def get_catalog():
    r=qs("SELECT snapshot FROM catalog_server ORDER BY json_extract(snapshot,'$.server.name')")
    out=[]
    for (s,) in r:
        snap=json.loads(s).get("server",{})
        n=snap.get("name")
        if n: out.append({"name":n,"title":snap.get("title",""),"desc":snap.get("description",""),"secrets":len(snap.get("secrets",[]))>0})
    return out

def load_state():
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    try:
        with open(STATE) as f: return json.load(f)
    except:
        pn=[s.get("snapshot",{}).get("server",{}).get("name") for s in get_profile() if s.get("snapshot",{}).get("server",{}).get("name")]
        s={"installed":pn.copy(),"enabled":pn.copy()}; save_state(s); return s

def save_state(s):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    with open(STATE,'w') as f: json.dump(s,f,indent=2)

def sync_profile(enabled):
    all_servers=get_profile(); pn={s.get("snapshot",{}).get("server",{}).get("name") for s in all_servers}
    kept=[s for s in all_servers if s.get("snapshot",{}).get("server",{}).get("name") in enabled]
    conn=sqlite3.connect(DB)
    for n in enabled:
        if n not in pn:
            snap=next((s for s in get_catalog() if s["name"]==n),None)
            if snap:
                entry={"type":"image","secrets":"default","tools":None,"image":f"mcp/{n}@sha256:latest","catalog_ref":"mcp/docker-mcp-catalog:latest",
                       "snapshot":{"server":{"name":n,"type":"server","image":f"mcp/{n}","description":snap["desc"],"title":snap["title"],
                                             "secrets":[{"name":f"{n}.api_key","env":f"{n.upper()}_API_KEY"}] if snap["secrets"] else [],"remote":{}}}}
                kept.append(entry)
    conn.execute("UPDATE working_set SET servers=? WHERE id='profile'",(json.dumps(kept),))
    conn.commit(); conn.close()
    return kept

def install_server(n):
    s=load_state()
    if n not in s["installed"]: s["installed"].append(n)
    if n not in s["enabled"]: s["enabled"].append(n)
    save_state(s); sync_profile(set(s["enabled"])); return True

def uninstall_server(n):
    s=load_state()
    s["installed"]=[x for x in s["installed"] if x!=n]
    s["enabled"]=[x for x in s["enabled"] if x!=n]
    save_state(s); sync_profile(set(s["enabled"])); return True

def toggle_active(n):
    s=load_state()
    if n in s["enabled"]: s["enabled"].remove(n)
    else: s["enabled"].append(n)
    save_state(s); sync_profile(set(s["enabled"])); return n in s["enabled"]

def restart_gw():
    subprocess.run(["pkill","-9","-f","docker mcp gateway run"],capture_output=True)
    os.system("(export MCP_GATEWAY_AUTH_TOKEN=mcp-local-token; "
              "nohup docker mcp gateway run --profile profile "
              "--transport sse --port 3099 --long-lived > /tmp/gateway.log 2>&1 &)")
    for _ in range(30):
        r=subprocess.run(["ss","-tlnp"],capture_output=True,text=True)
        if "3099" in r.stdout: return True
        time.sleep(0.5)
    return False

def get_recent_log(n=5):
    try:
        with open(LOG) as f: lines=[l for l in f.read().split("\n") if l.strip()]
        return lines[-n:]
    except: return []

# ─── curses app ──────────────────────────────────────────────────────────

HDR_END = 10  # rows 2-9 are header, content starts at 10

class App:
    def __init__(self, stdscr):
        self.stdscr=stdscr
        self.tab=0; self.cursor=0; self.scroll=0; self.filter=0
        self.search=""; self.market_search=""; self.market_scroll=0; self.market_cursor=0
        self.dialog=None; self.msg=""; self.msg_tick=0
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
        self.state=load_state()
        self.installed=set(self.state["installed"])
        self.enabled=set(self.state["enabled"])
        self.catalog_items=get_catalog()
        self.log_lines=get_recent_log()

    # ─── helpers ─────────────────────────────────────────────────────

    def tab_bar(self):
        for i,t in enumerate([" Home "," MCPs "," Market "]):
            s=curses.color_pair(4) if i==self.tab else curses.A_DIM
            x=2+i*8
            self.stdscr.addstr(0,x,f" {t.strip()} ",s)
        h="[1] [2] [3]  [q] sair"
        self.stdscr.addstr(0,self.w-len(h)-2,h,curses.A_DIM)

    def status_bar(self,m=""):
        self.stdscr.attron(curses.A_REVERSE)
        self.stdscr.addstr(self.h-1,0,f" {m} ".ljust(self.w-1))
        self.stdscr.attroff(curses.A_REVERSE)

    def center(self,r,t,a=0):
        self.stdscr.addstr(r,max(0,(self.w-len(t))//2),t[:self.w-1],a)

    def show_dialog(self,t,m,y=None,n=None):
        lines=textwrap.wrap(m,self.w-12) if len(m)>self.w-12 else [m]
        dh=len(lines)+5; dw=min(60,self.w-8)
        self.dialog={"y":(self.h-dh)//2,"x":(self.w-dw)//2,"h":dh,"w":dw,"title":t,"lines":lines,"cb_yes":y,"cb_no":n}

    def draw_dialog(self):
        if not self.dialog: return
        d=self.dialog
        for i in range(d["h"]): self.stdscr.addstr(d["y"]+i,d["x"]," "*d["w"],curses.A_REVERSE)
        self.stdscr.addstr(d["y"],d["x"],"┌"+"─"*(d["w"]-2)+"┐",curses.A_REVERSE)
        self.stdscr.addstr(d["y"]+d["h"]-1,d["x"],"└"+"─"*(d["w"]-2)+"┘",curses.A_REVERSE)
        self.center(d["y"],d["title"],curses.A_REVERSE|curses.A_BOLD)
        for i,l in enumerate(d["lines"]): self.stdscr.addstr(d["y"]+2+i,d["x"]+2,l[:d["w"]-4],curses.A_REVERSE)
        by=d["y"]+d["h"]-2; bx=d["x"]+d["w"]//2-10
        self.stdscr.addstr(by,bx," [Y] Yes ",curses.A_REVERSE|curses.A_BOLD)
        self.stdscr.addstr(by,bx+9," [N] No  ",curses.A_REVERSE|curses.A_BOLD)

    def close_dialog(self): self.dialog=None

    def notify(self,m,s=2): self.msg=m; self.msg_tick=time.time()+s

    # ─── shared header (shown on ALL tabs) ───────────────────────────

    def draw_header(self):
        ni=len(self.installed); ne=len(self.enabled); ct=len(self.catalog_items)
        self.center(2,"gmcp — Gerenciador de MCPs do Gateway",curses.A_BOLD|curses.color_pair(3))
        self.center(3,"Instale, ative e gerencie MCPs para seu Gateway Docker",curses.A_DIM)
        stats=[(" Instalados ",ni,curses.color_pair(3)),(" Ativos ",ne,curses.color_pair(1)),(" Catalogo ",ct,curses.color_pair(2))]
        bw=18; gap=2; sx=max(2,(self.w-(len(stats)*(bw+gap)-gap))//2)
        for i,(l,v,c) in enumerate(stats):
            x=sx+i*(bw+gap)
            for r in range(4):
                b="┌"+"─"*(bw-2)+"┐" if r==0 else "│"+" "*(bw-2)+"│" if r<3 else "└"+"─"*(bw-2)+"┘"
                self.stdscr.addstr(5+r,x,b,curses.A_DIM)
            self.stdscr.addstr(6,x+(bw-len(l))//2,l,curses.A_DIM)
            vs=str(v)
            self.stdscr.addstr(7,x+(bw-len(vs))//2,vs,curses.A_BOLD|c)
        self.stdscr.addstr(9,2,"─"*(self.w-6),curses.A_DIM)

    # ─── home tab ────────────────────────────────────────────────────

    def draw_home(self):
        self.draw_header()
        ry=11
        self.stdscr.addstr(ry,2,"─"*(self.w-6),curses.A_DIM)
        self.stdscr.addstr(ry+1,2,"Ultimas atividades",curses.A_BOLD)
        for i,l in enumerate(self.log_lines[:5]): self.stdscr.addstr(ry+2+i,4,l.strip()[:self.w-8],curses.A_DIM)
        if not self.log_lines: self.stdscr.addstr(ry+2,4,"(sem registros)",curses.A_DIM)
        ay=ry+8
        self.stdscr.addstr(ay,2,"─"*(self.w-6),curses.A_DIM)
        self.stdscr.addstr(ay+1,2,"Acoes rapidas",curses.A_BOLD)
        self.stdscr.addstr(ay+2,6," Reiniciar Gateway [R] ",curses.color_pair(4))
        self.stdscr.addstr(ay+2,32," Abrir script [O] ",curses.color_pair(4))

    # ─── mcps tab ────────────────────────────────────────────────────

    def draw_mcps(self):
        self.draw_header()
        # search + filter
        self.stdscr.addstr(10,2,"Buscar:",curses.A_DIM)
        self.stdscr.addstr(10,10,f" {self.search} ",curses.A_NORMAL)
        flt=[" All "," Active "," Inactive "]
        x=max(24,len(self.search)+14)
        self.stdscr.addstr(10,x,"|",curses.A_DIM)
        for i,f in enumerate(flt):
            self.stdscr.addstr(10,x+2,f,curses.color_pair(4) if i==self.filter else curses.A_DIM)
            x+=len(f)+1
        # header
        self.stdscr.addstr(11,2,"    Status     Servidor               Descricao",curses.A_BOLD|curses.A_UNDERLINE)
        self.stdscr.addstr(12,2,"─"*(self.w-6),curses.A_DIM)
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
            if act: self.stdscr.addstr(row,2,"[ ativo ]  ",curses.color_pair(1)|curses.A_BOLD)
            else: self.stdscr.addstr(row,2,"[inativo]  ",curses.A_DIM)
            self.stdscr.addstr(row,13,s["name"][:22].ljust(22),curses.A_BOLD if act else curses.A_NORMAL)
            self.stdscr.addstr(row,36,s["desc"][:self.w-50])
            if s["secrets"]: self.stdscr.addstr(row,self.w-5,"*",curses.color_pair(2)|curses.A_BOLD)
            if cur: self.stdscr.attroff(curses.color_pair(4))
        if self.scroll>0:
            self.stdscr.addstr(13,2,f"\u25b2 {self.scroll} mais",curses.A_DIM)
        if items and len(items)>self.scroll+mv:
            rm=len(items)-self.scroll-mv; rw=min(self.h-3,13+mv)
            self.stdscr.addstr(rw,2,f"{rm} \u25bc",curses.A_DIM)
        if not items: self.center(self.h//2+3,"(nenhum MCP instalado — va na aba Market)",curses.A_DIM)
        # detail
        if items and 0<=self.cursor<len(items):
            sel=items[self.cursor]; dy=self.h-3
            self.stdscr.addstr(dy,2,"─"*(self.w-6),curses.A_DIM)
            st="ATIVO" if sel["name"] in self.enabled else "INATIVO"
            sc=curses.color_pair(1) if sel["name"] in self.enabled else curses.color_pair(6)
            self.stdscr.addstr(dy+1,2,f" {sel['name']}: {sel['desc'][:self.w-70]}",curses.A_DIM)
            self.stdscr.addstr(dy+1,self.w-14,f"[{st}]",sc|curses.A_BOLD)

    # ─── market tab ──────────────────────────────────────────────────

    def draw_market(self):
        self.draw_header()
        self.stdscr.addstr(10,2,"Buscar:",curses.A_BOLD)
        self.stdscr.addstr(10,10,f" {self.market_search} ",curses.A_NORMAL)
        self.stdscr.addstr(11,2,"    Status     Servidor               Descricao",curses.A_BOLD|curses.A_UNDERLINE)
        self.stdscr.addstr(12,2,"─"*(self.w-6),curses.A_DIM)
        items=self.catalog_items
        if self.market_search: items=[s for s in items if self.market_search.lower() in s["name"].lower()]
        mv=max(3,self.h-16); self.market_cursor=max(0,min(self.market_cursor,len(items)-1)) if items else 0
        self.market_scroll=max(0,min(self.market_cursor-mv+1,len(items)-mv))
        vis=items[self.market_scroll:self.market_scroll+mv]
        for idx,s in enumerate(vis):
            row=idx+13; i=self.market_scroll+idx; inst=s["name"] in self.installed; cur=i==self.market_cursor
            if cur: self.stdscr.attron(curses.color_pair(4))
            self.stdscr.addstr(row,2,"[instalado]" if inst else "[disponivel]",curses.color_pair(1)|curses.A_DIM if inst else curses.A_DIM)
            self.stdscr.addstr(row,14,s["name"][:22].ljust(22),curses.A_BOLD if inst else curses.A_NORMAL)
            self.stdscr.addstr(row,37,s["desc"][:self.w-50])
            if s["secrets"]: self.stdscr.addstr(row,self.w-5,"*",curses.color_pair(2)|curses.A_BOLD)
            if cur: self.stdscr.attroff(curses.color_pair(4))
        if self.market_scroll>0:
            self.stdscr.addstr(13,2,f"\u25b2 {self.market_scroll} mais",curses.A_DIM)
        if vis and len(items)>self.market_scroll+mv:
            rm=len(items)-self.market_scroll-mv; rw=min(self.h-3,13+mv)
            self.stdscr.addstr(rw,2,f"{rm} \u25bc",curses.A_DIM)
        if not vis: self.center(self.h//2+3,"(catalogo vazio — verifique conexao Docker)",curses.A_DIM)
        if vis and 0<=self.market_cursor<len(items):
            sel=items[self.market_cursor]; dy=self.h-3
            self.stdscr.addstr(dy,2,"─"*(self.w-6),curses.A_DIM)
            st="instalado" if sel["name"] in self.installed else "disponivel"
            self.stdscr.addstr(dy+1,2,f" {sel['name']}: {sel['desc'][:self.w-74]}  [{st}]",curses.A_DIM)

    # ─── main loop ───────────────────────────────────────────────────

    def run(self):
        while True:
            self.h,self.w=self.stdscr.getmaxyx(); self.stdscr.clear()
            self.tab_bar(); self.stdscr.addstr(1,0,"─"*(self.w-1),curses.A_DIM)
            if self.tab==0: self.draw_home()
            elif self.tab==1: self.draw_mcps()
            else: self.draw_market()
            if self.dialog: self.draw_dialog()
            if self.msg and time.time()<self.msg_tick: self.center(self.h-2,self.msg,curses.color_pair(1)|curses.A_BOLD)
            self.status_bar(self._status_msg())
            self.stdscr.refresh()
            if not self.handle_input(): break
        sys.stderr.write("\033[?1007l\033[?1002l"); sys.stderr.flush()

    def _status_msg(self):
        if self.tab==0: return f"Home — {len(self.enabled)} ativos · {len(self.installed)} instalados · {len(self.catalog_items)} catalogo"
        if self.tab==1:
            a=sum(1 for s in self.catalog_items if s["name"] in self.enabled and s["name"] in self.installed)
            i=sum(1 for s in self.catalog_items if s["name"] not in self.enabled and s["name"] in self.installed)
            return f"MCPs — {a} ativos · {i} inativos  | [Espaco] toggle  [1-3] filtro  [Esc] busca  [r] remover"
        return f"Market — {len(self.catalog_items)} servidores  | [Enter] instalar/remover  [Esc] busca"

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
                d=self.dialog; by=d["y"]+d["h"]-2; bx=d["x"]+d["w"]//2-10
                if my==by:
                    if bx<=mx<=bx+8:
                        cb=d["cb_yes"]; self.dialog=None; cb and cb()
                    elif bx+9<=mx<=bx+17:
                        cb=d["cb_no"]; self.dialog=None; cb and cb()
                return True
            if my==0:
                if 2<=mx<8: self.tab=0
                elif 10<=mx<16: self.tab=1
                elif 18<=mx<26: self.tab=2
                return True
            if self.tab==1 and my==10:
                ft=[(" All ",24),(" Active ",30),(" Inactive ",39)]
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
                            self.show_dialog("Remover",f"Remover '{n}' do gateway?",lambda n=n:self._uninstall(n),self.close_dialog)
                        else:
                            self.show_dialog("Instalar",f"Instalar '{n}' no gateway?",lambda n=n:self._install(n),self.close_dialog)
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
        elif key==ord('q'): return False
        elif self.tab==0:
            if key in (ord('r'),ord('R')): self.show_dialog("Reiniciar","Reiniciar o gateway agora?",self._do_restart,self.close_dialog)
            elif key in (ord('o'),ord('O')): os.system(f"$EDITOR ~/Documentos/MCPs/start-gateway.sh &")
        elif self.tab==1:
            items=self._filtered_mcps()
            if key==curses.KEY_UP and self.cursor>0: self.cursor-=1
            elif key==curses.KEY_DOWN and self.cursor<len(items)-1: self.cursor+=1
            elif key==ord(' '):
                if items: self._confirm_toggle(items[self.cursor]["name"])
            elif key in (ord('r'),ord('R')):
                if items: self.show_dialog("Remover",f"Remover '{items[self.cursor]['name']}' permanentemente?",lambda n=items[self.cursor]["name"]:self._uninstall(n),self.close_dialog)
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
                        self.show_dialog("Remover",f"Remover '{n}' do gateway?",lambda n=n:self._uninstall(n),self.close_dialog)
                    else:
                        self.show_dialog("Instalar",f"Instalar '{n}' no gateway?",lambda n=n:self._install(n),self.close_dialog)
            elif key==27: self.market_search=""; self.market_cursor=0
            elif key in (127,curses.KEY_BACKSPACE): self.market_search=self.market_search[:-1]; self.market_cursor=0
            elif 32<=key<127: self.market_search+=chr(key); self.market_cursor=0
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
        self.show_dialog("Desativar" if act else "Ativar",f"{'Desativar' if act else 'Ativar'} '{n}'?",lambda x=n:self._toggle(x),self.close_dialog)

    def _toggle(self,n):
        a=toggle_active(n); self.refresh_data(); self.notify(f"{'Ativado' if a else 'Desativado'} {n}")

    def _install(self,n):
        install_server(n); self.refresh_data(); self.notify(f"Instalado {n}")

    def _uninstall(self,n):
        uninstall_server(n); self.refresh_data(); self.notify(f"Removido {n}")

    def _do_restart(self):
        self.notify("Reiniciando gateway...",10)
        if restart_gw(): self.notify("Gateway reiniciado!")
        else: self.notify("Erro ao reiniciar gateway",3)

def main():
    try: curses.wrapper(lambda s: App(s).run())
    except KeyboardInterrupt: pass

if __name__=="__main__":
    main()
