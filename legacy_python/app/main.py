"""
FastAPI entry point for the Linux Synchronization Tools for RTOS demo.

One WebSocket route, `/ws/{demo}`, drives any of the six demos. The
client sends a JSON message `{"action": "start", "params": {...}}` and
receives a stream of events until the demo finishes.

Run with:
    uvicorn app.main:app --reload
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.demos import REGISTRY

# Resolve paths relative to this file so the server works no matter where
# `uvicorn` is launched from.
ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = ROOT / "web"

app = FastAPI(title="Linux Synchronization Tools for RTOS")


@app.get("/")
async def index():
    """Serve the single-page app."""
    return FileResponse(WEB_DIR / "index.html")


@app.get("/health")
async def health():
    """Used by the UI's status pill to show the green dot."""
    return {"ok": True, "demos": list(REGISTRY.keys())}


@app.websocket("/ws/{demo}")
async def ws_demo(ws: WebSocket, demo: str):
    """Run one demo and stream its events to the client."""
    await ws.accept()

    runner = REGISTRY.get(demo)
    if runner is None:
        await ws.send_json({"type": "error", "message": f"unknown demo: {demo}"})
        await ws.close()
        return

    try:
        msg = await ws.receive_json()
    except WebSocketDisconnect:
        return

    if msg.get("action") != "start":
        await ws.send_json({"type": "error",
                            "message": "expected {'action': 'start'}"})
        await ws.close()
        return

    params = msg.get("params") or {}

    async def send(event: dict) -> None:
        try:
            await ws.send_json(event)
        except Exception:
            # Client disconnected mid-run; ignore so the worker thread
            # can wind down naturally.
            pass

    try:
        await runner(send, params)
    except Exception as exc:  # pragma: no cover — demo crashes are visible in UI
        await send({"type": "error", "message": str(exc)})
    finally:
        try:
            await ws.close()
        except Exception:
            pass


# Static files come last so the explicit routes above win.
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")
