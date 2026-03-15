import aiosqlite
import json
import os
from backend.game.models import Player

DB_PATH = os.getenv("DB_PATH", "game.db")


class Repository:
    async def init(self):
        from backend.db.init_db import init_db
        await init_db()

    async def get_or_create(self, tg_id: int, first_name: str) -> Player:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT tg_id, first_name, score, data FROM players WHERE tg_id = ?",
                (tg_id,)
            ) as cursor:
                row = await cursor.fetchone()

            if row:
                return Player(
                    tg_id=row[0],
                    first_name=row[1],
                    score=row[2],
                    data=json.loads(row[3])
                )
            else:
                await db.execute(
                    "INSERT INTO players (tg_id, first_name, score, data) VALUES (?, ?, 0, '{}')",
                    (tg_id, first_name)
                )
                await db.commit()
                return Player(tg_id=tg_id, first_name=first_name)

    async def save(self, player: Player):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE players SET score = ?, data = ? WHERE tg_id = ?",
                (player.score, json.dumps(player.data), player.tg_id)
            )
            await db.commit()
