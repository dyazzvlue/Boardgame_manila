"""main.py — 程序入口"""
from __future__ import annotations
from player import Player
from ai import AIPlayer
from game import Game


def setup_players() -> list[Player]:
    print("\n欢迎来到 马尼拉！")
    while True:
        try:
            n = int(input("请输入玩家人数（3~5）: "))
            if 3 <= n <= 5:
                break
            print("  人数须在 3~5 之间")
        except ValueError:
            print("  无效输入")

    players: list[Player] = []
    for i in range(n):
        name = input(f"  玩家{i+1} 的名字: ").strip() or f"玩家{i+1}"
        is_human = input(f"  {name} 是真人玩家吗？(y/n): ").strip().lower() in ("y", "yes", "是", "1")
        if is_human:
            players.append(Player(name, n, is_human=True))
        else:
            players.append(AIPlayer(name, n))
    return players


def main() -> None:
    players = setup_players()
    game = Game(players)
    game.run()


if __name__ == "__main__":
    main()
