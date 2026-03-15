from fastapi import WebSocket, WebSocketDisconnect
from backend.game.engine import Engine
from backend.game.models import Player
from backend.db.repository import Repository
import json


async def handle(websocket: WebSocket, tg_id: int, first_name: str):
    repo = Repository()
    await repo.init()

    player = await repo.get_or_create(tg_id, first_name)
    engine = Engine(player)

    await websocket.send_json({
        "type": "state",
        "payload": engine.get_state()
    })

    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)
            msg_type = data.get("type")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong", "echo": data})

            elif msg_type == "action":
                result = engine.handle_action(data.get("payload", {}))
                await repo.save(player)
                await websocket.send_json({
                    "type": "state",
                    "payload": result
                })

            else:
                await websocket.send_json({
                    "type": "error",
                    "message": f"unknown type: {msg_type}"
                })

    except WebSocketDisconnect:
        await repo.save(player)
        print(f"[WS] Player {tg_id} disconnected")
