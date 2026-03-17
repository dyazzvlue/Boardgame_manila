"""
Manila/online/state.py
将 game_context（Market/Ship/Board/Player 等对象）序列化为 JSON dict。
供 ManilaGame.get_state() 调用，以及 WebSocket STATE 消息广播。
"""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..market import Market
    from ..ship import Ship
    from ..board import Board
    from ..player import Player
    from ..constants import Goods


def _player_to_dict(p: "Player") -> dict:
    return {
        "name": p.name,
        "is_human": p.is_human,
        "money": p.money,
        "stocks": {g.value: p.stocks[g] for g in p.stocks},
        "pledged_stocks": [g.value for g in p.pledged_stocks],
        "workers_available": p.workers_available,
        "workers_total": p.workers_total,
        "can_deploy": p.can_deploy,
        "is_harbor_master": p.is_harbor_master,
    }


def _market_to_dict(m: "Market") -> dict:
    return {
        "prices":      {g.value: v for g, v in m.prices.items()},
        "bank_stocks": {g.value: v for g, v in m.bank_stocks.items()},
    }


def _ship_to_dict(ship: "Ship") -> dict:
    return {
        "good": ship.good.value,
        "position": ship.position,
        "docked_at": ship.docked_at.name if ship.docked_at else None,
        "hijacked": ship.hijacked,
        "slots": [
            {
                "cost": s.cost,
                "worker": s.worker.name if s.worker else None,
            }
            for s in ship.slots
        ],
    }


def _board_to_dict(board: "Board") -> dict:
    def _slot(s):
        d = {"label": s.label, "cost": s.cost}
        if hasattr(s, "profit") and s.profit:
            d["profit"] = s.profit
        if hasattr(s, "move") and s.move:
            d["move"] = s.move
        d["worker"] = s.worker.name if s.worker else None
        return d

    return {
        "port":      [_slot(s) for s in board.port_slots],
        "shipyard":  [_slot(s) for s in board.shipyard_slots],
        "pirate":    [_slot(s) for s in board.pirate_slots],
        "navigator": [_slot(s) for s in board.navigator_slots],
        "insurance": board.insurance_slot.name if board.insurance_slot else None,
    }


def serialize_context(ctx: dict) -> dict:
    """
    将 bridge.game_context 序列化为 JSON dict。
    ctx 来自 bridge.game_context（含 market/ships/board/players 等）。
    """
    market  = ctx.get("market")
    ships   = ctx.get("ships") or {}
    board   = ctx.get("board")
    players = ctx.get("players") or []
    active  = ctx.get("active_goods") or []

    return {
        "phase":        ctx.get("phase", ""),
        "round_num":    ctx.get("round_num", 0),
        "sub_round":    ctx.get("sub_round"),
        "market":       _market_to_dict(market) if market else None,
        "ships":        {g.value: _ship_to_dict(s) for g, s in ships.items()},
        "board":        _board_to_dict(board) if board else None,
        "players":      [_player_to_dict(p) for p in players],
        "active_goods": [g.value for g in active],
    }
