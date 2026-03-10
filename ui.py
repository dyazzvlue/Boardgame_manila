"""ui.py — 终端 UI：显示与输入"""
from __future__ import annotations
from typing import Optional
from constants import CFG, Goods, PositionType

# ── ANSI 颜色 ──────────────────────────────────────────────────────────────
RESET = "\033[0m"
BOLD = "\033[1m"
FG = {
    "black": "\033[30m", "red": "\033[31m", "green": "\033[32m",
    "yellow": "\033[33m", "blue": "\033[34m", "magenta": "\033[35m",
    "cyan": "\033[36m", "white": "\033[37m",
    "brown": "\033[33m",
}
GOOD_COLOR = {
    Goods.nutmeg: FG["brown"],
    Goods.silk: FG["blue"],
    Goods.ginseng: FG["yellow"],
    Goods.jade: FG["green"],
}
GOOD_ICON = {
    Goods.nutmeg: "🌰",
    Goods.silk: "🪡",
    Goods.ginseng: "🌿",
    Goods.jade: "💎",
}
PLAYER_COLORS = [FG["cyan"], FG["magenta"], FG["red"], FG["green"], FG["yellow"]]

def _good_name(good: Goods) -> str:
    return CFG["goods"][good.value]["name"]

def good_str(good: Goods) -> str:
    return f"{GOOD_COLOR[good]}{GOOD_ICON[good]}{_good_name(good)}{RESET}"

def player_str(player, player_list) -> str:
    idx = player_list.index(player)
    color = PLAYER_COLORS[idx % len(PLAYER_COLORS)]
    return f"{color}{BOLD}{player.name}{RESET}"


# ── 显示函数 ───────────────────────────────────────────────────────────────
def show_market(market, player_list=None) -> None:
    print(f"\n{BOLD}── 市场股价 ──{RESET}")
    for g in Goods:
        price = market.prices[g]
        bank = market.bank_stocks[g]
        bar = "█" * (price // 5) + "░" * (6 - price // 5) if price <= 30 else "██████"
        print(f"  {good_str(g):20s}  价格: {BOLD}{price:2d}{RESET}  {bar}  银行余量: {bank}")
    print()


def show_ships(ships: dict, active_goods: list) -> None:
    track = CFG["game"]["ship_track_length"]
    print(f"\n{BOLD}── 货船位置 ──{RESET}")
    for g in Goods:
        if g not in active_goods:
            continue
        ship = ships[g]
        pos = ship.position
        line = list("·" * (track + 1))
        if pos <= track:
            line[pos] = "⛵"
        track_str = "".join(line)
        # 槽位工人
        slot_info = []
        for i, slot in enumerate(ship.slots):
            if slot.is_empty:
                slot_info.append(f"槽{i}(空,费{slot.cost})")
            else:
                slot_info.append(f"槽{i}({slot.worker.name})")
        workers_str = "  ".join(slot_info)
        docked = f" [{ship.docked_at.value}]" if ship.docked_at else ""
        hijacked = " [被劫持]" if ship.hijacked else ""
        print(f"  {good_str(g):20s}  [{track_str}] {pos:2d}/13{docked}{hijacked}")
        print(f"    {workers_str}")
    print()


def show_board(board) -> None:
    print(f"\n{BOLD}── 板块槽位 ──{RESET}")
    # 港口
    print(f"  {BOLD}港口:{RESET}")
    for i, s in enumerate(board.port_slots):
        occ = s.worker.name if s.worker else "空"
        print(f"    [{i}] {s.label} — 费用:{s.cost} 利润:{s.profit}  占用:{occ}")
    # 造船厂
    print(f"  {BOLD}造船厂:{RESET}")
    for i, s in enumerate(board.shipyard_slots):
        occ = s.worker.name if s.worker else "空"
        print(f"    [{i}] {s.label} — 费用:{s.cost} 利润:{s.profit}  占用:{occ}")
    # 航海家
    print(f"  {BOLD}航海家:{RESET}")
    for i, s in enumerate(board.navigator_slots):
        occ = s.worker.name if s.worker else "空"
        print(f"    [{i}] {s.label} — 费用:{s.cost} 移动+{s.move}  占用:{occ}")
    # 海盗
    print(f"  {BOLD}海盗:{RESET}")
    for i, s in enumerate(board.pirate_slots):
        occ = s.worker.name if s.worker else "空"
        print(f"    [{i}] {s.label} — 费用:{s.cost}  占用:{occ}")
    # 保险
    ins_occ = board.insurance_slot.name if board.insurance_slot else "空"
    print(f"  {BOLD}保险:{RESET} 立即+10比索  占用:{ins_occ}")
    print()


def show_players(players, market) -> None:
    print(f"\n{BOLD}── 玩家状态 ──{RESET}")
    for i, p in enumerate(players):
        stocks_str = "  ".join(
            f"{good_str(g)}×{p.stocks.get(g,0)}"
            for g in Goods if p.stocks.get(g, 0) > 0
        ) or "无"
        pledged = len(p.pledged_stocks)
        nw = p.net_worth(market.prices)
        kind = "(AI)" if not p.is_human else "(人)"
        print(f"  {PLAYER_COLORS[i%len(PLAYER_COLORS)]}{BOLD}{p.name}{RESET}"
              f"  金钱:{BOLD}{p.money}{RESET}  净资产:{nw}"
              f"  工人:{p.workers_available}/{p.workers_total}"
              f"  {kind}")
        print(f"    股票: {stocks_str}  质押:{pledged}")
    print()


def show_full_state(market, ships, board, players, active_goods) -> None:
    show_market(market)
    show_ships(ships, active_goods)
    show_board(board)
    show_players(players, market)


def show_final_scores(players, market) -> None:
    print(f"\n{BOLD}══════ 游戏结束！最终计分 ══════{RESET}")
    ranked = sorted(players, key=lambda p: p.net_worth(market.prices), reverse=True)
    for rank, p in enumerate(ranked, 1):
        nw = p.net_worth(market.prices)
        stocks_val = sum(
            market.prices[g] * cnt
            for g, cnt in p.stocks.items()
        )
        print(f"  第{rank}名: {p.name}  净资产:{BOLD}{nw}{RESET}  "
              f"(现金:{p.money} + 股票市值:{stocks_val})")
    winner = ranked[0]
    print(f"\n{BOLD}{FG['yellow']}🏆 赢家: {winner.name}！{RESET}\n")


# ── 输入函数 ───────────────────────────────────────────────────────────────
def ask_int(prompt: str, lo: int, hi: int) -> int:
    while True:
        try:
            val = int(input(prompt))
            if lo <= val <= hi:
                return val
            print(f"  请输入 {lo}~{hi} 之间的整数")
        except (ValueError, EOFError):
            print("  无效输入，请重试")


def ask_choice(prompt: str, options: list[str]) -> int:
    for i, opt in enumerate(options):
        print(f"  [{i}] {opt}")
    return ask_int(prompt, 0, len(options) - 1)


def ask_yes_no(prompt: str) -> bool:
    while True:
        ans = input(f"{prompt} (y/n): ").strip().lower()
        if ans in ("y", "yes", "是", "1"):
            return True
        if ans in ("n", "no", "否", "0"):
            return False
        print("  请输入 y 或 n")


def ask_bid(player_name: str, current_bid: int, min_bid: int, state_fn=None) -> int:
    """返回出价（>= min_bid），或 0 表示放弃；输入 s 查看当前状态。"""
    while True:
        print(f"  当前最高出价: {current_bid}")
        ans = input(f"  {player_name} — 请出价（≥{min_bid}，输入0放弃，s查看状态）: ").strip()
        if ans in ("s", "S", "?"):
            if state_fn:
                state_fn()
            continue
        try:
            val = int(ans)
            if val == 0:
                return 0
            if val >= min_bid:
                return val
            print(f"  出价必须 ≥ {min_bid} 或输入 0 放弃")
        except ValueError:
            print("  无效输入")


def ask_ship_placement(player_name: str, active_goods: list, n_ships: int) -> dict:
    """
    让港务长分配初始ship位置，总和必须为 ship_start_sum (=9)。
    返回 {Goods: position}
    """
    target_sum = CFG["game"]["ship_start_sum"]
    names = [_good_name(g) for g in active_goods]
    while True:
        print(f"\n  {player_name}，请为 {n_ships} 艘货船分配初始位置（总和须为{target_sum}）：")
        positions = {}
        for g, name in zip(active_goods, names):
            v = ask_int(f"    {name} 的起始位置（0-9）: ", 0, 9)
            positions[g] = v
        if sum(positions.values()) == target_sum:
            return positions
        print(f"  ❌ 位置总和为 {sum(positions.values())}，必须为 {target_sum}，请重新分配")


def ask_choose_goods(player_name: str, all_goods: list) -> list:
    """港务长从全部货物中选择排除一种，返回其余货物列表。"""
    print(f"\n  {player_name}，请选择本轮{BOLD}不{RESET}运输的货物：")
    options = [_good_name(g) for g in all_goods]
    idx = ask_choice("  输入编号: ", options)
    excluded = all_goods[idx]
    active = [g for g in all_goods if g != excluded]
    print(f"  已排除 {good_str(excluded)}，本轮运输: {', '.join(good_str(g) for g in active)}")
    return active


def ask_buy_stock(player_name: str, market, player_money: int) -> Optional[Goods]:
    """询问是否购买股票，返回 Goods 或 None。"""
    available = [g for g in Goods if market.can_buy(g)]
    if not available:
        print("  银行无可购买股票")
        return None
    if not ask_yes_no(f"  {player_name}，是否购买一张股票？"):
        return None
    options = [f"{_good_name(g)} (价格:{market.buy_price(g)}, 银行余:{market.bank_stocks[g]})" for g in available]
    idx = ask_choice("  选择购买的股票: ", options)
    good = available[idx]
    if market.buy_price(good) > player_money:
        print(f"  ❌ 金钱不足（需要{market.buy_price(good)}，只有{player_money}）")
        return None
    return good


def ask_deploy_position(player_name: str, ships: dict, board, active_goods: list,
                         workers_available: int, state_fn=None) -> Optional[tuple]:
    """
    让玩家选择部署位置。
    返回 (pos_type: str, idx1: int, idx2: int|None) 或 None(跳过)
    pos_type: 'port'|'shipyard'|'navigator'|'pirate'|'insurance'|'ship'
    对于 'ship': idx1=good在active_goods的索引, idx2=槽位索引
    对于 'port'/'shipyard'/'navigator'/'pirate': idx1=槽位索引, idx2=None
    对于 'insurance': idx1=0, idx2=None
    """
    if workers_available == 0:
        return None

    options = []
    option_data = []

    # 港口
    for i, s in enumerate(board.port_slots):
        if s.is_empty:
            options.append(f"港口 {s.label} (费用:{s.cost}, 利润:{s.profit})")
            option_data.append(("port", i, None))
    # 造船厂
    for i, s in enumerate(board.shipyard_slots):
        if s.is_empty:
            options.append(f"造船厂 {s.label} (费用:{s.cost}, 利润:{s.profit})")
            option_data.append(("shipyard", i, None))
    # 航海家
    for i, s in enumerate(board.navigator_slots):
        if s.is_empty:
            options.append(f"航海家 {s.label} (费用:{s.cost}, 移动+{s.move})")
            option_data.append(("navigator", i, None))
    # 海盗
    for i, s in enumerate(board.pirate_slots):
        if s.is_empty:
            options.append(f"海盗 {s.label} (费用:{s.cost})")
            option_data.append(("pirate", i, None))
    # 保险
    if board.insurance_slot is None:
        options.append("保险 (费用:0, 立即+10比索)")
        option_data.append(("insurance", 0, None))
    # 货船槽位（每艘船只显示费用最低的一个空槽）
    for gi, g in enumerate(active_goods):
        ship = ships[g]
        empty_slots = [(si, slot) for si, slot in enumerate(ship.slots) if slot.is_empty]
        if not empty_slots:
            continue
        cheapest_si, cheapest_slot = min(empty_slots, key=lambda x: x[1].cost)
        # 构建其他槽位描述（不包含当前选中槽）
        other_descs = []
        for si, slot in enumerate(ship.slots):
            if si == cheapest_si:
                continue
            if slot.is_empty:
                other_descs.append(f"槽{si}:费用{slot.cost}")
            else:
                other_descs.append(f"槽{si}:[{slot.worker.name}]")
        others = "  ".join(other_descs)
        options.append(
            f"货船 {_good_name(g)} 槽{cheapest_si}(费{cheapest_slot.cost})"
            + (f"  |  其他槽: {others}" if others else "")
        )
        option_data.append(("ship", gi, cheapest_si))

    if not options:
        print("  没有可部署的位置")
        return None

    options_display = options + ["📊 查看当前状态", "跳过（不再部署）", "↩ 回滚本次出海的所有部署"]
    while True:
        print(f"\n  {player_name}，选择部署位置 (工人余: {workers_available})：")
        idx = ask_choice("  输入编号: ", options_display)
        if idx == len(options_display) - 1:
            return "rollback"
        if idx == len(options_display) - 2:
            return None
        if idx == len(options_display) - 3:
            if state_fn:
                state_fn()
            continue
        return option_data[idx]


def ask_navigator_moves(nav_player_name: str, undocked_goods: list,
                         move_steps: int, ships: dict) -> list:
    """航海家操作：每步选一艘未进港的船移动±1格，不能超出0-13范围。
    返回 [(Goods, delta), ...] 最多 move_steps 个条目。
    """
    track = CFG["game"]["ship_track_length"]
    size_name = "大" if move_steps >= 2 else "小"
    print(f"\n  {nav_player_name}（{size_name}航海家，{move_steps}步）"
          f" — 每步选一艘船向前或向后移动1格，不能超过终点{track}")
    moves = []
    # 本地位置追踪（用于显示多步时的中间状态）
    local_pos = {g: ships[g].position for g in undocked_goods}
    for step in range(1, move_steps + 1):
        pos_str = "  ".join(f"{_good_name(g)}@{local_pos[g]}" for g in undocked_goods)
        print(f"  位置: {pos_str}")
        options = []
        move_data = []
        for gd in undocked_goods:
            pos = local_pos[gd]
            if pos < track:
                options.append(f"{_good_name(gd)} 向前+1（{pos}→{pos+1}）")
                move_data.append((gd, +1))
            if pos > 0:
                options.append(f"{_good_name(gd)} 向后-1（{pos}→{pos-1}）")
                move_data.append((gd, -1))
        options.append(f"跳过（结束移动，已用 {step-1}/{move_steps} 步）")
        print(f"  [{step}/{move_steps}步]")
        idx = ask_choice("  选择: ", options)
        if idx == len(options) - 1:
            break
        gd, delta = move_data[idx]
        local_pos[gd] += delta
        moves.append((gd, delta))
    return moves


def ask_pirate_board(pirate_player_name: str, active_goods: list,
                      ships: dict) -> Optional[Goods]:
    """第2轮骰子后，海盗船长选择登上哪艘到达13格的货船（或放弃）。"""
    print(f"\n  {pirate_player_name} 是海盗船长，可登上已到达终点的货船")
    options = []
    for g in active_goods:
        ship = ships[g]
        slots_info = "  ".join(
            f"槽{i}:{slot.worker.name if not slot.is_empty else f'空(费{slot.cost})'}"
            for i, slot in enumerate(ship.slots)
        )
        options.append(f"{_good_name(g)} | {slots_info}")
    options.append("放弃")
    idx = ask_choice("  选择登哪艘货船: ", options)
    if idx == len(active_goods):
        return None
    return active_goods[idx]


def ask_pirate_kick_slot(pirate_player_name: str, target_good: Goods,
                          ship) -> int:
    """第2轮，海盗选择踢出哪个槽位的工人（船已满時）。返回槽位索引。"""
    occupied = [(i, slot) for i, slot in enumerate(ship.slots) if not slot.is_empty]
    print(f"  {good_str(target_good)} 所有槽位已满，选择踢出哪个工人:")
    options = [f"槽{i} ({slot.worker.name}, 费用{slot.cost})" for i, slot in occupied]
    idx = ask_choice("  选择踢出的槽位: ", options)
    return occupied[idx][0]


def ask_pirate_destination(pirate_player_name: str, target_good: Goods, current_pos: int,
                            track_len: int) -> int:
    """第3轮骰子后，海盗选择目的地（港口=track_len 或 造船厂=0）。"""
    print(f"\n  {pirate_player_name} 控制 {good_str(target_good)} (当前位置:{current_pos})")
    print(f"  无论选择何处，海盗均可获得货物价值分成")
    print(f"  选择目的地:")
    print(f"  [0] 港口（股价上涨，原船员无法获利——海盗已驱逐全员）")
    print(f"  [1] 造船厂（股价不涨）")
    choice = ask_int("  输入编号: ", 0, 1)
    return track_len if choice == 0 else 0
