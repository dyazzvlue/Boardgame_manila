"""
Manila/online/adapter.py
将 Manila 的 Game / bridge 包装为 framework 的 AbstractGame。

依赖安装:
    pip install -e /path/to/gameplatform
或: PYTHONPATH=/path/to/gameplatform python3 ...
"""
from __future__ import annotations
import sys, os, threading, random
from typing import Any

try:
    from framework.core import AbstractGame, AbstractBridge
except ImportError as _e:
    raise ImportError(
        "联机模式需要 gameplatform 框架。\n"
        "请运行: pip install -e /path/to/gameplatform\n"
        f"原始错误: {_e}"
    )

# ── 确保 Manila 包自身可被 import ──────────────────────────────────────────
_MANILA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _MANILA_DIR not in sys.path:
    sys.path.insert(0, _MANILA_DIR)

# ── 在 game.py 被 import 之前，把 ui 模块替换为 shim ─────────────────────
# game.py 顶层做 import ui，Python 会查 sys.modules['ui']。
# 若此时 shim 已注入，则 game 模块拿到的是 shim 代理，而非真实 gui/ui.py。
from online import _ui_shim as _shim_module   # noqa: E402
if sys.modules.get("ui") is not _shim_module:
    sys.modules["ui"] = _shim_module

from constants import Goods
from player import Player
from ai import AIPlayer
from game import Game             # 此时 game.py 里的 import ui 已命中 shim
from .state import serialize_context


class _ManilaNetBridgeShim:
    """
    替换 gui/bridge.py，让 game.py 的 ask_*() 调用转发给 AbstractBridge.ask()。
    同时拦截 print 输出为 bridge.log()。
    """

    def __init__(self, abstract_bridge: AbstractBridge, players: list[Player]):
        self._b = abstract_bridge
        self._players = players

    def _player_idx(self, player_name: str) -> int:
        for i, p in enumerate(self._players):
            if p.name == player_name:
                return i
        return 0

    # ── show_* 函数：广播 state ──────────────────────────────────────────
    def _update(self):
        self._b.broadcast_state()

    def show_market(self, *a, **kw):       self._update()
    def show_ships(self, *a, **kw):        self._update()
    def show_board(self, *a, **kw):        self._update()
    def show_players(self, *a, **kw):      self._update()
    def show_full_state(self, *a, **kw):   self._update()
    def show_round_start(self, *a, **kw):  self._update()
    def show_profit_report(self, *a, **kw): self._update()

    def header(self, text):   self._b.log(f"▌ {text}", "header"); self._update()
    def section(self, text):  self._b.log(f"► {text}", "section"); self._update()
    def divider(self, *a, **kw): pass
    def pause(self, *a, **kw): pass

    def good_str(self, g): return g.value if g else ""
    def _good_name(self, g): return g.value if g else ""
    def player_str(self, p, *a): return p.name if p else "?"

    # 兼容 t() 国际化调用
    def t(self, key, **kw): return key

    # ── ask_* → AbstractBridge.ask() ────────────────────────────────────

    def ask_bid(self, player_name, current_bid, min_bid, **kw) -> int:
        idx = self._player_idx(player_name)
        val = self._b.ask(idx, "bid", {"current_bid": current_bid, "min_bid": min_bid})
        return val if isinstance(val, int) else 0

    def ask_buy_stock(self, player_name, market, player_money, **kw):
        from .state import _market_to_dict
        idx = self._player_idx(player_name)
        val = self._b.ask(idx, "buy_stock", {
            "market": _market_to_dict(market),
            "player_money": player_money,
        })
        if val is None:
            return None
        try:
            return Goods(val)
        except ValueError:
            return None

    def ask_choose_goods(self, player_name, goods_list, **kw) -> list:
        """
        前端返回被排除货物的单个字符串；game.py 需要 *留下的* 货物列表。
        """
        idx = self._player_idx(player_name)
        val = self._b.ask(idx, "choose_goods", {
            "goods": [g.value for g in goods_list],
        })
        if isinstance(val, str):
            try:
                excluded = Goods(val)
                return [g for g in goods_list if g != excluded]
            except ValueError:
                pass
        return goods_list

    def ask_ship_placement(self, player_name, active_goods, count, **kw) -> dict:
        idx = self._player_idx(player_name)
        val = self._b.ask(idx, "ship_placement", {
            "active_goods": [g.value for g in active_goods],
            "count": count,
        })
        if isinstance(val, dict):
            try:
                return {Goods(k): v for k, v in val.items()}
            except (ValueError, KeyError):
                pass
        # 默认随机放置
        import random as _r
        positions = list(range(1, count + 1))
        _r.shuffle(positions)
        return {g: p for g, p in zip(active_goods, positions)}

    def ask_deploy_position(self, player_name, ships, board,
                            active_goods, workers_available, **kw):
        """
        game.py 调用签名:
            ui.ask_deploy_position(player.name, self.ships, self.board,
                                   self.active_goods, player.workers_available)
        返回值：game.py 期望 (pos_type, idx1, idx2) tuple 或 None。
        """
        from .state import _ship_to_dict, _board_to_dict
        idx = self._player_idx(player_name)
        val = self._b.ask(idx, "deploy", {
            "ships": {g.value: _ship_to_dict(s) for g, s in ships.items()},
            "board": _board_to_dict(board),
            "active_goods": [g.value for g in active_goods],
            "workers_available": workers_available,
        })
        if val is None:
            return None
        try:
            t = val.get("type", "")
            if t == "ship":
                good_val = val.get("good", "")
                slot = int(val.get("slot", 0))
                idx1 = next(i for i, g in enumerate(active_goods) if g.value == good_val)
                return ("ship", idx1, slot)
            elif t in ("port", "shipyard", "navigator", "pirate"):
                return (t, int(val.get("slot", 0)), 0)
            elif t == "insurance":
                return ("insurance", 0, 0)
        except (TypeError, ValueError, StopIteration):
            pass
        return None

    def ask_navigator_moves(self, player_name, still_sailing, move_steps, ships, **kw):
        """
        game.py 调用签名:
            ui.ask_navigator_moves(nav_player.name, still_sailing, move_steps, self.ships)
        前端返回: [{good: str, step: int}, ...]
        game.py 期望: list of (Goods, int) tuples
        """
        idx = self._player_idx(player_name)
        val = self._b.ask(idx, "navigator_moves", {
            "undocked_goods": [g.value for g in still_sailing],
            "move_steps": move_steps,
        })
        if isinstance(val, list):
            result = []
            for m in val:
                try:
                    result.append((Goods(m["good"]), int(m["step"])))
                except (KeyError, ValueError, TypeError):
                    pass
            if result:
                return result
        return []

    def ask_insurance(self, player_name, **kw) -> bool:
        idx = self._player_idx(player_name)
        val = self._b.ask(idx, "insurance", {})
        return bool(val)

    def ask_harbor_action(self, player_name, ship, **kw) -> str:
        from .state import _ship_to_dict
        idx = self._player_idx(player_name)
        val = self._b.ask(idx, "harbor_action", {
            "ship": _ship_to_dict(ship),
        })
        return val if isinstance(val, str) else "pass"

    def ask_pirate_board(self, pirate_name, boardable_goods, ships, **kw):
        """
        game.py 调用签名:
            ui.ask_pirate_board(captain.name, boardable_list, ships_dict)
        boardable_goods: list[Goods] —— 可登船的货物列表
        """
        idx = self._player_idx(pirate_name)
        val = self._b.ask(idx, "pirate_board", {
            "active_goods": [g.value for g in boardable_goods],
        })
        if val is None:
            return None
        try:
            return Goods(val)
        except ValueError:
            return None

    def ask_pirate_kick_slot(self, pirate_name, target_good, ship) -> int:
        from .state import _ship_to_dict
        idx = self._player_idx(pirate_name)
        val = self._b.ask(idx, "pirate_kick", {
            "target_good": target_good.value,
            "ship": _ship_to_dict(ship),
        })
        return val if isinstance(val, int) else 0

    def ask_pirate_destination(self, pirate_name, target_good, current_pos, track_len) -> int:
        idx = self._player_idx(pirate_name)
        val = self._b.ask(idx, "pirate_dest", {
            "target_good": target_good.value,
            "current_pos": current_pos,
            "track_len": track_len,
        })
        return val if isinstance(val, int) else 0

    # ── misc ─────────────────────────────────────────────────────────────

    def ask_int(self, prompt, lo, hi): return lo
    def ask_choice(self, prompt, options): return 0
    def ask_yes_no(self, prompt): return False

    def show_final_scores(self, players, market):
        self._b.broadcast_game_over({
            "ranking": [
                {"name": p.name, "worth": p.net_worth(market.prices)}
                for p in sorted(players, key=lambda x: x.net_worth(market.prices), reverse=True)
            ]
        })
        self._update()


class ManilaGame(AbstractGame):
    GAME_ID      = "manila"
    GAME_NAME    = "马尼拉"
    MIN_PLAYERS  = 3
    MAX_PLAYERS  = 5
    COVER_IMAGE  = "manila_cover.png"

    def __init__(self):
        self._game: Game = None
        self._players: list[Player] = []
        self._shim: _ManilaNetBridgeShim = None

    def setup(self, player_names: list, human_flags: list) -> None:
        self._players = [
            Player(name, len(player_names), is_human=is_human)
            if is_human
            else AIPlayer(name, len(player_names))
            for name, is_human in zip(player_names, human_flags)
        ]
        self._shim = _ManilaNetBridgeShim(self.bridge, self._players)
        # 更新 shim 代理指向当前对局的 _ManilaNetBridgeShim
        _shim_module._current_shim = self._shim
        self._game = Game(self._players)

    def run(self) -> None:
        seed = random.randint(0, 2**31 - 1)
        random.seed(seed)
        self._game.run()

    def get_state(self) -> dict:
        """直接从 self._game 读取状态，不依赖 gui.bridge.game_context。"""
        if self._game is None:
            return {}
        ctx = {
            "phase":        "",
            "round_num":    self._game.round_num,
            "sub_round":    self._game._sub_round,
            "market":       self._game.market,
            "ships":        self._game.ships,
            "board":        self._game.board,
            "players":      self._players,
            "active_goods": self._game.active_goods,
        }
        return serialize_context(ctx)

    def on_player_disconnected(self, player_idx: int) -> None:
        if 0 <= player_idx < len(self._players):
            p = self._players[player_idx]
            p.is_human = False
            self.bridge.log(f"{p.name} 断线，已切换为 AI 接管", "warn")
