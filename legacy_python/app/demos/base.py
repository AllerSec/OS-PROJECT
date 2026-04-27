"""
Shared helpers for the synchronization demos.

Each demo is a single async function `run(send, params)` where:
  - `send` is an async callable: `await send({"type": ..., ...})`
  - `params` is a dict of demo-specific options coming from the UI

We keep the helpers tiny on purpose: the demo code is the teaching material,
so it must stay readable.
"""

from __future__ import annotations

import asyncio
import threading
import time
from typing import Awaitable, Callable

# An async callback the demos use to push events to the WebSocket client.
Sender = Callable[[dict], Awaitable[None]]


def now_ms() -> float:
    """High-resolution monotonic time, in milliseconds."""
    return time.monotonic() * 1000.0


async def run_blocking(fn, *args, **kwargs):
    """
    Run a blocking function in a worker thread without freezing the event loop.

    All our demos use real OS threads (that's the whole point), so we hop off
    the event loop to drive them, then await results.
    """
    return await asyncio.to_thread(fn, *args, **kwargs)


class ThreadSafeBridge:
    """
    Lets a worker thread push events to an async sender without blocking it.

    The sender lives on the asyncio loop; threads cannot await on it directly.
    This bridge schedules a coroutine on the loop and returns immediately.
    """

    def __init__(self, send: Sender, loop: asyncio.AbstractEventLoop):
        self._send = send
        self._loop = loop

    def emit(self, event: dict) -> None:
        """Fire-and-forget. Safe to call from any thread."""
        asyncio.run_coroutine_threadsafe(self._send(event), self._loop)


def make_bridge(send: Sender) -> ThreadSafeBridge:
    """Helper used by demos: get the running loop and wrap the sender."""
    return ThreadSafeBridge(send, asyncio.get_running_loop())
