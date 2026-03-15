from backend.game.models import Player
from typing import Any


class Engine:
    """
    Universal game engine stub.
    Replace the body of handle_action() with your game logic.
    Do NOT change the interface (get_state / handle_action signatures).
    """

    def __init__(self, player: Player):
        self.player = player

    def get_state(self) -> dict[str, Any]:
        return {
            "player": {
                "tg_id": self.player.tg_id,
                "first_name": self.player.first_name,
                "score": self.player.score,
            },
            "status": "idle",
            "game": self.player.data
        }

    def handle_action(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Process one player action and return new state.
        payload = whatever the frontend sends inside { type: 'action', payload: {...} }
        """
        # --- STUB: just echo action back ---
        # Replace this block with real game logic in Phase 1
        self.player.data["last_action"] = payload
        return self.get_state()
