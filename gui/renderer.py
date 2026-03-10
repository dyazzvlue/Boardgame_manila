"""gui/renderer.py — pygame board renderer"""
from __future__ import annotations
_NO_CLICK = object()  # 哨兵：区分"未点击"与"点击了值为None的按钮"
import pygame
from typing import Optional, Any, List, Tuple
from constants import CFG, Goods

# Colors
BG=(18,25,45); PANEL_BG=(24,35,60); PANEL_DARK=(14,20,38)
BORDER=(50,80,130); TEXT=(220,220,230); TEXT_DIM=(130,140,160)
TEXT_BRIGHT=(255,255,255); ACCENT=(220,65,85); GOLD=(218,175,55)
GREEN_OK=(55,185,95); RED_WARN=(210,60,60)
BTN_NORMAL=(32,58,95); BTN_HOVER=(50,90,150); BTN_ACTIVE=(200,55,70)
BTN_DISABLED=(30,40,55); BTN_TEXT=(220,230,245); BTN_SEL=(55,145,70)
TRACK_BG=(22,33,58); TRACK_SLOT=(35,55,90); TRACK_END=(65,120,65)
GOODS_COLORS={Goods.nutmeg:(165,95,35),Goods.silk:(70,125,215),
              Goods.ginseng:(215,185,35),Goods.jade:(50,168,95)}
PLAYER_COLORS_LIST=[(220,80,80),(80,125,220),(75,200,105),(180,80,200),(80,200,200)]
LOG_STYLES={"normal":(200,200,210),"header":(218,175,55),"section":(100,185,230),
            "good":(80,200,110),"warn":(220,80,80),"dim":(100,110,130)}

_fc={}
def _font(sz,bold=False):
    k=(sz,bold)
    if k in _fc: return _fc[k]
    for n in ["notosanscjksc","wqyzenhei","simhei","microsoftyahei","unifont"]:
        p=pygame.font.match_font(n,bold=bold)
        if p:
            _fc[k]=pygame.font.Font(p,sz); return _fc[k]
    _fc[k]=pygame.font.Font(None,sz); return _fc[k]

class Button:
    def __init__(self,rect,text,value,color=None,disabled=False):
        self.rect=pygame.Rect(rect); self.text=text; self.value=value
        self.color=color or BTN_NORMAL; self.disabled=disabled
    def draw(self,screen,font,mouse):
        col=BTN_DISABLED if self.disabled else (BTN_HOVER if self.rect.collidepoint(mouse) else self.color)
        tc=TEXT_DIM if self.disabled else TEXT_BRIGHT
        pygame.draw.rect(screen,col,self.rect,border_radius=7)
        pygame.draw.rect(screen,BORDER,self.rect,1,border_radius=7)
        lines=self.text.split("\n")
        if len(lines)==1:
            s=font.render(self.text,True,tc); screen.blit(s,s.get_rect(center=self.rect.center))
        else:
            h=font.get_height()+2; y0=self.rect.centery-len(lines)*h//2
            for ln in lines:
                s=font.render(ln,True,tc); screen.blit(s,s.get_rect(centerx=self.rect.centerx,top=y0)); y0+=h
    def clicked(self,pos): return not self.disabled and self.rect.collidepoint(pos)

class GameRenderer:
    W=1280;H=800;HEADER_H=52;ACTION_Y=610;ACTION_H=190
    LEFT_W=830;RIGHT_X=830;SHIPS_H=272;BOARD_Y=324;BOARD_H=286
    MARKET_H=148;PLAYERS_Y=200;PLAYERS_H=250;LOG_Y=450;LOG_H=160

    def __init__(self):
        self._buttons=[]; self._dialog_state={}
        self._current_req_type=None; self._log_scroll=0

    def draw(self,screen,ctx,log,current_req,mouse):
        screen.fill(BG)
        self._draw_header(screen,ctx)
        self._draw_ships(screen,ctx)
        self._draw_board(screen,ctx)
        self._draw_market(screen,ctx)
        self._draw_players(screen,ctx)
        self._draw_log(screen,log)
        self._draw_action_panel(screen,ctx,current_req,mouse)

    def _draw_header(self,screen,ctx):
        pygame.draw.rect(screen,PANEL_DARK,(0,0,self.W,self.HEADER_H))
        pygame.draw.line(screen,BORDER,(0,self.HEADER_H-1),(self.W,self.HEADER_H-1),2)
        t=_font(22,True).render("Manila — 马尼拉桌游",True,GOLD)
        screen.blit(t,(16,13))
        ph=ctx.get("phase","")
        rn=ctx.get("round_num",0); sn=ctx.get("sub_round")
        rt=f"第{rn}大轮"+(f"·第{sn}轮" if sn else "") if rn else ""
        ps=_font(15).render(ph,True,TEXT); screen.blit(ps,(350,18))
        rs=_font(14).render(rt,True,TEXT_DIM); screen.blit(rs,(self.W-rs.get_width()-16,18))

    def _draw_ships(self,screen,ctx):
        x0=0; y0=self.HEADER_H; w=self.LEFT_W; h=self.SHIPS_H
        pygame.draw.rect(screen,PANEL_BG,(x0,y0,w,h))
        pygame.draw.line(screen,BORDER,(x0,y0+h-1),(x0+w,y0+h-1),1)
        screen.blit(_font(14,True).render("货船轨道",True,GOLD),(14,y0+8))
        ships=ctx.get("ships",{}); ag=ctx.get("active_goods",[])
        track=CFG["game"]["ship_track_length"]
        if not ag:
            screen.blit(_font(13).render("(等待港务长选择货物...)",True,TEXT_DIM),(14,y0+35))
            return
        row_h=(h-30)//len(ag); tx0=100; tx1=w-12; tw=tx1-tx0; cw=tw/(track+1)
        for ri,g in enumerate(ag):
            ry=y0+28+ri*row_h; ship=ships.get(g)
            if not ship: continue
            gn=CFG["goods"][g.value]["name"]; gc=GOODS_COLORS[g]
            pos=ship.position; docked=ship.docked_at
            screen.blit(_font(13,True).render(gn,True,gc),(8,ry+18))
            st="港口" if docked=="port" else ("造船厂" if docked=="shipyard" else
               ("被劫" if ship.hijacked else f"@{pos}"))
            screen.blit(_font(11).render(st,True,TEXT_DIM),(8,ry+36))
            pygame.draw.rect(screen,TRACK_BG,(tx0,ry+12,tw,28),border_radius=4)
            for ci in range(track+1):
                cx=tx0+int(ci*cw); cwr=max(1,int(cw)-2)
                cr=pygame.Rect(cx+1,ry+13,cwr,26)
                col=TRACK_END if ci==track else TRACK_SLOT
                pygame.draw.rect(screen,col,cr,border_radius=2)
                if ci%2==0 or ci==track:
                    ns=_font(10).render(str(ci),True,TEXT_DIM)
                    screen.blit(ns,ns.get_rect(centerx=cx+cwr//2,top=ry+42))
            if not docked:
                sx=tx0+int(pos*cw)+int(cw)//2; sy=ry+26
                pygame.draw.circle(screen,gc,(sx,sy),9)
                pygame.draw.circle(screen,TEXT_BRIGHT,(sx,sy),9,2)
                sl=_font(10,True).render(str(pos),True,TEXT_BRIGHT)
                screen.blit(sl,sl.get_rect(center=(sx,sy)))
            if ship.slots:
                dy=ry+row_h-10
                for si,slot in enumerate(ship.slots):
                    dx=tx0+6+si*22
                    if slot.worker:
                        pi=self._player_index(slot.worker,ctx)
                        pygame.draw.circle(screen,PLAYER_COLORS_LIST[pi%5],(dx,dy),7)
                        wl=_font(9).render(slot.worker.name[:2],True,TEXT_BRIGHT)
                        screen.blit(wl,wl.get_rect(center=(dx,dy)))
                    else:
                        pygame.draw.circle(screen,TRACK_SLOT,(dx,dy),7)
                        pygame.draw.circle(screen,BORDER,(dx,dy),7,1)

    def _draw_board(self,screen,ctx):
        x0=0; y0=self.BOARD_Y; w=self.LEFT_W; h=self.BOARD_H
        pygame.draw.rect(screen,PANEL_DARK,(x0,y0,w,h))
        pygame.draw.line(screen,BORDER,(x0,y0),(x0+w,y0),1)
        screen.blit(_font(14,True).render("棋盘位置",True,GOLD),(14,y0+8))
        board=ctx.get("board")
        if not board:
            screen.blit(_font(13).render("(等待初始化...)",True,TEXT_DIM),(14,y0+35))
            return
        secs=[("港口",getattr(board,"port_slots",[]),(50,160,80)),
              ("造船厂",getattr(board,"shipyard_slots",[]),(110,140,180)),
              ("航海家",getattr(board,"navigator_slots",[]),(80,160,200)),
              ("海盗",getattr(board,"pirate_slots",[]),(200,80,80))]
        sw=w//5
        for si,(stt,slots,col) in enumerate(secs):
            sx=x0+si*sw; sy=y0+28
            screen.blit(_font(12).render(stt,True,col),(sx+6,sy))
            pygame.draw.line(screen,BORDER,(sx+sw-1,y0+24),(sx+sw-1,y0+h-4),1)
            for sli,slot in enumerate(slots):
                sly=sy+20+sli*52
                occ=getattr(slot,"worker",None) is not None
                bg=(40,65,45) if occ else (28,40,65)
                sr=pygame.Rect(sx+6,sly,sw-14,48)
                pygame.draw.rect(screen,bg,sr,border_radius=5)
                pygame.draw.rect(screen,col if occ else BORDER,sr,1,border_radius=5)
                lb=getattr(slot,"label",f"槽{sli}")
                cost=getattr(slot,"cost",0); profit=getattr(slot,"profit",0)
                move=getattr(slot,"move",0)
                info=f"{lb} ¥{cost}"+( f"→¥{profit}" if profit else "")+( f" ±{move}" if move else "")
                screen.blit(_font(11).render(info,True,col),(sx+8,sly+4))
                w2=getattr(slot,"worker",None)
                if w2:
                    pi=self._player_index(w2,ctx)
                    screen.blit(_font(11).render(w2.name[:5],True,PLAYER_COLORS_LIST[pi%5]),(sx+8,sly+22))
                else:
                    screen.blit(_font(11).render("空",True,TEXT_DIM),(sx+8,sly+22))
        # Insurance (insurance_slot 直接存 Player 对象，None=空)
        ins_player=getattr(board,"insurance_slot",None)
        ix=x0+4*sw; iy=y0+28
        screen.blit(_font(12).render("保险",True,GOLD),(ix+6,iy))
        occ=ins_player is not None
        ir=pygame.Rect(ix+6,iy+20,sw-14,48)
        pygame.draw.rect(screen,(50,60,30) if occ else (28,40,65),ir,border_radius=5)
        pygame.draw.rect(screen,GOLD if occ else BORDER,ir,1,border_radius=5)
        gain=CFG.get("insurance",{}).get("immediate_gain",10)
        screen.blit(_font(11).render(f"免费+{gain}",True,GOLD),(ix+8,iy+24))
        if occ:
            pi=self._player_index(ins_player,ctx)
            screen.blit(_font(11).render(ins_player.name[:5],True,PLAYER_COLORS_LIST[pi%5]),(ix+8,iy+38))
        else:
            screen.blit(_font(11).render("空",True,TEXT_DIM),(ix+8,iy+38))

    def _draw_market(self,screen,ctx):
        x0=self.RIGHT_X; y0=self.HEADER_H; w=self.W-x0; h=self.MARKET_H
        pygame.draw.rect(screen,PANEL_BG,(x0,y0,w,h))
        pygame.draw.line(screen,BORDER,(x0,y0),(x0,y0+h),1)
        pygame.draw.line(screen,BORDER,(x0,y0+h-1),(x0+w,y0+h-1),1)
        screen.blit(_font(14,True).render("市场股价",True,GOLD),(x0+10,y0+8))
        market=ctx.get("market")
        if not market: return
        ep=CFG["game"].get("end_price",30); rh=(h-28)//4
        for ri,g in enumerate(Goods):
            ry=y0+26+ri*rh; gn=CFG["goods"][g.value]["name"]; gc=GOODS_COLORS[g]
            pr=market.prices[g]; bk=market.bank_stocks[g]
            screen.blit(_font(13,True).render(gn,True,gc),(x0+10,ry+4))
            bx=x0+68; bw=120; fi=int(bw*pr/ep)
            pygame.draw.rect(screen,TRACK_BG,(bx,ry+7,bw,12),border_radius=3)
            pygame.draw.rect(screen,gc,(bx,ry+7,fi,12),border_radius=3)
            ps=_font(13).render(f"¥{pr}",True,TEXT_BRIGHT); screen.blit(ps,(bx+bw+6,ry+5))
            bs=_font(12).render(f"余{bk}",True,TEXT_DIM); screen.blit(bs,(x0+w-bs.get_width()-6,ry+5))

    def _draw_players(self,screen,ctx):
        x0=self.RIGHT_X; y0=self.PLAYERS_Y; w=self.W-x0; h=self.PLAYERS_H
        pygame.draw.rect(screen,PANEL_DARK,(x0,y0,w,h))
        pygame.draw.line(screen,BORDER,(x0,y0),(x0,y0+h),1)
        pygame.draw.line(screen,BORDER,(x0,y0+h-1),(x0+w,y0+h-1),1)
        screen.blit(_font(14,True).render("玩家状态",True,GOLD),(x0+10,y0+8))
        players=ctx.get("players",[]); market=ctx.get("market")
        if not players: return
        rh=max(26,(h-28)//max(len(players),1))
        for pi,p in enumerate(players):
            ry=y0+26+pi*rh; pc=PLAYER_COLORS_LIST[pi%5]
            pygame.draw.rect(screen,PANEL_BG,(x0+4,ry,w-8,rh-2),border_radius=4)
            hm="[HM]" if p.is_harbor_master else ("[AI]" if not p.is_human else "   ")
            screen.blit(_font(12).render(hm,True,GOLD if p.is_harbor_master else TEXT_DIM),(x0+6,ry+4))
            screen.blit(_font(13,True).render(p.name,True,pc),(x0+42,ry+4))
            screen.blit(_font(13).render(f"¥{p.money}",True,GOLD),(x0+42+_font(13,True).size(p.name)[0]+6,ry+4))
            wa=getattr(p,"workers_available",0); wt=getattr(p,"workers_total",0)
            ws=_font(11).render(f"工{wa}/{wt}",True,TEXT_DIM); screen.blit(ws,(x0+w-ws.get_width()-6,ry+4))
            sx=x0+6
            for g in Goods:
                cnt=getattr(p,"stocks",{}).get(g,0)
                if cnt>0:
                    gs=_font(11).render(f"{CFG['goods'][g.value]['name']}x{cnt}",True,GOODS_COLORS[g])
                    if sx+gs.get_width()<x0+w-4: screen.blit(gs,(sx,ry+rh-16)); sx+=gs.get_width()+4
            if market:
                nw=p.net_worth(market.prices)
                ns=_font(11).render(f"净¥{nw}",True,GREEN_OK); screen.blit(ns,(x0+w-ns.get_width()-6,ry+rh-16))

    def _draw_log(self,screen,log):
        x0=self.RIGHT_X; y0=self.LOG_Y; w=self.W-x0; h=self.LOG_H
        pygame.draw.rect(screen,PANEL_BG,(x0,y0,w,h))
        pygame.draw.line(screen,BORDER,(x0,y0),(x0,y0+h),1)
        screen.blit(_font(13,True).render("事件日志",True,GOLD),(x0+10,y0+6))
        screen.set_clip(pygame.Rect(x0+2,y0+24,w-4,h-26))
        lh=_font(12).get_height()+2; vis=(h-26)//lh
        st=max(0,len(log)-vis-self._log_scroll); en=max(0,len(log)-self._log_scroll)
        for i,(txt,sty) in enumerate(log[st:en]):
            col=LOG_STYLES.get(sty,LOG_STYLES["normal"])
            ts=_font(12).render(txt[:52],True,col); screen.blit(ts,(x0+8,y0+25+i*lh))
        screen.set_clip(None)

    def _draw_action_panel(self,screen,ctx,req,mouse):
        pygame.draw.rect(screen,PANEL_DARK,(0,self.ACTION_Y,self.W,self.ACTION_H))
        pygame.draw.line(screen,ACCENT,(0,self.ACTION_Y),(self.W,self.ACTION_Y),2)
        if req is None:
            screen.blit(_font(14).render("AI 行动中... 请等待",True,TEXT_DIM),(14,self.ACTION_Y+75))
            self._buttons=[]
            self._current_req_type=None  # 重置，确保下次相同类型请求能重建按钮
            return
        rt=req.get("type","")
        if rt!=self._current_req_type:
            if self._current_req_type is not None:  # 真正换了请求类型才清空状态
                self._dialog_state={}
            self._current_req_type=rt
            self._rebuild_buttons(req,ctx,0,self.ACTION_Y)
        title=self._title(req); ts=_font(15,True).render(title,True,TEXT_BRIGHT); screen.blit(ts,(14,self.ACTION_Y+8))
        if rt=="bid":
            cv=self._dialog_state.get("value",req.get("min_bid",1))
            vs=_font(15,True).render(f"出价: ¥{cv}",True,GOLD)
            screen.blit(vs,vs.get_rect(centerx=self.W//2,top=self.ACTION_Y+8))
        elif rt=="ship_placement":
            pos=self._dialog_state.get("positions",{}); total=sum(pos.values()); tgt=CFG["game"]["ship_start_sum"]
            cs=_font(13).render(f"合计:{total}(需{tgt})",True,GREEN_OK if total==tgt else RED_WARN)
            screen.blit(cs,(self.W-cs.get_width()-14,self.ACTION_Y+30))
        elif rt=="navigator_moves":
            done=len(self._dialog_state.get("moves",[])); mx=req.get("move_steps",1)
            screen.blit(_font(13).render(f"已用步数:{done}/{mx}",True,TEXT_DIM),(self.W-160,self.ACTION_Y+8))
        for btn in self._buttons: btn.draw(screen,_font(13),mouse)

    def _title(self,req):
        rt=req.get("type",""); nm=req.get("player_name") or req.get("nav_name") or req.get("pirate_name") or ""
        d={"pause":"继续","game_over":"游戏结束","bid":f"{nm} — 竞标出价",
           "choose_goods":f"{nm} — 选择货物(排除一种)","buy_stock":f"{nm} — 是否购买股票",
           "ship_placement":f"{nm} — 设定起始位置(合计{CFG['game']['ship_start_sum']}格)",
           "deploy":f"{nm} — 派遣工人","navigator_moves":f"{nm} — 航海家操作",
           "pirate_board":f"{nm} — 海盗登船","pirate_kick":f"{nm} — 踢出哪个工人",
           "pirate_dest":f"{nm} — 选择目的地","int":req.get("prompt","输入数字"),
           "yes_no":req.get("prompt","请选择"),"choice":req.get("prompt","请选择")}
        return d.get(rt,f"请 {nm} 行动")

    def _rebuild_buttons(self,req,ctx,px,py):
        self._buttons=[]; rt=req.get("type","")
        bx=px+10; by=py+36; bw=self.W-20; bh=self.ACTION_H-42
        if rt in("pause","game_over"):
            v=True if rt=="pause" else "exit"
            t="继续" if rt=="pause" else "退出"
            self._buttons=[Button((bx+bw//2-110,by+bh//2-22,220,44),t,v,BTN_ACTIVE)]
        elif rt=="yes_no":
            self._buttons=[Button((bx+bw//2-130,by+bh//2-22,120,44),"是",True,BTN_SEL),
                           Button((bx+bw//2+10,by+bh//2-22,120,44),"否",False)]
        elif rt=="int":
            lo=req.get("lo",0); hi=req.get("hi",10); mid=(lo+hi)//2
            if "value" not in self._dialog_state:
                self._dialog_state["value"]=mid
            self._buttons=self._stepper(bx,by,bw,bh,lo,hi,self._dialog_state["value"])
        elif rt=="bid":
            mn=req.get("min_bid",1); mx=self._pmoney(req.get("player_name",""),ctx)
            if "value" not in self._dialog_state:
                self._dialog_state["value"]=mn
            self._dialog_state["max"]=mx  # 每次更新上限
            self._buttons=self._bid_btns(req,bx,by,bw,bh)
        elif rt=="choose_goods":
            goods=req.get("goods",[]); self._grid([(CFG["goods"][g.value]["name"]+"\n(排除此项)",g) for g in goods],bx,by,bw,bh,4,[GOODS_COLORS[g] for g in goods])
        elif rt=="buy_stock":
            market=req.get("market"); money=req.get("player_money",0)
            opts=[("不购买",None,BTN_NORMAL)]
            for g in Goods:
                if market and market.can_buy(g):
                    pr=market.buy_price(g); nm2=CFG["goods"][g.value]["name"]
                    opts.append((f"{nm2}\n¥{pr}",g,GOODS_COLORS[g]) if pr<=money else (f"{nm2}\n¥{pr}(不足)",g,BTN_DISABLED))
            self._grid([(t,v) for t,v,_ in opts],bx,by,bw,bh,5,[c for _,_,c in opts])
        elif rt=="ship_placement":
            goods=req.get("active_goods",[]); tgt=CFG["game"]["ship_start_sum"]
            if "positions" not in self._dialog_state:
                init=self._init_pos(goods); self._dialog_state={"positions":dict(init),"target":tgt}
            self._buttons=self._place_btns(goods,bx,by,bw,bh)
        elif rt=="deploy":
            self._deploy_btns(req,ctx,bx,by,bw,bh)
        elif rt=="navigator_moves":
            ud=req.get("undocked_goods",[]); ms=req.get("move_steps",1)
            ships=req.get("ships",{}); lp={g:ships[g].position for g in ud if g in ships}
            if "moves" not in self._dialog_state:
                self._dialog_state={"moves":[],"local_pos":lp,"max_steps":ms}
            self._nav_btns(req,bx,by,bw,bh)
        elif rt=="pirate_board":
            goods=req.get("active_goods",[]); self._grid([(CFG["goods"][g.value]["name"]+"\n(登此船)",g) for g in goods]+[("放弃",None)],bx,by,bw,bh,4,[GOODS_COLORS.get(g,BTN_NORMAL) for g in goods]+[BTN_NORMAL])
        elif rt=="pirate_kick":
            ship=req.get("ship"); occ=[(i,s) for i,s in enumerate(ship.slots) if s.worker]
            self._grid([(f"踢出槽{i}\n({s.worker.name})",i) for i,s in occ],bx,by,bw,bh,4,[BTN_ACTIVE]*len(occ))
        elif rt=="pirate_dest":
            tk=req.get("track_len",13)
            self._buttons=[Button((bx+20,by+bh//2-25,240,50),"港口\n(股价上涨)",tk,(50,140,80)),
                           Button((bx+280,by+bh//2-25,240,50),"造船厂\n(股价不涨)",0,(100,100,160))]
        elif rt=="choice":
            opts=req.get("options",[]); self._grid([(o,i) for i,o in enumerate(opts)],bx,by,bw,bh,3)

    def _grid(self,items,bx,by,bw,bh,cols=3,colors=None):
        if not items: return
        rws=(len(items)+cols-1)//cols; btw=(bw-10*cols)//cols; bth=min(56,(bh-8*rws)//rws)
        self._buttons=[]
        for i,(txt,val) in enumerate(items):
            c=i%cols; r=i//cols; x=bx+c*(btw+10); y=by+r*(bth+8)
            col=colors[i] if colors and i<len(colors) else None
            dis=(col is BTN_DISABLED)
            self._buttons.append(Button((x,y,btw,bth),txt,val,col,dis))

    def _bid_btns(self,req,bx,by,bw,bh):
        mn=req.get("min_bid",1); mx=self._dialog_state.get("max",999); cv=self._dialog_state.get("value",mn)
        sw=68; sy=by+bh//2-22; btns=[]
        for i,(d,lb) in enumerate([(-10,"-10"),(-5,"-5"),(-1,"-1")]):
            btns.append(Button((bx+i*(sw+6),sy,sw,44),lb,("bd",d),BTN_NORMAL,cv+d<mn))
        btns.append(Button((bx+240,sy,150,44),f"出价¥{cv}",("bc",cv),BTN_ACTIVE))
        for i,(d,lb) in enumerate([(1,"+1"),(5,"+5"),(10,"+10")]):
            btns.append(Button((bx+404+i*(sw+6),sy,sw,44),lb,("bd",d),BTN_NORMAL,cv+d>mx))
        btns.append(Button((bw-110,sy,100,44),"放弃",("bf",0)))
        return btns

    def _stepper(self,bx,by,bw,bh,lo,hi,cur):
        cx=bx+bw//2; cy=by+bh//2
        return [Button((cx-200,cy-22,60,44),"-5",("st",-5),BTN_NORMAL,cur-5<lo),
                Button((cx-130,cy-22,60,44),"-1",("st",-1),BTN_NORMAL,cur-1<lo),
                Button((cx-38,cy-22,76,44),str(cur),("ci",cur),BTN_ACTIVE),
                Button((cx+48,cy-22,60,44),"+1",("st",1),BTN_NORMAL,cur+1>hi),
                Button((cx+118,cy-22,60,44),"+5",("st",5),BTN_NORMAL,cur+5>hi)]

    def _place_btns(self,goods,bx,by,bw,bh):
        pos=self._dialog_state.get("positions",{}); tgt=self._dialog_state.get("target",9)
        total=sum(pos.values()); rh=min(52,(bh-46)//max(len(goods),1)); btns=[]
        for ri,g in enumerate(goods):
            gy=by+ri*rh; gn=CFG["goods"][g.value]["name"]; gc=GOODS_COLORS[g]; cv=pos.get(g,1)
            btns+=[Button((bx,gy,50,rh-4),"-1",("pd",g,-1),BTN_NORMAL,cv<=0),
                   Button((bx+56,gy,130,rh-4),f"{gn}:{cv}",None,gc,True),
                   Button((bx+194,gy,50,rh-4),"+1",("pd",g,1),BTN_NORMAL,cv>=5)]
        ok=total!=tgt
        btns.append(Button((bw-130,by+bh-50,120,44),f"确认({total})",("pc",dict(pos)),BTN_ACTIVE if not ok else BTN_DISABLED,ok))
        return btns

    def _deploy_btns(self,req,ctx,bx,by,bw,bh):
        ships=req.get("ships",{}); board=req.get("board"); ag=req.get("active_goods",[]); opts=[]
        if board:
            for i,s in enumerate(getattr(board,"port_slots",[])):
                if getattr(s,"is_empty",True) or s.worker is None: opts.append((f"港口{s.label}\n¥{s.cost}→¥{s.profit}",("port",i,None),(50,160,80)))
            for i,s in enumerate(getattr(board,"shipyard_slots",[])):
                if getattr(s,"is_empty",True) or s.worker is None: opts.append((f"造船厂{s.label}\n¥{s.cost}→¥{s.profit}",("shipyard",i,None),(110,140,190)))
            for i,s in enumerate(getattr(board,"navigator_slots",[])):
                if getattr(s,"is_empty",True) or s.worker is None:
                    lb="大" if i==0 else "小"
                    opts.append((f"{lb}航海家\n¥{s.cost}±{s.move}步",("navigator",i,None),(80,160,200)))
            for i,s in enumerate(getattr(board,"pirate_slots",[])):
                if getattr(s,"is_empty",True) or s.worker is None:
                    lb="船长" if i==0 else "水手"
                    opts.append((f"海盗·{lb}\n¥{s.cost}",("pirate",i,None),(200,80,80)))
            ins=getattr(board,"insurance_slot",None)
            if ins is None:  # insurance_slot 为 None 表示无人占用
                gain=CFG.get("insurance",{}).get("immediate_gain",10)
                opts.append((f"保险\n免费+¥{gain}",("insurance",0,None),(200,165,45)))
        for gi,g in enumerate(ag):
            ship=ships.get(g)
            if not ship or getattr(ship,"docked_at",None) is not None: continue
            emp=[(si,sl) for si,sl in enumerate(ship.slots) if getattr(sl,"is_empty",True) or sl.worker is None]
            if not emp: continue
            ci,cs=min(emp,key=lambda x:x[1].cost)
            opts.append((f"{CFG['goods'][g.value]['name']}槽{ci}\n¥{cs.cost}",("ship",gi,ci),GOODS_COLORS[g]))
        opts+=[("跳过部署",None,BTN_NORMAL),("回滚部署","rollback",(140,60,160))]
        self._grid([(t,v) for t,v,_ in opts],bx,by,bw,bh,4,[c for _,_,c in opts])

    def _nav_btns(self,req,bx,by,bw,bh):
        lp=self._dialog_state.get("local_pos",{}); moves=self._dialog_state.get("moves",[])
        ms=self._dialog_state.get("max_steps",1); ud=req.get("undocked_goods",[]); track=CFG["game"]["ship_track_length"]
        opts=[]
        for g in ud:
            pos=lp.get(g,0); gn=CFG["goods"][g.value]["name"]
            if pos<track: opts.append((f"{gn}+1\n({pos}→{pos+1})",("nm",g,1),GOODS_COLORS[g]))
            if pos>0:    opts.append((f"{gn}-1\n({pos}→{pos-1})",("nm",g,-1),GOODS_COLORS[g]))
        opts.append((f"结束({len(moves)}/{ms}步)",("nd",),BTN_NORMAL))
        self._grid([(t,v) for t,v,_ in opts],bx,by,bw,bh,4,[c for _,_,c in opts])

    def handle_click(self,pos,current_req):
        if not current_req: return _NO_CLICK
        for btn in self._buttons:
            if not btn.clicked(pos): continue
            val=btn.value; rt=current_req.get("type","")
            if isinstance(val,tuple):
                k=val[0]
                if k=="bd":   # bid delta
                    cv=self._dialog_state.get("value",current_req.get("min_bid",1))
                    mn=current_req.get("min_bid",1); mx=self._dialog_state.get("max",999)
                    self._dialog_state["value"]=max(mn,min(mx,cv+val[1])); self._current_req_type=None; return _NO_CLICK
                if k=="bc": return val[1]   # bid confirm
                if k=="bf": return 0        # bid fold
                if k=="st":  # stepper delta
                    lo=current_req.get("lo",0); hi=current_req.get("hi",10)
                    cv=self._dialog_state.get("value",(lo+hi)//2)
                    self._dialog_state["value"]=max(lo,min(hi,cv+val[1])); self._current_req_type=None; return _NO_CLICK
                if k=="ci": return self._dialog_state.get("value",val[1])
                if k=="pd":  # place delta
                    _,g,d=val; pd=self._dialog_state.get("positions",{})
                    pd[g]=max(0,min(5,pd.get(g,1)+d)); self._current_req_type=None; return _NO_CLICK
                if k=="pc": return val[1]   # place confirm
                if k=="nm":  # nav move
                    _,g,d=val; lp=self._dialog_state.get("local_pos",{})
                    lp[g]=lp.get(g,0)+d; self._dialog_state["moves"].append((g,d))
                    if len(self._dialog_state["moves"])>=self._dialog_state.get("max_steps",1):
                        return list(self._dialog_state["moves"])
                    self._current_req_type=None; return _NO_CLICK
                if k=="nd": return list(self._dialog_state.get("moves",[]))
            return val
        return _NO_CLICK

    def _player_index(self,player,ctx):
        for i,p in enumerate(ctx.get("players",[])):
            if p is player: return i
        return 0
    def _pmoney(self,name,ctx):
        for p in ctx.get("players",[]): 
            if p.name==name: return p.money
        return 999
    def _init_pos(self,goods):
        n=len(goods); tgt=CFG["game"]["ship_start_sum"]; base=[1]*n; rem=tgt-n
        for i in range(rem): base[i%n]+=1
        return {g:min(5,base[i]) for i,g in enumerate(goods)}
    def scroll_log(self,d): self._log_scroll=max(0,self._log_scroll+d)
