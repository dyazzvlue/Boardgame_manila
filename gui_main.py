"""gui_main.py — Manila pygame 入口"""
from __future__ import annotations
import sys, os, threading
sys.path.insert(0, os.path.dirname(__file__))
import gui.bridge as bridge
sys.modules["ui"] = bridge          # 替换 ui 模块
import pygame
from game import Game
from player import Player
from ai import AIPlayer
from constants import CFG

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

class SetupScene:
    NAMES=["玩家1","玩家2","玩家3","玩家4","玩家5"]
    def __init__(self,screen):
        self.screen=screen; self.n=3; self.ok=False
        self.inputs=[TextInput((320+i//2*280,160+i%2*54,240,40),self.NAMES[i]) for i in range(5)]
        self.ai_flags=[False]*5
        self._rebuild()
    def _rebuild(self):
        self.btns=[]
        for i,c in enumerate([3,4,5]):
            self.btns.append(Btn((80+i*90,140,80,40),f"{c}人",("n",c),ACTIVE if self.n==c else NORMAL))
        for i in range(self.n):
            row=i%2; col=i//2; x=325+col*280; y=212+row*54
            a=self.ai_flags[i]
            self.btns.append(Btn((x,y,100,30),"AI" if a else "玩家",("ai",i),DIM if a else (50,120,200)))
        self.btns.append(Btn((W//2-80,H-100,160,50),"开始游戏",("start",),ACTIVE))
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
            t=_ft(28,True).render("Manila — 马尼拉桌游设置",True,GOLD)
            self.screen.blit(t,t.get_rect(centerx=W//2,top=60))
            self.screen.blit(_ft(14).render("玩家数量:",True,TEXT),(80,150))
            for i in range(self.n):
                self.inputs[i].draw(self.screen)
                col=i//2; row=i%2
                lx=230+col*280; ly=162+row*54
                nt=_ft(14).render(f"玩家{i+1}名字:",True,DIM)
                self.screen.blit(nt,(lx,ly+12))
            for b in self.btns: b.draw(self.screen,mx,my)
            pygame.display.flip(); clock.tick(60)

class GameScene:
    def __init__(self,screen,players):
        self.screen=screen; self.players=players
        from gui.renderer import GameRenderer
        self.renderer=GameRenderer()
        self.g_thread=None; self.done=False; self.clock=pygame.time.Clock()
    def run(self):
        def _run_game():
            game=Game(self.players)
            game.run()
        self.g_thread=threading.Thread(target=_run_game,daemon=True)
        self.g_thread.start()
        current_req=None
        while True:
            mx,my=pygame.mouse.get_pos()
            for ev in pygame.event.get():
                if ev.type==pygame.QUIT: pygame.quit(); sys.exit()
                if ev.type==pygame.MOUSEBUTTONDOWN:
                    ans=self.renderer.handle_click(ev.pos,current_req)
                    if ans is not None:
                        bridge.respond(ans)
                        current_req=None
                if ev.type==pygame.MOUSEWHEEL:
                    self.renderer.scroll_log(-ev.y)
            req=bridge.get_pending_request()
            if req: current_req=req
            ctx=bridge.game_context
            log=bridge.game_log
            rt=current_req.get("type","") if current_req else ""
            if rt=="game_over":
                self.renderer.draw(self.screen,ctx,log,current_req,(mx,my))
                pygame.display.flip(); self.clock.tick(30)
                if current_req:
                    ans=self.renderer.handle_click((0,0),None)
                # Show game over overlay
                self._game_over_overlay(ctx)
                return
            self.renderer.draw(self.screen,ctx,log,current_req,(mx,my))
            pygame.display.flip(); self.clock.tick(30)
            if not self.g_thread.is_alive() and current_req is None:
                self._game_over_overlay(ctx); return
    def _game_over_overlay(self,ctx):
        ov=pygame.Surface((W,H),pygame.SRCALPHA); ov.fill((0,0,0,180))
        self.screen.blit(ov,(0,0))
        t=_ft(30,True).render("游戏结束",True,GOLD)
        self.screen.blit(t,t.get_rect(centerx=W//2,top=260))
        players=ctx.get("players",[])
        market=ctx.get("market")
        if players and market:
            ranked=sorted(players,key=lambda p:p.net_worth(market.prices),reverse=True)
            y=320
            for i,p in enumerate(ranked):
                nw=p.net_worth(market.prices)
                c=(218,175,55) if i==0 else (220,220,230)
                s=_ft(18).render(f"{'🥇 ' if i==0 else f'{i+1}. '}{p.name}: ¥{nw}",True,c)
                self.screen.blit(s,s.get_rect(centerx=W//2,top=y)); y+=36
        ct=_ft(14).render("点击任意处退出",True,DIM)
        self.screen.blit(ct,ct.get_rect(centerx=W//2,top=H-80))
        pygame.display.flip()
        while True:
            for ev in pygame.event.get():
                if ev.type==pygame.QUIT or ev.type==pygame.MOUSEBUTTONDOWN or ev.type==pygame.KEYDOWN:
                    return

def main():
    pygame.init(); pygame.display.set_caption("Manila")
    screen=pygame.display.set_mode((W,H))
    players=SetupScene(screen).run()
    GameScene(screen,players).run()
    pygame.quit()

if __name__=="__main__":
    main()
