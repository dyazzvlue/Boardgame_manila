"""
ai.py — AI 玩家决策逻辑

策略核心：
  - 根据货船当前位置用 sigmoid 模型估算入港概率
  - 用 DP 精确计算"至少 k 艘船入港/入修"的概率，动态评估港口/修船厂价值
  - 综合持仓量与股价调整各决策的期望收益
"""

from __future__ import annotations
import math
import random
from typing import Optional
from constants import CFG, Goods
from player import Player
from market import Market


class AIPlayer(Player):
    """AI 玩家，自动做出所有决策。"""

    def __init__(self, name: str, player_count: int) -> None:
        super().__init__(name, player_count, is_human=False)

    # ── 内部辅助：概率估算 ────────────────────────────────────────────────────

    def _ship_arrival_prob(self, ship, track_len: int) -> float:
        """
        估算货船本轮能到达终点（进港/修船厂门口）的概率。
        使用 sigmoid，以轨道 70% 处为中点，陡度 0.8：
          pos=5  ~4%   pos=7  ~16%   pos=9  ~48%
          pos=11 ~82%  pos=13 ~96%
        已停靠或被劫持返回 0。
        """
        if ship.docked_at is not None:
            return 0.0
        if ship.hijacked:
            return 0.0
        pos = ship.position
        midpoint = track_len * 0.70
        return 1.0 / (1.0 + math.exp(-0.8 * (pos - midpoint)))

    def _p_at_least_k(self, probs: list, k: int) -> float:
        """
        给定各独立事件概率列表，用 DP 精确计算"至少 k 个事件发生"的概率。
        """
        n = len(probs)
        if k > n:
            return 0.0
        if k <= 0:
            return 1.0
        dp = [0.0] * (n + 1)
        dp[0] = 1.0
        for p in probs:
            new_dp = [0.0] * (n + 1)
            for j in range(n + 1):
                if dp[j] == 0.0:
                    continue
                new_dp[j] += dp[j] * (1.0 - p)
                if j + 1 <= n:
                    new_dp[j + 1] += dp[j] * p
            dp = new_dp
        return sum(dp[j] for j in range(k, n + 1))

    # ── 竞标港务长 ────────────────────────────────────────────────────────────

    def decide_bid(self, current_bid: int, market: Market,
                   active_goods: list) -> int:
        """
        估算 HM 价值 = 最高持仓货物（持仓量 × 价格）/ 4，上限为资金 30%。
        加入随机性避免行为完全可预测。
        """
        best_holding_val = max(
            (self.stocks.get(g, 0) * market.prices[g] for g in Goods),
            default=0
        )
        hm_value = max(3, best_holding_val // 4)
        max_willing = min(hm_value, int(self.money * 0.30))

        next_bid = current_bid + 1
        if next_bid > max_willing or next_bid > self.money:
            return 0
        if random.random() < 0.65:
            return next_bid
        return 0

    # ── HM 行动：买股票 ───────────────────────────────────────────────────────

    def decide_buy_stock(self, market: Market):
        """
        综合评分 = 持仓量 × 3 - 价格 × 0.5（持仓多优先，价低优先）。
        没有高评分时，兜底买最便宜的可买货物。
        """
        best_score: Optional[float] = None
        best_good = None
        for g in Goods:
            if not market.can_buy(g):
                continue
            price = market.buy_price(g)
            if price > self.money:
                continue
            score = self.stocks.get(g, 0) * 3.0 - price * 0.5
            if best_score is None or score > best_score:
                best_score = score
                best_good = g

        if best_good is not None and (best_score or 0) >= -2:
            return best_good
        # 兜底：资金充足时买最便宜的
        if self.money >= CFG["game"]["min_stock_price"] * 3:
            affordable = [g for g in Goods
                          if market.can_buy(g) and market.buy_price(g) <= self.money]
            if affordable:
                return min(affordable, key=lambda g: market.buy_price(g))
        return None

    # ── HM 行动：选择货物（排除一种） ─────────────────────────────────────────

    def decide_choose_goods(self, all_goods: list, market: Market) -> list:
        """
        排除"持仓量 × 2 + 股价"得分最低的货物。
        """
        def keep_score(g) -> float:
            return self.stocks.get(g, 0) * 2.0 + market.prices[g]

        worst = min(all_goods, key=keep_score)
        return [g for g in all_goods if g != worst]

    # ── HM 行动：设置货船起始位置 ─────────────────────────────────────────────

    def decide_ship_placement(self, chosen_goods: list) -> dict:
        """
        持仓最多的货物分配最高起始格（加速入港涨价收益）。
        总和等于 ship_start_sum。
        """
        total = CFG["game"]["ship_start_sum"]
        n = len(chosen_goods)
        base = total // n
        remainder = total - base * n
        cap = max(1, int(CFG["game"]["ship_track_length"] * 0.40))

        sorted_goods = sorted(chosen_goods,
                              key=lambda g: self.stocks.get(g, 0),
                              reverse=True)
        positions = {g: base for g in chosen_goods}
        for g in sorted_goods[:remainder]:
            positions[g] = min(positions[g] + 1, cap)

        # 修正边界误差，确保总和正确
        diff = total - sum(positions.values())
        if diff != 0:
            positions[sorted_goods[-1]] = max(1, positions[sorted_goods[-1]] + diff)

        return positions

    # ── 部署工人（核心改进） ──────────────────────────────────────────────────

    def decide_deploy(self, ships: dict, board,
                      market: Market, active_goods: list,
                      player_list: list = None):
        """
        派遣策略（基于船位置概率动态评估）：
          货船槽  ：arrival_prob × cargo_val/workers + holding × price_step × 0.6 - cost
          港口[i] ：P(至少 i+1 艘进港) × slot.profit - cost
          修船厂  ：P(至少 i+1 艘进修) × slot.profit - cost
          保险    ：immediate_gain - 已占修船厂槽的期望赔付
          海盗    ：只有船临近终点时才押注，best_cargo × 0.25 - cost
          领航员  ：推己方船前进的期望增益 - cost
        返回 (pos_type, idx1, idx2) 或 None。
        "ship": idx1 是 active_goods 中的位置索引，idx2 是货船槽索引。
        """
        if self.workers_available <= 0:
            return None

        track_len  = CFG["game"]["ship_track_length"]
        price_step = CFG["game"]["price_step"]

        # 计算各活跃货船入港概率
        arrival_probs = {
            g: self._ship_arrival_prob(ships[g], track_len)
            for g in active_goods
        }
        port_probs = [arrival_probs[g] for g in active_goods]
        yard_probs = [1.0 - p for p in port_probs]

        candidates = []  # (score, pos_type, idx1, idx2)

        # ── 货船槽 ───────────────────────────────────────────
        for gi, g in enumerate(active_goods):
            ship = ships[g]
            if ship.docked_at is not None:
                continue
            arr_p     = arrival_probs[g]
            cargo_val = CFG["goods"][g.value]["cargo_value"]
            holding   = self.stocks.get(g, 0)
            n_workers = ship.worker_count  # property

            for slot_idx, slot in enumerate(ship.slots):
                if not slot.is_empty:
                    continue
                cost = slot.cost
                if cost > self.money:
                    continue
                # 货物分成期望 + 持仓涨价期望
                expected_cargo = arr_p * cargo_val / (n_workers + 1)
                stock_gain     = arr_p * holding * price_step * 0.6
                score = expected_cargo + stock_gain - cost
                candidates.append((score, "ship", gi, slot_idx))

        # ── 港口 ─────────────────────────────────────────────
        for i, s in enumerate(board.port_slots):
            if not s.is_empty or s.cost > self.money:
                continue
            p_pay = self._p_at_least_k(port_probs, i + 1)
            score = p_pay * s.profit - s.cost
            candidates.append((score, "port", i, 0))

        # ── 修船厂 ───────────────────────────────────────────
        for i, s in enumerate(board.shipyard_slots):
            if not s.is_empty or s.cost > self.money:
                continue
            p_pay = self._p_at_least_k(yard_probs, i + 1)
            score = p_pay * s.profit - s.cost
            candidates.append((score, "shipyard", i, 0))

        # ── 保险 ─────────────────────────────────────────────
        if board.insurance_slot is None:
            ins = CFG["insurance"]
            # 即时收益 - 已占修船厂槽位的期望赔付
            expected_payout = sum(
                s.profit * self._p_at_least_k(yard_probs, i + 1)
                for i, s in enumerate(board.shipyard_slots)
                if not s.is_empty
            )
            score = ins["immediate_gain"] - expected_payout
            candidates.append((score, "insurance", 0, 0))

        # ── 海盗 ─────────────────────────────────────────────
        for i, s in enumerate(board.pirate_slots):
            if not s.is_empty or s.cost > self.money:
                continue
            best_plunder = max(
                (CFG["goods"][g.value]["cargo_value"]
                 for g in active_goods
                 if not ships[g].hijacked and ships[g].docked_at is None),
                default=0
            )
            has_target = any(arrival_probs[g] >= 0.25
                             for g in active_goods
                             if not ships[g].hijacked)
            score = (best_plunder * 0.25 - s.cost) if has_target else -10.0
            candidates.append((score, "pirate", i, 0))

        # ── 领航员 ───────────────────────────────────────────
        for i, s in enumerate(board.navigator_slots):
            if not s.is_empty or s.cost > self.money:
                continue
            move_steps = s.move  # BoardSlot.move 字段
            my_bonus = 0.0
            for g in active_goods:
                ship = ships[g]
                if ship.docked_at is not None:
                    continue
                if any(sl.worker is self for sl in ship.slots):
                    arr_p     = arrival_probs[g]
                    cargo_val = CFG["goods"][g.value]["cargo_value"]
                    n_workers = max(1, ship.worker_count)
                    delta_p   = 0.08 * move_steps
                    gain = delta_p * (cargo_val / n_workers
                                      + self.stocks.get(g, 0) * price_step * 0.6)
                    my_bonus = max(my_bonus, gain)
            score = my_bonus - s.cost
            candidates.append((score, "navigator", i, 0))

        if not candidates:
            return None

        best_score, pos_type, idx1, idx2 = max(candidates, key=lambda x: x[0])

        if best_score < -2.0:
            return None

        return (pos_type, idx1, idx2)

    # ── 领航员行动 ────────────────────────────────────────────────────────────

    def decide_navigator(self, still_sailing: list, move_steps: int,
                         market: Market, ships: dict) -> list:
        """
        优先前推"已投资且接近终点"的己方船；
        若无，后推"对手已投资且到达概率高"的船。
        still_sailing: 仍在航行的 Goods 列表。
        返回 list[(Goods, delta)]，delta: +1 前进，-1 后退。
        """
        track_len = CFG["game"]["ship_track_length"]
        moves = []

        def priority(g) -> float:
            ship = ships[g]
            has_mine = any(sl.worker is self for sl in ship.slots)
            pos = ship.position
            if has_mine:
                return pos / track_len * 10.0 + 5.0
            arr_p = self._ship_arrival_prob(ship, track_len)
            return -arr_p * 5.0

        ranked = sorted(still_sailing, key=priority, reverse=True)

        for g in ranked:
            if len(moves) >= move_steps:
                break
            ship = ships[g]
            has_mine = any(sl.worker is self for sl in ship.slots)
            if has_mine:
                delta = 1
            else:
                if self._ship_arrival_prob(ship, track_len) < 0.3:
                    continue
                delta = -1
            moves.append((g, delta))

        return moves

    # ── 海盗行动 ──────────────────────────────────────────────────────────────

    def decide_pirate_board(self, boardable: list, market: Market,
                            ships: dict):
        """选货物价值最高（cargo_value）的船登上；boardable 是 Goods 列表。"""
        if not boardable:
            return None
        return max(boardable,
                   key=lambda g: CFG["goods"][g.value]["cargo_value"])

    def decide_pirate_destination(self, g, position: int,
                                  track: int, market: Market) -> int:
        """
        返回船的目标位置（int）：
          >= track => 送进港口（自己持有该货物股票时受益）
          == 0     => 送修船厂（阻止对手赚港口收益）
        """
        if self.stocks.get(g, 0) > 0:
            return track  # 入港
        return 0           # 入修船厂

    # ── 贷款决策 ──────────────────────────────────────────────────────────────

    def decide_loan(self, needed_cost: int):
        """
        决定是否质押股票贷款。
        策略：质押持仓最少的货物（损失最小）。
        """
        if self.money >= needed_cost:
            return None
        for g in sorted(Goods, key=lambda g: self.stocks.get(g, 0)):
            if self.stocks.get(g, 0) > 0:
                return g
        return None
