import os
from pathlib import Path
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

load_dotenv()

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[SERVER] Starting up...")
    yield
    print("[SERVER] Shutting down...")


app = FastAPI(lifespan=lifespan)

app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
async def index():
    html_path = FRONTEND_DIR / "index.html"
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0-scaffold"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print(f"[WS] Client connected: {websocket.client}")
    try:
        while True:
            data = await websocket.receive_json()
            print(f"[WS] Received: {data}")
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong", "echo": data})
            else:
                await websocket.send_json({"type": "error", "message": "unknown type"})
    except WebSocketDisconnect:
        print(f"[WS] Client disconnected")
