"""ship.py — 货船与船位槽管理"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from constants import CFG, Goods, PositionType
from player import Player


@dataclass
class ShipSlot:
    cost: int
    worker: Optional[Player] = field(default=None)

    @property
    def is_empty(self) -> bool:
        return self.worker is None

    def clear(self) -> Optional[Player]:
        p = self.worker
        self.worker = None
        return p


class Ship:
    def __init__(self, good: Goods) -> None:
        self.good = good
        cfg_slots = CFG["goods"][good.value]["slots"]
        self.slots: list[ShipSlot] = [ShipSlot(cost=s["cost"]) for s in cfg_slots]
        self.position: int = 0
        self.docked_at: Optional[PositionType] = None
        self.hijacked: bool = False

    @property
    def slot_count(self) -> int:
        return len(self.slots)

    @property
    def worker_count(self) -> int:
        return sum(1 for s in self.slots if not s.is_empty)

    def add_worker(self, slot_idx: int, player: Player) -> int:
        if slot_idx < 0 or slot_idx >= self.slot_count:
            raise ValueError(f"槽位索引 {slot_idx} 无效")
        slot = self.slots[slot_idx]
        if not slot.is_empty:
            raise ValueError(f"槽位 {slot_idx} 已有工人")
        cost = slot.cost
        player.pay(cost)
        player.use_worker()
        slot.worker = player
        return cost

    def evict_all_workers(self) -> list[Player]:
        evicted: list[Player] = []
        for slot in self.slots:
            p = slot.clear()
            if p is not None:
                p.workers_available += 1
                evicted.append(p)
        return evicted

    def move(self, steps: int) -> None:
        track_len = CFG["game"]["ship_track_length"]
        self.position = min(self.position + steps, track_len)

    def dock_to_port(self) -> None:
        self.docked_at = PositionType.PORT

    def dock_to_shipyard(self) -> None:
        self.docked_at = PositionType.SHIPYARD

    def distribute_cargo_profit(self, market_price: int) -> dict[Player, int]:
        wc = self.worker_count
        if wc == 0:
            return {}
        per_worker = market_price // wc
        payouts: dict[Player, int] = {}
        for slot in self.slots:
            if slot.worker is not None:
                p = slot.worker
                payouts[p] = payouts.get(p, 0) + per_worker
        for p, amount in payouts.items():
            p.collect(amount)
        return payouts

    def reset(self) -> None:
        for slot in self.slots:
            p = slot.clear()
            if p is not None:
                p.workers_available += 1
        self.position = 0
        self.docked_at = None
        self.hijacked = False

    def __repr__(self) -> str:
        name = CFG["goods"][self.good.value]["name"]
        return f"Ship({name}, pos={self.position}, docked={self.docked_at})"
