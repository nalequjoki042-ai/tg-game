from pydantic import BaseModel
from typing import Any


# --- Incoming (client → server) ---

class PingMessage(BaseModel):
    type: str = "ping"


class ActionMessage(BaseModel):
    type: str = "action"
    payload: dict[str, Any] = {}


# --- Outgoing (server → client) ---

class PongMessage(BaseModel):
    type: str = "pong"
    echo: dict[str, Any] = {}


class StateMessage(BaseModel):
    type: str = "state"
    payload: dict[str, Any] = {}


class ErrorMessage(BaseModel):
    type: str = "error"
    message: str
