# ──────────────────────────────────────────────────────────────────────────────
# Patch 3: 
#   1. 货船只显示最低费用可选槽（ui.py）
#   2. 超过13格直接进港；恰好=13触发海盗逻辑（game.py）
# ──────────────────────────────────────────────────────────────────────────────
import sys

# ─── UI.PY ────────────────────────────────────────────────────────────────────
with open('ui.py', 'r') as f:
    ui = f.read()
orig_ui = ui

OLD_SLOTS = (
    '    # 货船槽位（按货船分组，所有空槽均可选）\n'
    '    for gi, g in enumerate(active_goods):\n'
    '        ship = ships[g]\n'
    '        slot_descs = []\n'
    '        for si, slot in enumerate(ship.slots):\n'
    '            if slot.is_empty:\n'
    '                slot_descs.append(f"费用{slot.cost}")\n'
    '            else:\n'
    '                slot_descs.append(f"[{slot.worker.name}]")\n'
    '        for si, slot in enumerate(ship.slots):\n'
    '            if slot.is_empty:\n'
    '                others = "  ".join(\n'
    '                    f"槽{j}:{slot_descs[j]}" for j in range(len(ship.slots)) if j != si\n'
    '                )\n'
    '                options.append(\n'
    '                    f"货船 {_good_name(g)} 槽{si}(费{slot.cost})"\n'
    '                    + (f"  |  其他槽: {others}" if others else "")\n'
    '                )\n'
    '                option_data.append(("ship", gi, si))'
)
NEW_SLOTS = (
    '    # 货船槽位（每艘船只显示费用最低的一个空槽）\n'
    '    for gi, g in enumerate(active_goods):\n'
    '        ship = ships[g]\n'
    '        empty_slots = [(si, slot) for si, slot in enumerate(ship.slots) if slot.is_empty]\n'
    '        if not empty_slots:\n'
    '            continue\n'
    '        cheapest_si, cheapest_slot = min(empty_slots, key=lambda x: x[1].cost)\n'
    '        # 构建其他槽位描述（不包含当前选中槽）\n'
    '        other_descs = []\n'
    '        for si, slot in enumerate(ship.slots):\n'
    '            if si == cheapest_si:\n'
    '                continue\n'
    '            if slot.is_empty:\n'
    '                other_descs.append(f"槽{si}:费用{slot.cost}")\n'
    '            else:\n'
    '                other_descs.append(f"槽{si}:[{slot.worker.name}]")\n'
    '        others = "  ".join(other_descs)\n'
    '        options.append(\n'
    '            f"货船 {_good_name(g)} 槽{cheapest_si}(费{cheapest_slot.cost})"\n'
    '            + (f"  |  其他槽: {others}" if others else "")\n'
    '        )\n'
    '        option_data.append(("ship", gi, cheapest_si))'
)
ui = ui.replace(OLD_SLOTS, NEW_SLOTS)
assert ui != orig_ui, "UI: ship slot change FAILED"
print("UI Change 1 OK: cheapest slot only")

with open('ui.py', 'w') as f:
    f.write(ui)
print("ui.py written")

# ─── GAME.PY ──────────────────────────────────────────────────────────────────
with open('game.py', 'r') as f:
    g = f.read()
orig_g = g

# 1. dice roll + dock logic in _roll_and_move
OLD_DICE_DOCK = (
    '            self.logger.record(self.round_num, sub_round, "骰子", "掷骰",\n'
    '                               {"good": g.value, "roll": roll, "new_pos": self.ships[g].position})\n'
    '\n'
    '        # 检查是否到达港口（position >= track_length）\n'
    '        track = CFG["game"]["ship_track_length"]\n'
    '        for g in self.active_goods:\n'
    '            ship = self.ships[g]\n'
    '            if ship.position >= track and ship.docked_at is None:\n'
    '                ship.dock_to_port()\n'
    '                print(f"    {ui.good_str(g)} 抵达港口！🏁")\n'
    '\n'
    '        if sub_round == 2:\n'
    '            self._pirate_board_action()\n'
    '        elif sub_round == 3:\n'
    '            self._pirate_rob_action()\n'
    '\n'
    '        ui.show_ships(self.ships, self.active_goods)'
)
NEW_DICE_DOCK = (
    '            self.logger.record(self.round_num, sub_round, "骰子", "掷骰",\n'
    '                               {"good": g_roll.value, "roll": roll,\n'
    '                                "new_pos": self.ships[g_roll].position,\n'
    '                                "overshot": (intended > track_roll)})\n'
    '            if intended > track_roll:\n'
    '                self.ships[g_roll].dock_to_port()\n'
    '                print(f"    {ui.good_str(g_roll)} 越过终点 → 直接进港！🏁")\n'
    '\n'
    '        if sub_round == 2:\n'
    '            self._pirate_board_action()\n'
    '        elif sub_round == 3:\n'
    '            self._pirate_rob_action()\n'
    '\n'
    '        # 海盗行动后，正好到达终点(=13)且未被劫持的船进港\n'
    '        track_final = CFG["game"]["ship_track_length"]\n'
    '        for g in self.active_goods:\n'
    '            ship = self.ships[g]\n'
    '            if ship.docked_at is None and ship.position == track_final:\n'
    '                ship.dock_to_port()\n'
    '                print(f"    {ui.good_str(g)} 到达终点，进港！🏁")\n'
    '\n'
    '        ui.show_ships(self.ships, self.active_goods)'
)
g = g.replace(OLD_DICE_DOCK, NEW_DICE_DOCK)
assert g != orig_g, "Game Change 1 (dice+dock) FAILED"
print("Game Change 1 OK: dice+dock split logic")
c1 = g

# 2. Rewrite the dice rolling loop to compute "intended" and check overshoot
OLD_DICE_LOOP = (
    '        # 掷骰子\n'
    '        rolls: dict[Goods, int] = {}\n'
    '        print(f"\\n  掷骰子:")\n'
    '        for g in self.active_goods:\n'
    '            roll = random.randint(1, 6)\n'
    '            rolls[g] = roll\n'
    '            self.ships[g].move(roll)\n'
    '            print(f"    {ui.good_str(g)}: 🎲{roll}  → 位置 {self.ships[g].position}")\n'
    '            self.logger.record(self.round_num, sub_round, "骰子", "掷骰",'
)
NEW_DICE_LOOP = (
    '        # 掷骰子（>13越过终点直接进港，==13等待海盗行动）\n'
    '        rolls: dict[Goods, int] = {}\n'
    '        track_roll = CFG["game"]["ship_track_length"]\n'
    '        print(f"\\n  掷骰子:")\n'
    '        for g_roll in self.active_goods:\n'
    '            ship_r = self.ships[g_roll]\n'
    '            if ship_r.docked_at is not None:\n'
    '                continue\n'
    '            roll = random.randint(1, 6)\n'
    '            rolls[g_roll] = roll\n'
    '            intended = ship_r.position + roll\n'
    '            ship_r.position = min(intended, track_roll)\n'
    '            overshot_str = "（越过终点）" if intended > track_roll else ""\n'
    '            print(f"    {ui.good_str(g_roll)}: 🎲{roll}  → 位置 {ship_r.position}{overshot_str}")\n'
    '            self.logger.record(self.round_num, sub_round, "骰子", "掷骰",'
)
g = g.replace(OLD_DICE_LOOP, NEW_DICE_LOOP)
assert g != c1, "Game Change 2 (dice loop) FAILED"
print("Game Change 2 OK: dice loop with intended calc")
c2 = g

# 3. Navigator: compute intended before move to detect overshoot
OLD_NAV_MOVE = (
    '            if target is not None:\n'
    '                self.ships[target].move(move_steps)\n'
    '                print(f"  {nav_player.name} 使用航海家移动 {ui.good_str(target)} +{move_steps}步 → {self.ships[target].position}")\n'
    '                self.logger.record(self.round_num, self._sub_round, nav_player.name, "航海家",\n'
    '                                   {"good": target.value, "steps": move_steps, "new_pos": self.ships[target].position})\n'
    '                track = CFG["game"]["ship_track_length"]\n'
    '                if self.ships[target].position >= track and self.ships[target].docked_at is None:\n'
    '                    self.ships[target].dock_to_port()\n'
    '                    print(f"  {ui.good_str(target)} 通过航海家抵达港口！🏁")'
)
NEW_NAV_MOVE = (
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
g = g.replace(OLD_NAV_MOVE, NEW_NAV_MOVE)
assert g != c2, "Game Change 3 (navigator) FAILED"
print("Game Change 3 OK: navigator overshoot logic")
c3 = g

# 4. pirate_board_action: boardable = exactly at 13 and not yet docked
OLD_BOARDABLE = (
    '        """第2轮：海盗可登上已到达终点(pos>=13)的货船，若船满则踢出一个工人占位。"""\n'
    '        captain_slot = self.board.pirate_slots[0]\n'
    '        if captain_slot.is_empty:\n'
    '            return\n'
    '        captain = captain_slot.worker\n'
    '        track = CFG["game"]["ship_track_length"]\n'
    '        # 只有到达终点且未被劫持的船可登\n'
    '        boardable = [g for g in self.active_goods\n'
    '                     if self.ships[g].position >= track and not self.ships[g].hijacked]'
)
NEW_BOARDABLE = (
    '        """第2轮：海盗可登上恰好到达终点(pos==13)且未进港的货船，若船满则踢出一个工人占位。"""\n'
    '        captain_slot = self.board.pirate_slots[0]\n'
    '        if captain_slot.is_empty:\n'
    '            return\n'
    '        captain = captain_slot.worker\n'
    '        track = CFG["game"]["ship_track_length"]\n'
    '        # 只有恰好到达终点(==13)且未进港、未被劫持的船可登\n'
    '        boardable = [g for g in self.active_goods\n'
    '                     if self.ships[g].position == track\n'
    '                     and self.ships[g].docked_at is None\n'
    '                     and not self.ships[g].hijacked]'
)
g = g.replace(OLD_BOARDABLE, NEW_BOARDABLE)
assert g != c3, "Game Change 4 (boardable) FAILED"
print("Game Change 4 OK: boardable == track and docked_at is None")

with open('game.py', 'w') as f:
    f.write(g)
print("game.py written")
print("\nAll patches applied successfully!")
