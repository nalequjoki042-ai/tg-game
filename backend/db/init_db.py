import aiosqlite
import os

DB_PATH = os.getenv("DB_PATH", "game.db")


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS players (
                tg_id     INTEGER PRIMARY KEY,
                first_name TEXT NOT NULL,
                score     INTEGER DEFAULT 0,
                data      TEXT DEFAULT '{}'
            )
        """)
        await db.commit()
    print("[DB] Tables ready")
