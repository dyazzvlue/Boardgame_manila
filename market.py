"""market.py — 黑市股价与股票牌管理"""
from __future__ import annotations
import random
from constants import CFG, Goods
from player import Player


class Market:
    def __init__(self) -> None:
        self.prices: dict[Goods, int] = {g: 0 for g in Goods}
        self.bank_stocks: dict[Goods, int] = {g: 0 for g in Goods}

    def setup(self, players: list[Player]) -> None:
        stocks_cfg = CFG["stocks"]
        draw_count = stocks_cfg["initial_draw_per_good"]
        deal_count = stocks_cfg["deal_per_player"]
        draw_pool: list[Goods] = []
        for g in Goods:
            draw_pool.extend([g] * draw_count)
        random.shuffle(draw_pool)
        idx = 0
        for _ in range(deal_count):
            for player in players:
                player.add_stock(draw_pool[idx])
                idx += 1
        for card in draw_pool[idx:]:
            self.bank_stocks[card] += 1
        per_total = stocks_cfg["per_good_total"]
        for g in Goods:
            self.bank_stocks[g] += per_total - draw_count

    def buy_price(self, good: Goods) -> int:
        return max(self.prices[good], CFG["game"]["min_stock_price"])

    def can_buy(self, good: Goods) -> bool:
        return self.bank_stocks[good] > 0

    def buy_stock(self, good: Goods, player: Player) -> int:
        if not self.can_buy(good):
            raise ValueError(f"银行已无 {CFG['goods'][good.value]['name']} 股票")
        price = self.buy_price(good)
        player.pay(price)
        self.bank_stocks[good] -= 1
        player.add_stock(good)
        return price

    def raise_price(self, good: Goods) -> int:
        step = CFG["game"]["price_step"]
        self.prices[good] = min(self.prices[good] + step, CFG["game"]["end_price"])
        return self.prices[good]

    def is_game_over(self) -> bool:
        end = CFG["game"]["end_price"]
        return any(p >= end for p in self.prices.values())

    def get_price(self, good: Goods) -> int:
        return self.prices[good]

    def __repr__(self) -> str:
        parts = [f"{CFG['goods'][g.value]['name']}={self.prices[g]}" for g in Goods]
        return f"Market({', '.join(parts)})"
