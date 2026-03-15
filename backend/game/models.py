from dataclasses import dataclass, field
from typing import Any


@dataclass
class Player:
    tg_id: int
    first_name: str
    score: int = 0
    data: dict = field(default_factory=dict)  # game-specific state, any shape


@dataclass
class GameState:
    player: Player
    status: str = "idle"  # idle | playing | finished
    payload: dict = field(default_factory=dict)  # engine fills this
