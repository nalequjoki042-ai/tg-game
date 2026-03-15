import os
from pathlib import Path
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

from backend.db.init_db import init_db
from backend.db.repository import Repository
from backend.api.ws_handler import handle

load_dotenv()

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[SERVER] Starting up...")
    await init_db()
    yield
    print("[SERVER] Shutting down...")


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTMLResponse(content=(FRONTEND_DIR / "index.html").read_text(encoding="utf-8"))


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.3.0-leaderboard"}


@app.get("/leaderboard")
async def leaderboard():
    repo = Repository()
    await repo.init()
    return await repo.get_leaderboard()


@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    tg_id: int = Query(default=0),
    first_name: str = Query(default="Guest")
):
    await websocket.accept()
    print(f"[WS] Player connected: {first_name} ({tg_id})")
    await handle(websocket, tg_id, first_name)
