"""player.py — 玩家类"""
from __future__ import annotations
from constants import CFG, Goods


class Player:
    def __init__(self, name: str, player_count: int, is_human: bool = True) -> None:
        self.name = name
        self.is_human = is_human
        game_cfg = CFG["game"]
        self.money: int = game_cfg["initial_money"]
        workers_map: dict = game_cfg["workers_by_player_count"]
        self.workers_total: int = workers_map[str(player_count)]
        self.workers_available: int = self.workers_total
        self.stocks: dict[Goods, int] = {g: 0 for g in Goods}
        self.pledged_stocks: list[Goods] = []
        self.can_deploy: bool = True
        self.is_harbor_master: bool = False

    def pay(self, amount: int) -> None:
        if self.money < amount:
            raise ValueError(f"玩家 [{self.name}] 金钱不足：需要 {amount}，仅有 {self.money}")
        self.money -= amount

    def collect(self, amount: int) -> None:
        self.money += amount

    def add_stock(self, good: Goods) -> None:
        self.stocks[good] += 1

    def total_stocks(self) -> int:
        return sum(self.stocks.values()) + len(self.pledged_stocks)

    def free_stock_count(self) -> int:
        return sum(self.stocks.values())

    def can_loan(self) -> bool:
        return self.free_stock_count() > 0

    def loan(self, good: Goods) -> int:
        if self.stocks[good] <= 0:
            raise ValueError(f"玩家 [{self.name}] 没有 {good.value} 的股票可质押")
        self.stocks[good] -= 1
        self.pledged_stocks.append(good)
        amount = CFG["game"]["loan_amount"]
        self.collect(amount)
        return amount

    def can_redeem(self, good: Goods) -> bool:
        return good in self.pledged_stocks and self.money >= CFG["game"]["loan_redeem"]

    def redeem(self, good: Goods) -> int:
        if good not in self.pledged_stocks:
            raise ValueError(f"玩家 [{self.name}] 没有质押的 {good.value} 股票")
        cost = CFG["game"]["loan_redeem"]
        self.pay(cost)
        self.pledged_stocks.remove(good)
        self.stocks[good] += 1
        return cost

    def stowaway_eligible(self) -> bool:
        return self.money == 0 and not self.can_loan()

    def stowaway_partial(self, cheapest_slot_cost: int) -> bool:
        return self.money < cheapest_slot_cost and not self.can_loan()

    def use_worker(self) -> None:
        if self.workers_available <= 0:
            raise ValueError(f"玩家 [{self.name}] 没有可用工人")
        self.workers_available -= 1

    def return_all_workers(self) -> None:
        self.workers_available = self.workers_total
        self.can_deploy = True

    def net_worth(self, prices: dict[Goods, int]) -> int:
        stock_value = sum(self.stocks[g] * prices[g] for g in Goods)
        return self.money + stock_value

    def __repr__(self) -> str:
        tag = "人" if self.is_human else "AI"
        return f"Player({tag} {self.name!r}, ¥{self.money}, workers={self.workers_available}/{self.workers_total})"
