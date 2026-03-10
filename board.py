"""board.py — 港口/造船厂/保险等板块槽位管理"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from constants import CFG, PositionType
from player import Player


@dataclass
class BoardSlot:
    label: str
    cost: int
    profit: int = 0
    move: int = 0
    worker: Optional[Player] = field(default=None)

    @property
    def is_empty(self) -> bool:
        return self.worker is None

    def clear(self) -> Optional[Player]:
        p = self.worker
        self.worker = None
        return p


class Board:
    def __init__(self) -> None:
        port_cfg = CFG["port"]["slots"]
        shipyard_cfg = CFG["shipyard"]["slots"]
        pirate_cfg = CFG["pirate"]["slots"]
        nav_cfg = CFG["navigator"]["slots"]
        ins_cfg = CFG["insurance"]

        self.port_slots: list[BoardSlot] = [
            BoardSlot(label=s["label"], cost=s["cost"], profit=s["profit"])
            for s in port_cfg
        ]
        self.shipyard_slots: list[BoardSlot] = [
            BoardSlot(label=s["label"], cost=s["cost"], profit=s["profit"])
            for s in shipyard_cfg
        ]
        self.pirate_slots: list[BoardSlot] = [
            BoardSlot(label=s["label"], cost=s["cost"])
            for s in pirate_cfg
        ]
        self.navigator_slots: list[BoardSlot] = [
            BoardSlot(label=s["label"], cost=s["cost"], move=s["move"])
            for s in nav_cfg
        ]
        self.insurance_slot: Optional[Player] = None

    # ── 部署 ──────────────────────────────────────────────────────────────
    def deploy_port(self, slot_idx: int, player: Player) -> int:
        slot = self.port_slots[slot_idx]
        if not slot.is_empty:
            raise ValueError(f"港口槽位 {slot_idx} 已被占用")
        player.pay(slot.cost)
        player.use_worker()
        slot.worker = player
        return slot.cost

    def deploy_shipyard(self, slot_idx: int, player: Player) -> int:
        slot = self.shipyard_slots[slot_idx]
        if not slot.is_empty:
            raise ValueError(f"造船厂槽位 {slot_idx} 已被占用")
        player.pay(slot.cost)
        player.use_worker()
        slot.worker = player
        return slot.cost

    def deploy_pirate(self, slot_idx: int, player: Player) -> int:
        slot = self.pirate_slots[slot_idx]
        if not slot.is_empty:
            raise ValueError(f"海盗槽位 {slot_idx} 已被占用")
        player.pay(slot.cost)
        player.use_worker()
        slot.worker = player
        return slot.cost

    def deploy_navigator(self, slot_idx: int, player: Player) -> int:
        slot = self.navigator_slots[slot_idx]
        if not slot.is_empty:
            raise ValueError(f"航海家槽位 {slot_idx} 已被占用")
        player.pay(slot.cost)
        player.use_worker()
        slot.worker = player
        return slot.cost

    def deploy_insurance(self, player: Player) -> int:
        """保险费用为0，立即获得+10比索。"""
        if self.insurance_slot is not None:
            raise ValueError("保险槽位已被占用")
        player.use_worker()
        self.insurance_slot = player
        gain = CFG["insurance"]["immediate_gain"]
        player.collect(gain)
        return gain

    # ── 结算 ──────────────────────────────────────────────────────────────
    def resolve_port(self, docked_goods_labels: set[str]) -> dict[Player, int]:
        """根据靠港货船的标签(A/B/C)向对应槽位工人发放利润。"""
        payouts: dict[Player, int] = {}
        for slot in self.port_slots:
            if slot.worker is not None and slot.label in docked_goods_labels:
                slot.worker.collect(slot.profit)
                payouts[slot.worker] = payouts.get(slot.worker, 0) + slot.profit
        return payouts

    def resolve_shipyard(self, docked_goods_labels: set[str]) -> dict[Player, int]:
        payouts: dict[Player, int] = {}
        for slot in self.shipyard_slots:
            if slot.worker is not None and slot.label in docked_goods_labels:
                slot.worker.collect(slot.profit)
                payouts[slot.worker] = payouts.get(slot.worker, 0) + slot.profit
        return payouts

    def resolve_shipyard_with_insurance(self, docked_goods_labels: set[str],
                                          insurance_holder: Player) -> dict[Player, int]:
        """
        有保险时的修船厂结算：
        修船厂槽位工人的利润由保险方（insurance_holder）赔付，而非银行。
        赔付金额受保险方余额上限限制（不能强制负资产）。
        返回 {工人: 实际到手金额}。
        """
        payouts: dict[Player, int] = {}
        for slot in self.shipyard_slots:
            if slot.worker is not None and slot.label in docked_goods_labels:
                actual = min(slot.profit, insurance_holder.money)
                if actual > 0:
                    insurance_holder.pay(actual)
                    slot.worker.collect(actual)
                payouts[slot.worker] = payouts.get(slot.worker, 0) + actual
        return payouts

    # ── 重置 ──────────────────────────────────────────────────────────────
    def reset(self) -> None:
        for slot in self.port_slots + self.shipyard_slots + self.pirate_slots + self.navigator_slots:
            p = slot.clear()
            if p is not None:
                p.workers_available += 1
        if self.insurance_slot is not None:
            self.insurance_slot.workers_available += 1
            self.insurance_slot = None

    # ── 查询 ──────────────────────────────────────────────────────────────
    def has_navigator(self, slot_idx: int) -> bool:
        return not self.navigator_slots[slot_idx].is_empty

    def navigator_move(self, slot_idx: int) -> int:
        return self.navigator_slots[slot_idx].move

    def navigator_player(self, slot_idx: int) -> Optional[Player]:
        return self.navigator_slots[slot_idx].worker

    def has_pirate(self, slot_idx: int) -> bool:
        return not self.pirate_slots[slot_idx].is_empty

    def pirate_player(self, slot_idx: int) -> Optional[Player]:
        return self.pirate_slots[slot_idx].worker
