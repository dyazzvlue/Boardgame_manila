"""gui_main.py — Manila pygame 入口"""
from __future__ import annotations
import sys, os, threading
sys.path.insert(0, os.path.dirname(__file__))
import gui.bridge as bridge
from gui.renderer import _NO_CLICK
sys.modules["ui"] = bridge          # 替换 ui 模块
import pygame
from game import Game
from player import Player
from ai import AIPlayer
from constants import CFG
import datetime as _dt

# ── 存档目录 & 文件对话框 ──────────────────────────────────────────────────────
def _saves_dir():
    d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "saves")
    os.makedirs(d, exist_ok=True)
    return d

def _file_open_dlg(title="打开存档"):
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk(); root.withdraw(); root.attributes("-topmost", True)
        p = filedialog.askopenfilename(
            title=title,
            filetypes=[("Manila存档", "*.json"), ("所有文件", "*.*")],
            initialdir=_saves_dir())
        root.destroy()
        return p or None
    except Exception:
        return None

def _file_save_dlg(title="保存存档"):
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk(); root.withdraw(); root.attributes("-topmost", True)
        default = "manila_" + _dt.datetime.now().strftime("%Y%m%d_%H%M%S") + ".json"
        p = filedialog.asksaveasfilename(
            title=title, defaultextension=".json",
            filetypes=[("Manila存档", "*.json")],
            initialfile=default, initialdir=_saves_dir())
        root.destroy()
        return p or None
    except Exception:
        return None

def _build_players_from_save(data):
    n = len(data["players"])
    ps = []
    for pd in data["players"]:
        if pd["is_human"]:
            ps.append(Player(pd["name"], n, is_human=True))
        else:
            ps.append(AIPlayer(pd["name"], n))
    return ps

W,H=1280,800
_fc={}
def _ft(sz,bold=False):
    k=(sz,bold)
    if k in _fc: return _fc[k]
    for n in ["notosanscjksc","wqyzenhei","simhei","microsoftyahei","unifont"]:
        p=pygame.font.match_font(n,bold=bold)
        if p: _fc[k]=pygame.font.Font(p,sz); return _fc[k]
    _fc[k]=pygame.font.Font(None,sz); return _fc[k]

BG=(18,25,45); PANEL=(24,35,60); BORDER=(50,80,130)
TEXT=(220,220,230); GOLD=(218,175,55); ACTIVE=(200,55,70)
HOVER=(50,90,150); NORMAL=(32,58,95); DIM=(100,110,130)

class Btn:
    def __init__(self,rect,text,val,col=None):
        self.r=pygame.Rect(rect); self.t=text; self.v=val; self.c=col or NORMAL
    def draw(self,screen,mx,my):
        c=HOVER if self.r.collidepoint(mx,my) else self.c
        pygame.draw.rect(screen,c,self.r,border_radius=8)
        pygame.draw.rect(screen,BORDER,self.r,1,border_radius=8)
        s=_ft(17).render(self.t,True,TEXT)
        screen.blit(s,s.get_rect(center=self.r.center))
    def hit(self,pos): return self.r.collidepoint(pos)

class TextInput:
    def __init__(self,rect,placeholder=""):
        self.r=pygame.Rect(rect); self.ph=placeholder; self.text=""; self.focus=False
    def draw(self,screen):
        col=HOVER if self.focus else PANEL
        pygame.draw.rect(screen,col,self.r,border_radius=6)
        pygame.draw.rect(screen,HOVER if self.focus else BORDER,self.r,2,border_radius=6)
        t=self.text if self.text else self.ph
        c=TEXT if self.text else DIM
        s=_ft(15).render(t,True,c)
        screen.blit(s,(self.r.x+8,self.r.y+(self.r.h-s.get_height())//2))
        if self.focus and len(self.text)<24 and pygame.time.get_ticks()%1000<500:
            cx=self.r.x+8+_ft(15).size(self.text)[0]+1
            pygame.draw.line(screen,TEXT,(cx,self.r.y+6),(cx,self.r.y+self.r.h-6),2)
    def event(self,ev):
        if ev.type==pygame.MOUSEBUTTONDOWN: self.focus=self.r.collidepoint(ev.pos)
        elif ev.type==pygame.KEYDOWN and self.focus:
            if ev.key==pygame.K_BACKSPACE: self.text=self.text[:-1]
            elif ev.unicode and len(self.text)<20: self.text+=ev.unicode

# ── 主菜单 ────────────────────────────────────────────────────────────────────
class MainMenuScene:
    def __init__(self, screen):
        self.screen = screen
        self.clock = pygame.time.Clock()
        cx = W // 2
        self.btns = [
            Btn((cx-120, 310, 240, 60), "开始游戏", "new", ACTIVE),
            Btn((cx-120, 390, 240, 60), "继续游戏", "load", NORMAL),
            Btn((cx-120, 470, 240, 60), "帮    助", "help", NORMAL),
            Btn((cx-120, 550, 240, 60), "退    出", "quit", (70, 25, 25)),
        ]
    def run(self):
        while True:
            mx, my = pygame.mouse.get_pos()
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT: pygame.quit(); sys.exit()
                if ev.type == pygame.MOUSEBUTTONDOWN:
                    for b in self.btns:
                        if b.hit(ev.pos):
                            if b.v == "new": return "new"
                            elif b.v == "load":
                                path = _file_open_dlg("选择存档文件")
                                if path: return ("load", path)
                            elif b.v == "help": pass
                            elif b.v == "quit": pygame.quit(); sys.exit()
            self.screen.fill(BG)
            t = _ft(52, True).render("Manila", True, GOLD)
            self.screen.blit(t, t.get_rect(centerx=W//2, top=130))
            sub = _ft(18).render("马尼拉桌游 · 数字版", True, DIM)
            self.screen.blit(sub, sub.get_rect(centerx=W//2, top=198))
            pygame.draw.line(self.screen, BORDER, (W//2-200, 268), (W//2+200, 268), 1)
            for b in self.btns: b.draw(self.screen, mx, my)
            ver = _ft(12).render("v0.1  ©2026", True, DIM)
            self.screen.blit(ver, ver.get_rect(right=W-20, bottom=H-10))
            pygame.display.flip()
            self.clock.tick(60)

# ── 日志查看器（全屏覆盖层）──────────────────────────────────────────────────
class LogViewer:
    _STYLE_COL = {
        "normal":  (200, 200, 210), "header": (218, 175, 55),
        "section": (100, 180, 240), "good":   (80,  200, 120),
        "dim":     (100, 110, 130), "bad":    (220, 80,  80),
    }
    def __init__(self):
        self.active = False; self.scroll = 0
    def event(self, ev):
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
            self.active = False; return
        if ev.type == pygame.MOUSEBUTTONDOWN:
            if pygame.Rect(W-110, 14, 96, 32).collidepoint(ev.pos):
                self.active = False
        if ev.type == pygame.MOUSEWHEEL:
            self.scroll = max(0, self.scroll - ev.y * 3)
    def draw(self, screen, game_log):
        ov = pygame.Surface((W, H)); ov.fill((10, 15, 30)); screen.blit(ov, (0, 0))
        t = _ft(22, True).render("游戏日志", True, GOLD)
        screen.blit(t, t.get_rect(centerx=W//2, top=14))
        close = pygame.Rect(W-110, 14, 96, 32)
        pygame.draw.rect(screen, (80, 30, 30), close, border_radius=6)
        cs = _ft(14).render("关闭 [ESC]", True, TEXT)
        screen.blit(cs, cs.get_rect(center=close.center))
        pygame.draw.line(screen, BORDER, (0, 52), (W, 52), 1)
        LINE_H = 21; visible = (H - 60) // LINE_H
        max_sc = max(0, len(game_log) - visible + 2)
        self.scroll = min(self.scroll, max_sc)
        screen.set_clip(pygame.Rect(0, 55, W, H - 55))
        for idx, (text, style) in enumerate(game_log):
            y = 58 + (idx - self.scroll) * LINE_H
            if y < 55: continue
            if y > H: break
            col = self._STYLE_COL.get(style, (200, 200, 210))
            screen.blit(_ft(13).render(text, True, col), (30, y))
        screen.set_clip(None)

class SetupScene:
    NAMES=["玩家1","玩家2","玩家3","玩家4","玩家5"]
    # 布局：3列×2行，每玩家槽宽386px
    _CX=[20, 406, 792]   # 各列 x 起点
    _RY=[265, 400]        # 两行 y 起点

    def __init__(self,screen):
        self.screen=screen; self.n=3; self.ok=False
        self.inputs=[TextInput(self._inp_rect(i),self.NAMES[i]) for i in range(5)]
        self.ai_flags=[False]*5
        self._rebuild()

    def _inp_rect(self,i):
        col=i//2; row=i%2
        return (self._CX[col]+108, self._RY[row], 198, 46)

    def _rebuild(self):
        self.btns=[]
        # 玩家人数选择按钮（居中）
        for i,c in enumerate([3,4,5]):
            self.btns.append(Btn((460+i*130,148,100,46),f"{c}人",("n",c),ACTIVE if self.n==c else NORMAL))
        # AI/真人切换按钮
        for i in range(self.n):
            col=i//2; row=i%2
            x=self._CX[col]+315; y=self._RY[row]+5
            a=self.ai_flags[i]
            self.btns.append(Btn((x,y,65,36),"AI" if a else "真人",("ai",i),DIM if a else (50,120,200)))
        # 开始按钮
        self.btns.append(Btn((W//2-95,H-110,190,54),"开始游戏",("start",),ACTIVE))

    def run(self):
        clock=pygame.time.Clock()
        while True:
            mx,my=pygame.mouse.get_pos()
            for ev in pygame.event.get():
                if ev.type==pygame.QUIT: pygame.quit(); sys.exit()
                for ti in self.inputs[:self.n]: ti.event(ev)
                if ev.type==pygame.MOUSEBUTTONDOWN:
                    for b in self.btns:
                        if b.hit(ev.pos):
                            k=b.v[0]
                            if k=="n": self.n=b.v[1]; self._rebuild()
                            elif k=="ai": i=b.v[1]; self.ai_flags[i]=not self.ai_flags[i]; self._rebuild()
                            elif k=="start":
                                ps=[]
                                for i in range(self.n):
                                    nm=self.inputs[i].text.strip() or self.NAMES[i]
                                    if self.ai_flags[i]:
                                        ps.append(AIPlayer(nm, self.n))
                                    else:
                                        ps.append(Player(nm, self.n, is_human=True))
                                return ps
            self.screen.fill(BG)
            # 标题
            t=_ft(34,True).render("Manila  —  马尼拉桌游",True,GOLD)
            self.screen.blit(t,t.get_rect(centerx=W//2,top=36))
            # 分隔线
            pygame.draw.line(self.screen,BORDER,(80,90),(W-80,90),1)
            # 玩家人数标签
            lbl=_ft(17).render("选择玩家人数：",True,TEXT)
            self.screen.blit(lbl,lbl.get_rect(centerx=W//2,top=116))
            # 分隔线2
            pygame.draw.line(self.screen,BORDER,(80,182),(W-80,182),1)
            hint=_ft(13).render("修改名字，选择真人 / AI",True,DIM)
            self.screen.blit(hint,hint.get_rect(centerx=W//2,top=192))
            # 玩家槽
            for i in range(self.n):
                col=i//2; row=i%2
                cx=self._CX[col]; ry=self._RY[row]
                # 槽背景
                slot_rect=pygame.Rect(cx,ry-8,386,62)
                pygame.draw.rect(self.screen,PANEL,slot_rect,border_radius=10)
                pygame.draw.rect(self.screen,BORDER,slot_rect,1,border_radius=10)
                # 标签
                nt=_ft(15).render(f"玩家 {i+1}：",True,TEXT)
                self.screen.blit(nt,(cx+10,ry+13))
                self.inputs[i].draw(self.screen)
            for b in self.btns: b.draw(self.screen,mx,my)
            pygame.display.flip(); clock.tick(60)

class GameScene:
    _META_DEF = [
        (W-252, 4, 76, 28, "保  存", "save", (35, 80, 45)),
        (W-168, 4, 76, 28, "加  载", "load", (35, 60, 100)),
        (W- 84, 4, 76, 28, "日  志", "log",  (60, 45, 95)),
    ]
    def __init__(self, screen, players):
        self.screen = screen; self.players = players
        from gui.renderer import GameRenderer
        self.renderer = GameRenderer()
        self.g_thread = None; self.clock = pygame.time.Clock()
        self.meta_btns = [Btn((x,y,w,h), t, v, c) for x,y,w,h,t,v,c in self._META_DEF]
        self.log_viewer = LogViewer()
        self._save_msg = ""; self._save_msg_t = 0
    def run(self):
        def _run_game():
            import random
            random.seed(bridge._game_seed)
            game = Game(self.players)
            game.run()
        self.g_thread = threading.Thread(target=_run_game, daemon=True)
        self.g_thread.start()
        current_req = None
        while True:
            mx, my = pygame.mouse.get_pos()
            if self.log_viewer.active:
                for ev in pygame.event.get():
                    if ev.type == pygame.QUIT: pygame.quit(); sys.exit()
                    self.log_viewer.event(ev)
                self.log_viewer.draw(self.screen, bridge.game_log)
                pygame.display.flip(); self.clock.tick(30)
                continue
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT: pygame.quit(); sys.exit()
                if ev.type == pygame.MOUSEBUTTONDOWN:
                    meta_hit = False
                    for mb in self.meta_btns:
                        if mb.hit(ev.pos):
                            meta_hit = True
                            if mb.v == "save":
                                path = _file_save_dlg()
                                if path:
                                    bridge.save_game(self.players, path)
                                    self._save_msg = "已保存: " + os.path.basename(path)
                                    self._save_msg_t = pygame.time.get_ticks()
                            elif mb.v == "load":
                                path = _file_open_dlg()
                                if path:
                                    bridge.reset_bridge()
                                    return ("load", path)
                            elif mb.v == "log":
                                self.log_viewer.active = True
                            break
                    if not meta_hit:
                        ans = self.renderer.handle_click(ev.pos, current_req)
                        if ans is not _NO_CLICK:
                            bridge.respond(ans); current_req = None
                if ev.type == pygame.MOUSEWHEEL:
                    self.renderer.scroll_log(-ev.y)
            req = bridge.get_pending_request()
            if req: current_req = req
            ctx = bridge.game_context; log = bridge.game_log
            rt = current_req.get("type", "") if current_req else ""
            if rt == "game_over":
                self.renderer.draw(self.screen, ctx, log, current_req, (mx, my))
                self._draw_meta(mx, my); pygame.display.flip(); self.clock.tick(30)
                self._game_over_overlay(ctx); return None
            self.renderer.draw(self.screen, ctx, log, current_req, (mx, my))
            self._draw_meta(mx, my); pygame.display.flip(); self.clock.tick(30)
            if not self.g_thread.is_alive() and current_req is None:
                self._game_over_overlay(ctx); return None
    def _draw_meta(self, mx, my):
        for mb in self.meta_btns: mb.draw(self.screen, mx, my)
        if self._save_msg and pygame.time.get_ticks() - self._save_msg_t < 3000:
            s = _ft(13).render(self._save_msg, True, (80, 220, 120))
            self.screen.blit(s, (W - 252, 36))
        else:
            self._save_msg = ""
    def _game_over_overlay(self, ctx):
        ov = pygame.Surface((W, H), pygame.SRCALPHA); ov.fill((0, 0, 0, 180))
        self.screen.blit(ov, (0, 0))
        t = _ft(30, True).render("游戏结束", True, GOLD)
        self.screen.blit(t, t.get_rect(centerx=W//2, top=260))
        players = ctx.get("players", []); market = ctx.get("market")
        if players and market:
            ranked = sorted(players, key=lambda p: p.net_worth(market.prices), reverse=True)
            y = 320
            for i, p in enumerate(ranked):
                nw = p.net_worth(market.prices)
                c = (218, 175, 55) if i == 0 else (220, 220, 230)
                s = _ft(18).render(f"{'#1 ' if i==0 else str(i+1)+'. '}{p.name}: ¥{nw}", True, c)
                self.screen.blit(s, s.get_rect(centerx=W//2, top=y)); y += 36
        ct = _ft(14).render("点击任意处退出", True, DIM)
        self.screen.blit(ct, ct.get_rect(centerx=W//2, top=H-80))
        pygame.display.flip()
        while True:
            for ev in pygame.event.get():
                if ev.type in (pygame.QUIT, pygame.MOUSEBUTTONDOWN, pygame.KEYDOWN):
                    return
def main():
    pygame.init()
    pygame.display.set_caption("Manila")
    screen = pygame.display.set_mode((W, H))

    def _run_from_save(path):
        try:
            data = bridge.load_game(path)
            players = _build_players_from_save(data)
            bridge.reset_bridge()
            bridge.start_replay(data["responses"], data.get("seed", 0))
            return GameScene(screen, players).run()
        except Exception as e:
            print(f"加载存档失败: {e}")
            return None

    pending_load = None
    while True:
        if pending_load:
            result = _run_from_save(pending_load)
            pending_load = None
        else:
            result = MainMenuScene(screen).run()
        if result == "new":
            players = SetupScene(screen).run()
            if players:
                bridge.reset_bridge()
                bridge.set_game_seed()  # 记录新游戏种子
                result = GameScene(screen, players).run()
                if isinstance(result, tuple) and result[0] == "load":
                    pending_load = result[1]
        elif isinstance(result, tuple) and result[0] == "load":
            pending_load = result[1]
    pygame.quit()

if __name__=="__main__":
    main()
