"""
constants.py — 枚举定义 + 配置加载
"""
import json
import os
from enum import Enum, auto

class Goods(Enum):
    nutmeg  = "nutmeg"
    silk    = "silk"
    ginseng = "ginseng"
    jade    = "jade"

class PositionType(Enum):
    SHIP      = auto()
    PORT      = auto()
    SHIPYARD  = auto()
    PIRATE    = auto()
    NAVIGATOR = auto()
    INSURANCE = auto()

class GamePhase(Enum):
    SETUP      = auto()
    BIDDING    = auto()
    HM_ACTION  = auto()
    DEPLOY     = auto()
    ROLLING    = auto()
    PROFIT     = auto()
    RAISE      = auto()
    END        = auto()

_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "config.json")
CFG: dict = {}

def load_config(path: str = _CONFIG_PATH) -> None:
    global CFG
    if not os.path.exists(path):
        raise FileNotFoundError(f"配置文件未找到：{path}")
    with open(path, encoding="utf-8") as f:
        CFG = json.load(f)
    required_keys = {"game", "goods", "port", "shipyard", "pirate", "navigator", "insurance", "stocks"}
    missing = required_keys - CFG.keys()
    if missing:
        raise ValueError(f"config.json 缺少必要字段：{missing}")
    for key in Goods:
        if key.value not in CFG["goods"]:
            raise ValueError(f"config.json 中缺少货物配置：{key.value}")

load_config()
