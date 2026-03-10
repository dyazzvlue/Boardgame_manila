"""game.py — 游戏主引擎"""
from __future__ import annotations
import random
from constants import CFG, Goods, PositionType
from player import Player
from market import Market
from ship import Ship
from board import Board
import ui
from logger import GameLogger



class _RollbackRequest(Exception):
    """部署阶段玩家请求回滚时抛出。"""


class Game:
    def __init__(self, players: list[Player]) -> None:
        self.players = players
        self.market = Market()
        self.ships: dict[Goods, Ship] = {g: Ship(g) for g in Goods}
        self.board = Board()
        self.active_goods: list[Goods] = list(Goods)
        self.hm_index: int = 0  # 当前港务长索引
        self.round_num: int = 0
        self._sub_round: int = 0
        self.logger = GameLogger()

    # ─────────────────────────────────────────────────────────
    # 初始化
    # ─────────────────────────────────────────────────────────
    def setup(self) -> None:
        self.market.setup(self.players)
        print("\n" + "=" * 50)
        print("  马尼拉 开始！")
        print("=" * 50)
        for p in self.players:
            if p.is_human:
                print(f"\n{p.name}，您的初始股票：")
                for g, cnt in p.stocks.items():
                    if cnt > 0:
                        print(f"  {ui.good_str(g)} × {cnt}")
            else:
                print(f"  AI 玩家 {p.name} 已就绪")
        self.hm_index = 0


    # ─────────────────────────────────────────────────────────
    # 状态快照（用于回滚）
    # ─────────────────────────────────────────────────────────
    def _save_state(self) -> dict:
        """将当前游戏状态序列化为可复制的字典。"""
        return {
            "round_num": self.round_num,
            "hm_index": self.hm_index,
            "active_goods": [g.value for g in self.active_goods],
            "market": {
                "prices": {g.value: v for g, v in self.market.prices.items()},
                "bank_stocks": {g.value: v for g, v in self.market.bank_stocks.items()},
            },
            "players": [
                {
                    "name": p.name,
                    "money": p.money,
                    "stocks": {g.value: v for g, v in p.stocks.items()},
                    "pledged_stocks": [g.value for g in p.pledged_stocks],
                    "workers_available": p.workers_available,
                    "can_deploy": p.can_deploy,
                }
                for p in self.players
            ],
            "ships": {
                g.value: {
                    "position": s.position,
                    "docked_at": s.docked_at.value if s.docked_at else None,
                    "hijacked": s.hijacked,
                    "slots": [
                        {"worker": slot.worker.name if slot.worker else None}
                        for slot in s.slots
                    ],
                }
                for g, s in self.ships.items()
            },
            "board": {
                "port_slots": [{"worker": s.worker.name if s.worker else None}
                                for s in self.board.port_slots],
                "shipyard_slots": [{"worker": s.worker.name if s.worker else None}
                                   for s in self.board.shipyard_slots],
                "pirate_slots": [{"worker": s.worker.name if s.worker else None}
                                 for s in self.board.pirate_slots],
                "navigator_slots": [{"worker": s.worker.name if s.worker else None}
                                    for s in self.board.navigator_slots],
                "insurance_slot": self.board.insurance_slot.name
                                  if self.board.insurance_slot else None,
            },
        }

    def _load_state(self, state: dict) -> None:
        """从快照字典恢复游戏状态。"""
        self.round_num = state["round_num"]
        self.hm_index = state["hm_index"]
        self.active_goods = [Goods(v) for v in state["active_goods"]]

        for k, v in state["market"]["prices"].items():
            self.market.prices[Goods(k)] = v
        for k, v in state["market"]["bank_stocks"].items():
            self.market.bank_stocks[Goods(k)] = v

        p_map = {p.name: p for p in self.players}
        for pd in state["players"]:
            p = p_map[pd["name"]]
            p.money = pd["money"]
            p.stocks = {Goods(k): v for k, v in pd["stocks"].items()}
            p.pledged_stocks = [Goods(v) for v in pd["pledged_stocks"]]
            p.workers_available = pd["workers_available"]
            p.can_deploy = pd["can_deploy"]

        for gv, sd in state["ships"].items():
            ship = self.ships[Goods(gv)]
            ship.position = sd["position"]
            ship.docked_at = PositionType(sd["docked_at"]) if sd["docked_at"] else None
            ship.hijacked = sd["hijacked"]
            for i, slotd in enumerate(sd["slots"]):
                ship.slots[i].worker = p_map[slotd["worker"]] if slotd["worker"] else None

        bd = state["board"]
        for i, sd in enumerate(bd["port_slots"]):
            self.board.port_slots[i].worker = p_map[sd["worker"]] if sd["worker"] else None
        for i, sd in enumerate(bd["shipyard_slots"]):
            self.board.shipyard_slots[i].worker = p_map[sd["worker"]] if sd["worker"] else None
        for i, sd in enumerate(bd["pirate_slots"]):
            self.board.pirate_slots[i].worker = p_map[sd["worker"]] if sd["worker"] else None
        for i, sd in enumerate(bd["navigator_slots"]):
            self.board.navigator_slots[i].worker = p_map[sd["worker"]] if sd["worker"] else None
        self.board.insurance_slot = (
            p_map[bd["insurance_slot"]] if bd["insurance_slot"] else None
        )

    # ─────────────────────────────────────────────────────────
    # 主循环
    # ─────────────────────────────────────────────────────────
    def run(self) -> None:
        self.setup()
        while not self.market.is_game_over():
            self.round_num += 1
            print(f"\n{'='*50}")
            print(f"  第 {self.round_num} 轮")
            print(f"{'='*50}")
            self._run_round()
            if self.market.is_game_over():
                break
        ui.show_final_scores(self.players, self.market)
        import os
        from datetime import datetime as _dt
        _log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
        _log_path = os.path.join(_log_dir, _dt.now().strftime("game_%Y%m%d_%H%M%S.json"))
        self.logger.save(_log_path)

    # ─────────────────────────────────────────────────────────
    # 单轮逻辑
    # ─────────────────────────────────────────────────────────
    def _run_round(self) -> None:
        # 1. 港务长竞拍
        hm = self._bid_harbor_master()
        self.hm_index = self.players.index(hm)
        print(f"\n  {ui.player_str(hm, self.players)} 成为本轮港务长！")

        # 2. 港务长行动（买股票 → 选货物 → 设出发位置）
        self._harbor_master_actions(hm)

        # 3. 三轮部署+骰子
        for sub_round in range(1, 4):
            self._sub_round = sub_round
            print("\n" + "=" * 50)
            print(f"  ── 第{sub_round}次出海 ──")
            self._deploy_phase(sub_round)
            self._roll_and_move(sub_round)

        # 4. 结算利润
        self._distribute_profits()

        # 5. 涨价
        self._raise_prices()

        # 6. 回合结束
        self._end_round()

    # ─────────────────────────────────────────────────────────
    # 竞拍港务长
    # ─────────────────────────────────────────────────────────
    def _bid_harbor_master(self) -> Player:
        n = len(self.players)
        prev_hm = self.players[self.hm_index]
        print("\n" + "=" * 50)
        print(f"{ui.BOLD}── 竞拍港务长 ──{ui.RESET}")
        print(f"  上轮港务长: {prev_hm.name}")

        current_bid = 0
        winning_player = prev_hm
        # 从港务长下家开始顺时针
        order = [(self.hm_index + i + 1) % n for i in range(n - 1)]
        active_bidders = list(order)

        # 循环叫价：除当前最高出价者外，其余人可继续出价，直到一轮内无人再加价
        passed: set[int] = set()  # 已永久放弃的玩家索引
        while True:
            new_bid_this_round = False
            for idx in active_bidders:
                if idx in passed:
                    continue
                # 当前最高出价者不需要自己超自己
                if self.players[idx] is winning_player and current_bid > 0:
                    continue
                p = self.players[idx]
                min_bid = current_bid + 1
                if p.is_human:
                    _bsfn = lambda: ui.show_full_state(self.market, self.ships, self.board, self.players, self.active_goods)
                    bid = ui.ask_bid(p.name, current_bid, min_bid, state_fn=_bsfn)
                else:
                    bid = p.decide_bid(current_bid, self.market, self.active_goods)
                    if bid > 0:
                        print(f"  {p.name}（AI）出价 {bid}")
                    else:
                        print(f"  {p.name}（AI）放弃")
                if bid >= min_bid and bid <= p.money:
                    current_bid = bid
                    winning_player = p
                    new_bid_this_round = True
                    self.logger.record(self.round_num, 0, p.name, "出价", {"bid": bid})
                else:
                    passed.add(idx)
                    self.logger.record(self.round_num, 0, p.name, "放弃竞拍", {})
            if not new_bid_this_round:
                break
            # 重置：让其他非放弃者可以继续叫价
            # passed 只记录永久放弃者，每轮自动跳过他们

        # 港务长支付竞价费用给池子（或上轮港务长）
        if winning_player != prev_hm and current_bid > 0:
            winning_player.pay(current_bid)
            prev_hm.collect(current_bid)
            print(f"  {winning_player.name} 花费 {current_bid} 比索成为港务长，上轮港务长 {prev_hm.name} 获得 {current_bid}")
            self.logger.record(self.round_num, 0, winning_player.name, "成为港务长", {"cost": current_bid})
        else:
            print(f"  无人竞价，{prev_hm.name} 免费连任港务长")
            self.logger.record(self.round_num, 0, prev_hm.name, "连任港务长", {"cost": 0})

        return winning_player

    # ─────────────────────────────────────────────────────────
    # 港务长行动
    # ─────────────────────────────────────────────────────────
    def _harbor_master_actions(self, hm: Player) -> None:
        print("\n" + "=" * 50)
        print(f"{ui.BOLD}── 港务长行动 ──{ui.RESET}")
        # 可选：购买股票
        if hm.is_human:
            good = ui.ask_buy_stock(hm.name, self.market, hm.money)
        else:
            good = hm.decide_buy_stock(self.market)
        if good is not None:
            price = self.market.buy_stock(good, hm)
            print(f"  {hm.name} 购买了 {ui.good_str(good)}，花费 {price}")
            self.logger.record(self.round_num, 0, hm.name, "购买股票", {"good": good.value}, f"花费{price}")
        else:
            self.logger.record(self.round_num, 0, hm.name, "不购买股票", {})

        # 选择本轮运输货物（排除一种）
        if hm.is_human:
            self.active_goods = ui.ask_choose_goods(hm.name, list(Goods))
        else:
            self.active_goods = hm.decide_choose_goods(list(Goods), self.market)
            excluded = [g for g in Goods if g not in self.active_goods]
            print(f"  {hm.name}（AI）排除了 {ui.good_str(excluded[0])}")

        # 设置各货船初始位置
        if hm.is_human:
            positions = ui.ask_ship_placement(hm.name, self.active_goods, len(self.active_goods))
        else:
            positions = hm.decide_ship_placement(self.active_goods)
            print(f"  {hm.name}（AI）分配位置: " +
                  ", ".join(f"{ui._good_name(g)}={v}" for g, v in positions.items()))
        for g, pos in positions.items():
            self.ships[g].position = pos
        self.logger.record(self.round_num, 0, hm.name, "设置出发位置",
                           {g.value: pos for g, pos in positions.items()})

        ui.show_ships(self.ships, self.active_goods)

    # ─────────────────────────────────────────────────────────
    # 部署阶段
    # ─────────────────────────────────────────────────────────
    def _deploy_phase(self, sub_round: int) -> None:
        n = len(self.players)
        # 3人局第1子轮：每人各部署2次
        deploys_per_player = 2 if (n == 3 and sub_round == 1) else 1
        order = [(self.hm_index + i + 1) % n for i in range(n)]

        while True:
            snap = self._save_state()
            try:
                for _ in range(deploys_per_player):
                    for idx in order:
                        self._do_deploy(self.players[idx])
                break
            except _RollbackRequest:
                self._load_state(snap)
                self.logger.record(self.round_num, sub_round, "系统", "回滚",
                                   {"sub_round": sub_round}, "部署阶段已回滚")
                print("\n  ↩ 已回滚！本次出海的所有部署已撤销，请重新部署。\n")

    def _do_deploy(self, player: Player) -> None:
        if player.workers_available == 0 or not player.can_deploy:
            return
        if player.is_human:
            _sfn = lambda: ui.show_full_state(self.market, self.ships, self.board, self.players, self.active_goods)
            ui.show_full_state(self.market, self.ships, self.board, self.players, self.active_goods)
            result = ui.ask_deploy_position(
                player.name, self.ships, self.board,
                self.active_goods, player.workers_available, state_fn=_sfn
            )
            if result == "rollback":
                raise _RollbackRequest()
        else:
            result = player.decide_deploy(
                self.ships, self.board, self.market, self.active_goods, self.players
            )

        if result is None:
            player.can_deploy = False
            self.logger.record(self.round_num, self._sub_round, player.name, "跳过部署", {})
            print(f"  {player.name} 选择不再部署")
            return

        pos_type, idx1, idx2 = result
        try:
            if pos_type == "ship":
                g = self.active_goods[idx1]
                cost = self.ships[g].add_worker(idx2, player)
                print(f"  {player.name} → {ui.good_str(g)} 槽{idx2}（花费{cost}）")
                self.logger.record(self.round_num, self._sub_round, player.name, "部署",
                                   {"type": "ship", "good": g.value, "slot": idx2}, f"花费{cost}")
            elif pos_type == "port":
                cost = self.board.deploy_port(idx1, player)
                print(f"  {player.name} → 港口 {self.board.port_slots[idx1].label}（花费{cost}）")
                self.logger.record(self.round_num, self._sub_round, player.name, "部署",
                                   {"type": "port", "slot": idx1}, f"花费{cost}")
            elif pos_type == "shipyard":
                cost = self.board.deploy_shipyard(idx1, player)
                print(f"  {player.name} → 造船厂 {self.board.shipyard_slots[idx1].label}（花费{cost}）")
                self.logger.record(self.round_num, self._sub_round, player.name, "部署",
                                   {"type": "shipyard", "slot": idx1}, f"花费{cost}")
            elif pos_type == "navigator":
                cost = self.board.deploy_navigator(idx1, player)
                print(f"  {player.name} → 航海家 {self.board.navigator_slots[idx1].label}（花费{cost}）")
                self.logger.record(self.round_num, self._sub_round, player.name, "部署",
                                   {"type": "navigator", "slot": idx1}, f"花费{cost}")
            elif pos_type == "pirate":
                cost = self.board.deploy_pirate(idx1, player)
                print(f"  {player.name} → 海盗 {self.board.pirate_slots[idx1].label}（花费{cost}）")
                self.logger.record(self.round_num, self._sub_round, player.name, "部署",
                                   {"type": "pirate", "slot": idx1}, f"花费{cost}")
            elif pos_type == "insurance":
                gain = self.board.deploy_insurance(player)
                print(f"  {player.name} → 保险（立即获得+{gain}）")
                self.logger.record(self.round_num, self._sub_round, player.name, "部署",
                                   {"type": "insurance"}, f"获得{gain}")
        except ValueError as e:
            print(f"  ⚠ 部署失败: {e}")

    # ─────────────────────────────────────────────────────────
    # 掷骰子 + 移船
    # ─────────────────────────────────────────────────────────
    def _roll_and_move(self, sub_round: int) -> None:
        # 第3子轮：先航海家行动，再掷骰子，再海盗抢劫
        # 第2子轮：掷骰子后，海盗登船
        if sub_round == 3:
            self._navigator_action()

        # 掷骰子（>13越过终点直接进港，==13等待海盗行动）
        rolls: dict[Goods, int] = {}
        track_roll = CFG["game"]["ship_track_length"]
        print(f"\n  掷骰子:")
        for g_roll in self.active_goods:
            ship_r = self.ships[g_roll]
            if ship_r.docked_at is not None:
                continue
            roll = random.randint(1, 6)
            rolls[g_roll] = roll
            intended = ship_r.position + roll
            ship_r.position = min(intended, track_roll)
            overshot_str = "（越过终点）" if intended > track_roll else ""
            print(f"    {ui.good_str(g_roll)}: 🎲{roll}  → 位置 {ship_r.position}{overshot_str}")
            self.logger.record(self.round_num, sub_round, "骰子", "掷骰",
                               {"good": g_roll.value, "roll": roll,
                                "new_pos": self.ships[g_roll].position,
                                "overshot": (intended > track_roll)})
            if intended > track_roll:
                self.ships[g_roll].dock_to_port()
                print(f"    {ui.good_str(g_roll)} 越过终点 → 直接进港！🏁")

        if sub_round == 2:
            self._pirate_board_action()
        elif sub_round == 3:
            self._pirate_rob_action()

        # 海盗行动后，正好在终点(=13)且未被劫持的船 → 造船厂
        # (超过13的船已在掷骰时直接进港；恰好=13且被劫持的船等海盗第3轮控制)
        track_final = CFG["game"]["ship_track_length"]
        for g in self.active_goods:
            ship = self.ships[g]
            if ship.docked_at is None and ship.position == track_final and not ship.hijacked:
                ship.dock_to_shipyard()
                print(f"    {ui.good_str(g)} 停在终点，驶入造船厂 ⚓")

        ui.show_ships(self.ships, self.active_goods)

    # ─────────────────────────────────────────────────────────
    # 航海家行动（第3轮前）
    # ─────────────────────────────────────────────────────────
    def _navigator_action(self) -> None:
        """航海家行动：每步±1，不能超过13，返回 list[(Goods, delta)]。
        小航海家先（1步），大航海家后（2步，可分配到不同船）。
        """
        # 小航海家先（slot_idx=1），大航海家后（slot_idx=0）
        for slot_idx in [1, 0]:
            slot = self.board.navigator_slots[slot_idx]
            if slot.is_empty:
                continue
            nav_player = slot.worker
            move_steps = slot.move
            still_sailing = [g for g in self.active_goods if self.ships[g].docked_at is None]
            if not still_sailing:
                break
            if nav_player.is_human:
                ui.show_ships(self.ships, self.active_goods)
                moves = ui.ask_navigator_moves(nav_player.name, still_sailing,
                                               move_steps, self.ships)
            else:
                moves = nav_player.decide_navigator(still_sailing, move_steps,
                                                    self.market, self.ships)
            nav_track = CFG["game"]["ship_track_length"]
            for target, delta in moves:
                new_pos = max(0, min(nav_track, self.ships[target].position + delta))
                actual = new_pos - self.ships[target].position
                self.ships[target].position = new_pos
                dir_str = f"+{actual}" if actual >= 0 else str(actual)
                print(f"  {nav_player.name} 移动 {ui.good_str(target)} {dir_str}格 → {new_pos}")
                self.logger.record(self.round_num, self._sub_round, nav_player.name, "航海家",
                                   {"good": target.value, "delta": actual, "new_pos": new_pos})

    # ─────────────────────────────────────────────────────────
    # 海盗登船（第2轮骰子后）
    # ─────────────────────────────────────────────────────────
    def _pirate_board_action(self) -> None:
        """第2轮：海盗可登上恰好到达终点(pos==13)且未进港的货船，若船满则踢出一个工人占位。"""
        captain_slot = self.board.pirate_slots[0]
        if captain_slot.is_empty:
            return
        captain = captain_slot.worker
        track = CFG["game"]["ship_track_length"]
        # 只有恰好到达终点(==13)且未进港、未被劫持的船可登
        boardable = [g for g in self.active_goods
                     if self.ships[g].position == track
                     and self.ships[g].docked_at is None
                     and not self.ships[g].hijacked]
        if not boardable:
            return
        if captain.is_human:
            target = ui.ask_pirate_board(captain.name, boardable,
                                         {g: self.ships[g] for g in boardable})
        else:
            target = captain.decide_pirate_board(boardable, self.market, self.ships)
        if target is None:
            return
        ship = self.ships[target]
        # 若有空位直接上；若满则踢出一个工人
        empty_slots = [i for i, s in enumerate(ship.slots) if s.is_empty]
        if empty_slots:
            board_slot = empty_slots[0]
        else:
            # 踢出一个工人
            if captain.is_human:
                board_slot = ui.ask_pirate_kick_slot(captain.name, target, ship)
            else:
                # AI踢最便宜的槽位
                board_slot = min(range(len(ship.slots)), key=lambda i: ship.slots[i].cost)
            evicted_player = ship.slots[board_slot].clear()
            if evicted_player:
                evicted_player.workers_available += 1
                print(f"  海盗踢出 {evicted_player.name} 从 {ui.good_str(target)} 槽{board_slot}！")
        # 海盗不花费工人，直接占位（用特殊标记占位，captain本人不是普通工人）
        ship.slots[board_slot].worker = captain
        ship.hijacked = True
        print(f"  {captain.name} 登上了 {ui.good_str(target)} 槽{board_slot}！🏴‍☠️")

    # ─────────────────────────────────────────────────────────
    # 海盗抢劫（第3轮骰子后）
    # ─────────────────────────────────────────────────────────
    def _pirate_rob_action(self) -> None:
        """第3轮：海盗驱逐所有工人，控制船去向，并获得货物cargo_value分成。"""
        captain_slot = self.board.pirate_slots[0]
        crew_slot = self.board.pirate_slots[1]
        if captain_slot.is_empty:
            return
        captain = captain_slot.worker
        hijacked_ships = [g for g in self.active_goods if self.ships[g].hijacked]
        if not hijacked_ships:
            return

        track = CFG["game"]["ship_track_length"]
        for g in hijacked_ships:
            ship = self.ships[g]
            if ship.docked_at is not None:
                continue

            # 驱逐所有工人（含海盗自己占位的槽）
            evicted = ship.evict_all_workers()
            non_pirate_evicted = [p for p in evicted if p is not captain
                                  and (crew_slot.is_empty or p is not crew_slot.worker)]
            if evicted:
                names = ", ".join(p.name for p in evicted)
                print(f"  {captain.name} 驱逐 {ui.good_str(g)} 上的所有工人: {names}")

            # 海盗选择目的地
            if captain.is_human:
                dest = ui.ask_pirate_destination(captain.name, g, ship.position, track)
            else:
                dest = captain.decide_pirate_destination(g, ship.position, track, self.market)

            if dest >= track:
                ship.position = track
                ship.dock_to_port()
                print(f"  {ui.good_str(g)} 被送往港口！")
            else:
                ship.position = 0
                ship.dock_to_shipyard()
                print(f"  {ui.good_str(g)} 被送往造船厂！")

            # 海盗获得货物价值（若有船员则平分）
            cargo_val = CFG["goods"][g.value]["cargo_value"]
            pirates = [captain]
            if not crew_slot.is_empty and crew_slot.worker is not captain:
                pirates.append(crew_slot.worker)
            share = cargo_val // len(pirates)
            for pirate in pirates:
                pirate.collect(share)
                print(f"  海盗 {pirate.name} 获得 {ui.good_str(g)} 货物分成 {share} 比索")
            self.logger.record(self.round_num, self._sub_round, captain.name, "海盗劫货",
                               {"good": g.value, "dest": "port" if dest >= track else "shipyard",
                                "share": share, "pirates": [p.name for p in pirates]})

    # ─────────────────────────────────────────────────────────
    # 分发利润
    # ─────────────────────────────────────────────────────────
    def _distribute_profits(self) -> None:
        print("\n" + "=" * 50)
        print(f"{ui.BOLD}── 结算利润 ──{ui.RESET}")
        track = CFG["game"]["ship_track_length"]

        # 未停靠的船强制进造船厂
        for g in self.active_goods:
            ship = self.ships[g]
            if ship.docked_at is None:
                ship.dock_to_shipyard()
                print(f"  {ui.good_str(g)} 未抵港，驶入造船厂")

        port_goods = [g for g in self.active_goods if self.ships[g].docked_at == PositionType.PORT]
        shipyard_goods = [g for g in self.active_goods if self.ships[g].docked_at == PositionType.SHIPYARD]

        # 货物利润（只有港口船，按配置货物固定价值平分）
        for g in port_goods:
            cargo_val = CFG["goods"][g.value]["cargo_value"]
            payouts = self.ships[g].distribute_cargo_profit(cargo_val)
            if payouts:
                pout_str = ", ".join(f"{p.name}+{v}" for p, v in payouts.items())
                print(f"  {ui.good_str(g)} 货物利润（货值{cargo_val}）: {pout_str}")

        # 港口槽位利润（按到港船数量）
        # 规则：A/B/C分别对应第一/二/三艘到达的船
        # 用标签索引：第1艘=A, 第2艘=B, 第3艘=C
        port_labels = {0: "A", 1: "B", 2: "C"}
        docked_labels = {port_labels[i] for i in range(len(port_goods))}
        port_payouts = self.board.resolve_port(docked_labels)
        if port_payouts:
            pout_str = ", ".join(f"{p.name}+{v}" for p, v in port_payouts.items())
            print(f"  港口槽位收入: {pout_str}")

        # 造船厂槽位利润（有保险则由保险方赔付，否则银行兜底免费）
        ship_labels = {port_labels[i] for i in range(len(shipyard_goods))}
        ins_player = self.board.insurance_slot
        if ins_player is not None:
            # 保险方直接赔付造船厂槽位工人
            sy_payouts = self.board.resolve_shipyard_with_insurance(ship_labels, ins_player)
            if sy_payouts:
                pout_str = ", ".join(f"{p.name}+{v}" for p, v in sy_payouts.items())
                print(f"  造船厂槽位收入（保险赔付）: {pout_str}")
            total_paid = sum(sy_payouts.values())
            immediate = CFG["insurance"]["immediate_gain"]
            ins_net = immediate - total_paid
            print(f"  保险结算: {ins_player.name} 净收益 {ins_net}"
                  f"（立即+{immediate}，赔付造船厂 {total_paid}）")
        else:
            # 无人购买保险，造船厂槽位收益由银行支付
            sy_payouts = self.board.resolve_shipyard(ship_labels)
            if sy_payouts:
                pout_str = ", ".join(f"{p.name}+{v}" for p, v in sy_payouts.items())
                print(f"  造船厂槽位收入: {pout_str}")

        ui.show_players(self.players, self.market)

    # ─────────────────────────────────────────────────────────
    # 涨价
    # ─────────────────────────────────────────────────────────
    def _raise_prices(self) -> None:
        print("\n" + "=" * 50)
        print(f"{ui.BOLD}── 股价上涨 ──{ui.RESET}")
        port_goods = [g for g in self.active_goods if self.ships[g].docked_at == PositionType.PORT]
        for g in port_goods:
            new_price = self.market.raise_price(g)
            print(f"  {ui.good_str(g)} 价格上涨 → {new_price}")
        ui.show_market(self.market)

    # ─────────────────────────────────────────────────────────
    # 回合结束
    # ─────────────────────────────────────────────────────────
    def _end_round(self) -> None:
        self.board.reset()
        for g in Goods:
            self.ships[g].reset()
        for p in self.players:
            p.return_all_workers()
            p.can_deploy = True
        # 港务长顺时针轮转到下一人（但若有竞价则在_bid中已设置）
        self.hm_index = (self.hm_index + 1) % len(self.players)
