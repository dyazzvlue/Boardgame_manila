# ──────────────────────────────────────────────────────────────────────────────
# Patch 4:
#   1. Final sweep: position==13 (non-hijacked) → SHIPYARD not PORT
#   2. Navigator: cap at 13 (no overshoot), moves return list[(Goods, delta)]
#      - Small(1): 1 step ±1 on any one undocked ship
#      - Large(2): 2 steps each ±1, can target different ships, capped at 0-13
#   3. game.py _navigator_action: apply (Goods, delta) list, no docking from nav
# ──────────────────────────────────────────────────────────────────────────────

# ─── GAME.PY ──────────────────────────────────────────────────────────────────
with open('game.py', 'r') as f:
    g = f.read()
orig = g

# 1. Final sweep: dock remaining ships at 13 to SHIPYARD (not port)
OLD_SWEEP = (
    '        # 海盗行动后，正好到达终点(=13)且未被劫持的船进港\n'
    '        track_final = CFG["game"]["ship_track_length"]\n'
    '        for g in self.active_goods:\n'
    '            ship = self.ships[g]\n'
    '            if ship.docked_at is None and ship.position == track_final:\n'
    '                ship.dock_to_port()\n'
    '                print(f"    {ui.good_str(g)} 到达终点，进港！🏁")'
)
NEW_SWEEP = (
    '        # 海盗行动后，正好在终点(=13)且未被劫持的船 → 造船厂\n'
    '        # (超过13的船已在掷骰时直接进港；恰好=13且被劫持的船等海盗第3轮控制)\n'
    '        track_final = CFG["game"]["ship_track_length"]\n'
    '        for g in self.active_goods:\n'
    '            ship = self.ships[g]\n'
    '            if ship.docked_at is None and ship.position == track_final and not ship.hijacked:\n'
    '                ship.dock_to_shipyard()\n'
    '                print(f"    {ui.good_str(g)} 停在终点，驶入造船厂 ⚓")'
)
g = g.replace(OLD_SWEEP, NEW_SWEEP)
assert g != orig, "Change 1 (sweep→shipyard) FAILED"
print("Change 1 OK: final sweep → shipyard")
c1 = g

# 2. Rewrite _navigator_action to use list[(Goods, delta)] interface
OLD_NAV_ACTION = (
    '    def _navigator_action(self) -> None:\n'
    '        # 小航海家先（slot_idx=1），大航海家后（slot_idx=0）\n'
    '        for slot_idx in [1, 0]:\n'
    '            slot = self.board.navigator_slots[slot_idx]\n'
    '            if slot.is_empty:\n'
    '                continue\n'
    '            nav_player = slot.worker\n'
    '            move_steps = slot.move\n'
    '            still_sailing = [g for g in self.active_goods if self.ships[g].docked_at is None]\n'
    '            if not still_sailing:\n'
    '                break\n'
    '            if nav_player.is_human:\n'
    '                ui.show_ships(self.ships, self.active_goods)\n'
    '                target = ui.ask_navigator_action(nav_player.name, still_sailing, move_steps)\n'
    '            else:\n'
    '                target = nav_player.decide_navigator(still_sailing, move_steps, self.market, self.ships)\n'
    '            if target is not None:\n'
    '                nav_intended = self.ships[target].position + move_steps\n'
    '                self.ships[target].move(move_steps)\n'
    '                print(f"  {nav_player.name} 使用航海家移动 {ui.good_str(target)} +{move_steps}步 → {self.ships[target].position}")\n'
    '                self.logger.record(self.round_num, self._sub_round, nav_player.name, "航海家",\n'
    '                                   {"good": target.value, "steps": move_steps, "new_pos": self.ships[target].position})\n'
    '                nav_track = CFG["game"]["ship_track_length"]\n'
    '                if nav_intended > nav_track and self.ships[target].docked_at is None:\n'
    '                    self.ships[target].dock_to_port()\n'
    '                    print(f"  {ui.good_str(target)} 通过航海家越过终点，直接进港！🏁")\n'
    '                elif self.ships[target].position == nav_track and self.ships[target].docked_at is None:\n'
    '                    print(f"  {ui.good_str(target)} 通过航海家到达终点（等待进港）")'
)
NEW_NAV_ACTION = (
    '    def _navigator_action(self) -> None:\n'
    '        """航海家行动：每步±1，不能超过13，返回 list[(Goods, delta)]。\n'
    '        小航海家先（1步），大航海家后（2步，可分配到不同船）。\n'
    '        """\n'
    '        # 小航海家先（slot_idx=1），大航海家后（slot_idx=0）\n'
    '        for slot_idx in [1, 0]:\n'
    '            slot = self.board.navigator_slots[slot_idx]\n'
    '            if slot.is_empty:\n'
    '                continue\n'
    '            nav_player = slot.worker\n'
    '            move_steps = slot.move\n'
    '            still_sailing = [g for g in self.active_goods if self.ships[g].docked_at is None]\n'
    '            if not still_sailing:\n'
    '                break\n'
    '            if nav_player.is_human:\n'
    '                ui.show_ships(self.ships, self.active_goods)\n'
    '                moves = ui.ask_navigator_moves(nav_player.name, still_sailing,\n'
    '                                               move_steps, self.ships)\n'
    '            else:\n'
    '                moves = nav_player.decide_navigator(still_sailing, move_steps,\n'
    '                                                    self.market, self.ships)\n'
    '            nav_track = CFG["game"]["ship_track_length"]\n'
    '            for target, delta in moves:\n'
    '                new_pos = max(0, min(nav_track, self.ships[target].position + delta))\n'
    '                actual = new_pos - self.ships[target].position\n'
    '                self.ships[target].position = new_pos\n'
    '                dir_str = f"+{actual}" if actual >= 0 else str(actual)\n'
    '                print(f"  {nav_player.name} 移动 {ui.good_str(target)} {dir_str}格 → {new_pos}")\n'
    '                self.logger.record(self.round_num, self._sub_round, nav_player.name, "航海家",\n'
    '                                   {"good": target.value, "delta": actual, "new_pos": new_pos})'
)
g = g.replace(OLD_NAV_ACTION, NEW_NAV_ACTION)
assert g != c1, "Change 2 (navigator action) FAILED"
print("Change 2 OK: _navigator_action with list[(Goods,delta)]")

with open('game.py', 'w') as f:
    f.write(g)
print("game.py written")

# ─── UI.PY ────────────────────────────────────────────────────────────────────
with open('ui.py', 'r') as f:
    u = f.read()
orig_u = u

OLD_ASK_NAV = (
    'def ask_navigator_action(nav_player_name: str, active_goods: list, move_steps: int) -> Optional[Goods]:\n'
    '    """导航员选择移动哪艘船（或放弃）。"""\n'
    '    print(f"\\n  {nav_player_name} 使用航海家能力，可移动 +{move_steps} 步")\n'
    '    options = [_good_name(g) for g in active_goods] + ["放弃使用"]\n'
    '    idx = ask_choice("  选择要移动的货船: ", options)\n'
    '    if idx == len(active_goods):\n'
    '        return None\n'
    '    return active_goods[idx]'
)
NEW_ASK_NAV = (
    'def ask_navigator_moves(nav_player_name: str, undocked_goods: list,\n'
    '                         move_steps: int, ships: dict) -> list:\n'
    '    """航海家操作：每步选一艘未进港的船移动±1格，不能超出0-13范围。\n'
    '    返回 [(Goods, delta), ...] 最多 move_steps 个条目。\n'
    '    """\n'
    '    track = CFG["game"]["ship_track_length"]\n'
    '    size_name = "大" if move_steps >= 2 else "小"\n'
    '    print(f"\\n  {nav_player_name}（{size_name}航海家，{move_steps}步）"\n'
    '          f" — 每步选一艘船向前或向后移动1格，不能超过终点{track}")\n'
    '    moves = []\n'
    '    # 本地位置追踪（用于显示多步时的中间状态）\n'
    '    local_pos = {g: ships[g].position for g in undocked_goods}\n'
    '    for step in range(1, move_steps + 1):\n'
    '        pos_str = "  ".join(f"{_good_name(g)}@{local_pos[g]}" for g in undocked_goods)\n'
    '        print(f"  位置: {pos_str}")\n'
    '        options = []\n'
    '        move_data = []\n'
    '        for gd in undocked_goods:\n'
    '            pos = local_pos[gd]\n'
    '            if pos < track:\n'
    '                options.append(f"{_good_name(gd)} 向前+1（{pos}→{pos+1}）")\n'
    '                move_data.append((gd, +1))\n'
    '            if pos > 0:\n'
    '                options.append(f"{_good_name(gd)} 向后-1（{pos}→{pos-1}）")\n'
    '                move_data.append((gd, -1))\n'
    '        options.append(f"跳过（结束移动，已用 {step-1}/{move_steps} 步）")\n'
    '        print(f"  [{step}/{move_steps}步]")\n'
    '        idx = ask_choice("  选择: ", options)\n'
    '        if idx == len(options) - 1:\n'
    '            break\n'
    '        gd, delta = move_data[idx]\n'
    '        local_pos[gd] += delta\n'
    '        moves.append((gd, delta))\n'
    '    return moves'
)
u = u.replace(OLD_ASK_NAV, NEW_ASK_NAV)
assert u != orig_u, "UI Change (ask_navigator_moves) FAILED"
print("UI Change OK: ask_navigator_moves")

with open('ui.py', 'w') as f:
    f.write(u)
print("ui.py written")

# ─── AI.PY ────────────────────────────────────────────────────────────────────
with open('ai.py', 'r') as f:
    ai = f.read()
orig_ai = ai

OLD_AI_NAV = (
    '    def decide_navigator(self, active_goods: list, move_steps: int,\n'
    '                          market: Market, ships: dict) -> Optional[Goods]:\n'
    '        """移动持仓最多且距港最近的货船。"""\n'
    '        candidates = [g for g in active_goods if not ships[g].hijacked]\n'
    '        if not candidates:\n'
    '            return None\n'
    '        track_len = CFG["game"]["ship_track_length"]\n'
    '        return max(candidates,\n'
    '                   key=lambda g: (self.stocks.get(g, 0), track_len - ships[g].position))'
)
NEW_AI_NAV = (
    '    def decide_navigator(self, active_goods: list, move_steps: int,\n'
    '                          market: Market, ships: dict) -> list:\n'
    '        """返回 [(Goods, delta), ...] 移动列表，每步向前+1。"""\n'
    '        track_len = CFG["game"]["ship_track_length"]\n'
    '        candidates = [g for g in active_goods if not ships[g].hijacked]\n'
    '        if not candidates:\n'
    '            return []\n'
    '        moves = []\n'
    '        temp_pos = {g: ships[g].position for g in active_goods}\n'
    '        for _ in range(move_steps):\n'
    '            # 选择可前进（未在终点）的船中距终点最近的\n'
    '            fwd = [g for g in candidates if temp_pos[g] < track_len]\n'
    '            if not fwd:\n'
    '                break\n'
    '            target = max(fwd, key=lambda g: (\n'
    '                self.stocks.get(g, 0), temp_pos[g]))\n'
    '            moves.append((target, +1))\n'
    '            temp_pos[target] += 1\n'
    '        return moves'
)
ai = ai.replace(OLD_AI_NAV, NEW_AI_NAV)
assert ai != orig_ai, "AI Change (decide_navigator) FAILED"
print("AI Change OK: decide_navigator returns list")

with open('ai.py', 'w') as f:
    f.write(ai)
print("ai.py written")
print("\nAll patches applied!")
