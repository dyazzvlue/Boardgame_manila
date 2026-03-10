"""ai.py — AI 玩家决策逻辑"""
from __future__ import annotations
import random
from typing import Optional
from constants import CFG, Goods
from player import Player
from market import Market


class AIPlayer(Player):
    def __init__(self, name: str, player_count: int) -> None:
        super().__init__(name, player_count, is_human=False)

    def _holding_score(self, good: Goods, market: Market) -> float:
        """持股量 × 当前股价，用于决策权重。"""
        return self.stocks.get(good, 0) * market.buy_price(good)

    def decide_bid(self, current_bid: int, market: Market, active_goods: list) -> int:
        """返回出价或 0（放弃）。AI 最多竞价到自己净资产的 40%。"""
        cap = max(1, self.money // 3)
        min_bid = max(1, current_bid + 1)
        if min_bid > cap or min_bid > self.money:
            return 0
        # 随机决定是否继续
        if random.random() < 0.35:
            return 0
        return min_bid

    def decide_buy_stock(self, market: Market) -> Optional[Goods]:
        """AI贪心选择持仓评分最高且银行有货的股票，金钱足够时购买。"""
        candidates = [g for g in Goods if market.can_buy(g) and market.buy_price(g) <= self.money]
        if not candidates or random.random() < 0.3:
            return None
        return max(candidates, key=lambda g: self._holding_score(g, market))

    def decide_choose_goods(self, all_goods: list, market: Market) -> list:
        """排除持仓评分最低的货物。"""
        if len(all_goods) <= 1:
            return all_goods
        worst = min(all_goods, key=lambda g: self._holding_score(g, market))
        return [g for g in all_goods if g != worst]

    def decide_ship_placement(self, chosen_goods: list) -> dict:
        """
        将自己持仓最多的货船放在最优位置。
        返回 {Goods: position}，总和须为 ship_start_sum。
        """
        target = CFG["game"]["ship_start_sum"]
        n = len(chosen_goods)
        # 基础分配：均分，多余给最高持仓
        base = target // n
        remainder = target - base * n
        sorted_goods = sorted(chosen_goods,
                               key=lambda g: self.stocks.get(g, 0), reverse=True)
        positions = {g: base for g in chosen_goods}
        for g in sorted_goods[:remainder]:
            positions[g] += 1
        # 确保每个位置 >= 0
        positions = {g: max(0, v) for g, v in positions.items()}
        # 修正总和
        diff = target - sum(positions.values())
        if diff != 0:
            positions[sorted_goods[0]] += diff
        return positions

    def decide_deploy(self, ships: dict, board, market: Market, active_goods: list,
                      player_list: list) -> Optional[tuple]:
        """
        AI 贪心选择期望净收益最大的部署位置。
        返回 ('port'|'shipyard'|'navigator'|'pirate'|'insurance'|'ship', idx1, idx2|None)
        或 None（跳过）
        """
        if self.workers_available == 0:
            return None

        best_score = -999
        best_action = None

        # 评估货船槽位（货物利润）
        for gi, g in enumerate(active_goods):
            ship = ships[g]
            price = market.prices[g]
            cargo_val = CFG["goods"][g.value]["cargo_value"]
            for si, slot in enumerate(ship.slots):
                if slot.is_empty and slot.cost <= self.money:
                    # 期望利润 = 货物价值/期望工人数 - 费用
                    expected_workers = max(1, ship.worker_count + 1)
                    expected_profit = price // expected_workers - slot.cost
                    # 自己有股票加权
                    stock_bonus = self.stocks.get(g, 0) * 2
                    score = expected_profit + stock_bonus
                    if score > best_score:
                        best_score = score
                        best_action = ("ship", gi, si)

        # 评估港口（固定利润）
        for i, s in enumerate(board.port_slots):
            if s.is_empty and s.cost <= self.money:
                score = s.profit - s.cost
                if score > best_score:
                    best_score = score
                    best_action = ("port", i, None)

        # 评估造船厂
        for i, s in enumerate(board.shipyard_slots):
            if s.is_empty and s.cost <= self.money:
                score = s.profit - s.cost
                if score > best_score:
                    best_score = score
                    best_action = ("shipyard", i, None)

        # 保险（立即收入，略保守）
        if board.insurance_slot is None and self.money >= 0:
            score = 4  # 期望净收益约为 4（平均）
            if score > best_score:
                best_score = score
                best_action = ("insurance", 0, None)

        if best_action is None or best_score < -5:
            return None
        return best_action

    def decide_navigator(self, active_goods: list, move_steps: int,
                          market: Market, ships: dict) -> list:
        """返回 [(Goods, delta), ...] 移动列表，每步向前+1。"""
        track_len = CFG["game"]["ship_track_length"]
        candidates = [g for g in active_goods if not ships[g].hijacked]
        if not candidates:
            return []
        moves = []
        temp_pos = {g: ships[g].position for g in active_goods}
        for _ in range(move_steps):
            # 选择可前进（未在终点）的船中距终点最近的
            fwd = [g for g in candidates if temp_pos[g] < track_len]
            if not fwd:
                break
            target = max(fwd, key=lambda g: (
                self.stocks.get(g, 0), temp_pos[g]))
            moves.append((target, +1))
            temp_pos[target] += 1
        return moves

    def decide_pirate_board(self, active_goods: list, market: Market,
                             ships: dict) -> Optional[Goods]:
        """登上持仓最少（且有工人）的货船以获取劫持机会；随机放弃。"""
        if random.random() < 0.4:
            return None
        candidates = [g for g in active_goods if ships[g].worker_count > 0]
        if not candidates:
            return None
        return min(candidates, key=lambda g: self.stocks.get(g, 0))

    def decide_pirate_destination(self, target_good: Goods, current_pos: int,
                                   track_len: int, market: Market) -> int:
        """若自己持有该货物的股票，送往港口；否则送往造船厂。"""
        if self.stocks.get(target_good, 0) > 0:
            return track_len  # 港口
        return 0  # 造船厂
