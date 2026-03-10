"""
gui/bridge.py — 线程安全 UI 桥接层，替换 ui.py 供 GUI 模式使用。
"""

from __future__ import annotations
import queue
import threading
from typing import Any, Optional

from constants import CFG, Goods

# ANSI 常量（保留以兼容 game.py 的 print 语句）
RESET = "\033[0m"
BOLD  = "\033[1m"
DIM   = "\033[2m"
FG    = {"yellow": "\033[33m", "red": "\033[31m", "green": "\033[32m",
         "blue": "\033[34m", "purple": "\033[35m", "cyan": "\033[36m",
         "white": "\033[37m", "brown": "\033[33m"}

GOOD_COLOR    = {}
GOOD_ICON     = {}
PLAYER_COLORS = []

# 共享游戏状态
_lock = threading.Lock()

game_context: dict = {
    "market":       None,
    "ships":        {},
    "board":        None,
    "players":      [],
    "active_goods": [],
    "phase":        "等待开始...",
    "round_num":    0,
    "sub_round":    None,
}

game_log: list = []
_MAX_LOG = 400

_req_q: queue.Queue = queue.Queue()
_rsp_q: queue.Queue = queue.Queue()


def _ask(data: dict) -> Any:
    _req_q.put(data)
    return _rsp_q.get()


def respond(value: Any) -> None:
    _rsp_q.put(value)


def get_pending_request() -> Optional[dict]:
    try:
        return _req_q.get_nowait()
    except queue.Empty:
        return None


def _log(text: str, style: str = "normal") -> None:
    with _lock:
        game_log.append((text, style))
        if len(game_log) > _MAX_LOG:
            game_log.pop(0)


def _ctx(**kwargs) -> None:
    with _lock:
        game_context.update(kwargs)


def _good_name(g: Goods) -> str:
    return CFG["goods"][g.value]["name"]


def good_str(g) -> str:
    if g is None:
        return ""
    return _good_name(g)


def player_str(player, player_list=None) -> str:
    return player.name if player else "?"


def divider(char="─", width=60) -> None:
    _log("─" * 36, "dim")


def header(text: str) -> None:
    _log(f"▌ {text}", "header")
    _ctx(phase=text)


def section(text: str) -> None:
    _log(f"► {text}", "section")
    _ctx(phase=text)


def show_market(market, player_list=None) -> None:
    _ctx(market=market)


def show_ships(ships: dict, active_goods: list) -> None:
    _ctx(ships=ships, active_goods=active_goods)


def show_board(board) -> None:
    _ctx(board=board)


def show_players(players, market) -> None:
    _ctx(players=players, market=market)


def show_full_state(market, ships, board, players, active_goods) -> None:
    _ctx(market=market, ships=ships, board=board,
         players=players, active_goods=active_goods)


def show_round_start(round_num: int, sub_round=None) -> None:
    _ctx(round_num=round_num, sub_round=sub_round)
    if sub_round is None:
        _log(f"=== 第 {round_num} 大轮 ===", "header")
        _ctx(phase=f"第 {round_num} 大轮")
    else:
        _log(f"--- 第 {round_num} 大轮 · 第 {sub_round} 小轮", "section")
        _ctx(phase=f"第 {round_num} 大轮 · 第 {sub_round} 小轮")


def show_profit_report(report) -> None:
    for entry in report:
        _log(str(entry), "good")


def show_final_scores(players, market) -> None:
    _ctx(players=players, market=market)
    _log("=== 游戏结束！最终得分 ===", "header")
    ranking = sorted(players, key=lambda p: p.net_worth(market.prices), reverse=True)
    for i, p in enumerate(ranking):
        worth = p.net_worth(market.prices)
        _log(f"  #{i+1} {p.name}  净资产{worth}", "good" if i == 0 else "normal")
    _ask({"type": "game_over", "winner": ranking[0], "players": players, "market": market})


def pause(msg="按 Enter 继续...") -> None:
    _ask({"type": "pause", "msg": msg})


def ask_int(prompt: str, lo: int, hi: int) -> int:
    return _ask({"type": "int", "prompt": prompt, "lo": lo, "hi": hi})


def ask_choice(prompt: str, options: list) -> int:
    return _ask({"type": "choice", "prompt": prompt, "options": list(options)})


def ask_yes_no(prompt: str) -> bool:
    return _ask({"type": "yes_no", "prompt": prompt})


def ask_bid(player_name: str, current_bid: int, min_bid: int, state_fn=None) -> int:
    _log(f"  {player_name} 出价中...(当前最高 {current_bid})", "dim")
    return _ask({
        "type": "bid",
        "player_name": player_name,
        "current_bid": current_bid,
        "min_bid": min_bid,
    })


def ask_ship_placement(player_name: str, active_goods: list, n_ships: int) -> dict:
    return _ask({
        "type": "ship_placement",
        "player_name": player_name,
        "active_goods": list(active_goods),
        "n_ships": n_ships,
    })


def ask_choose_goods(player_name: str, all_goods: list) -> list:
    return _ask({
        "type": "choose_goods",
        "player_name": player_name,
        "goods": list(all_goods),
    })


def ask_buy_stock(player_name: str, market, player_money: int):
    return _ask({
        "type": "buy_stock",
        "player_name": player_name,
        "market": market,
        "player_money": player_money,
    })


def ask_deploy_position(player_name: str, ships: dict, board,
                        active_goods: list, workers_available: int,
                        state_fn=None):
    return _ask({
        "type": "deploy",
        "player_name": player_name,
        "ships": ships,
        "board": board,
        "active_goods": list(active_goods),
        "workers_available": workers_available,
    })


def ask_navigator_moves(nav_player_name: str, undocked_goods: list,
                        move_steps: int, ships: dict) -> list:
    return _ask({
        "type": "navigator_moves",
        "nav_name": nav_player_name,
        "undocked_goods": list(undocked_goods),
        "move_steps": move_steps,
        "ships": ships,
    })


def ask_pirate_board(pirate_player_name: str, active_goods: list, ships: dict):
    return _ask({
        "type": "pirate_board",
        "pirate_name": pirate_player_name,
        "active_goods": list(active_goods),
        "ships": ships,
    })


def ask_pirate_kick_slot(pirate_player_name: str, target_good, ship) -> int:
    return _ask({
        "type": "pirate_kick",
        "pirate_name": pirate_player_name,
        "target_good": target_good,
        "ship": ship,
    })


def ask_pirate_destination(pirate_player_name: str, target_good,
                            current_pos: int, track_len: int) -> int:
    return _ask({
        "type": "pirate_dest",
        "pirate_name": pirate_player_name,
        "target_good": target_good,
        "current_pos": current_pos,
        "track_len": track_len,
    })
