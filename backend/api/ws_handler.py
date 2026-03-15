import json
from fastapi import WebSocket
from backend.db.repository import Repository

# Глобальное состояние арены
BOSS_MAX_HP = 1000
arena_state = {
    "boss_hp": BOSS_MAX_HP,
    "players": {}  # slot -> {tg_id, name, hp, atk, ws}
}

# Свободные слоты
SLOTS = [0, 1, 2]


def get_free_slot() -> int:
    used = {v["slot"] for v in arena_state["players"].values()}
    for s in SLOTS:
        if s not in used:
            return s
    return -1


def state_payload(for_tg_id: int) -> dict:
    my_slot = -1
    plist = []
    for tid, p in arena_state["players"].items():
        if int(tid) == for_tg_id:
            my_slot = p["slot"]
        plist.append({"slot": p["slot"], "name": p["name"], "hp": p["hp"], "atk": p["atk"]})
    return {
        "type": "arena_state",
        "boss_hp": arena_state["boss_hp"],
        "my_slot": my_slot,
        "players": plist
    }


async def broadcast(exclude_id: int = None):
    dead = []
    for tid, p in arena_state["players"].items():
        try:
            payload = state_payload(int(tid))
            await p["ws"].send_text(json.dumps(payload))
        except Exception:
            dead.append(tid)
    for tid in dead:
        arena_state["players"].pop(tid, None)


async def handle(websocket: WebSocket, tg_id: int, first_name: str):
    repo = Repository()
    player = await repo.get_or_create(tg_id, first_name)

    try:
        async for raw in websocket.iter_text():
            msg = json.loads(raw)
            t = msg.get("type")

            # — вход в арену
            if t == "arena_join":
                if str(tg_id) not in arena_state["players"]:
                    slot = get_free_slot()
                    if slot == -1:
                        await websocket.send_text(json.dumps({"type": "error", "message": "Arena full"}))
                        continue
                    arena_state["players"][str(tg_id)] = {
                        "slot": slot, "name": first_name,
                        "hp": 100, "atk": 10, "ws": websocket
                    }
                else:
                    # Обновить ws при реконнект
                    arena_state["players"][str(tg_id)]["ws"] = websocket
                await broadcast()

            # — добавить HP или ATK
            elif t == "arena_stat":
                stat = msg.get("stat")
                p = arena_state["players"].get(str(tg_id))
                if p:
                    if stat == "hp":  p["hp"]  = min(p["hp"]  + 20, 500)
                    if stat == "atk": p["atk"] = min(p["atk"] + 5,  100)
                    # Атака босса при атаке
                    if stat == "atk":
                        total_atk = sum(pp["atk"] for pp in arena_state["players"].values())
                        arena_state["boss_hp"] = max(0, arena_state["boss_hp"] - p["atk"])
                    await broadcast()

            # — атака босса по игроку
            elif t == "arena_boss_attack":
                target_slot = msg.get("target_slot", 0)
                for p in arena_state["players"].values():
                    if p["slot"] == target_slot:
                        dmg = max(5, 30 - p["atk"] // 5)
                        p["hp"] = max(0, p["hp"] - dmg)
                await broadcast()

            # — ping
            elif t == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))

    except Exception:
        pass
    finally:
        arena_state["players"].pop(str(tg_id), None)
        await broadcast()
