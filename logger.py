"""logger.py — 游戏操作日志，支持回放查阅。"""
from __future__ import annotations
import json
import os
from datetime import datetime


class GameLogger:
    """记录每一次操作，并在游戏结束时保存为 JSON 文件。"""

    def __init__(self) -> None:
        self.actions: list[dict] = []

    def record(
        self,
        round_num: int,
        sub_round: int,
        player_name: str,
        action_type: str,
        details: dict,
        result: str = "",
    ) -> None:
        """追加一条操作记录。"""
        self.actions.append(
            {
                "round": round_num,
                "sub_round": sub_round,
                "player": player_name,
                "action": action_type,
                "details": details,
                "result": result,
                "time": datetime.now().strftime("%H:%M:%S"),
            }
        )

    def save(self, path: str) -> None:
        """将日志保存为 JSON 文件（自动创建目录）。"""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.actions, f, ensure_ascii=False, indent=2)
        print(f"\n  📄 操作日志已保存至 {path}")
