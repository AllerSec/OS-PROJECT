"""
Demo 5 — Deadlock

What it shows:
  Two threads, two locks. Thread A grabs lock 1 then tries lock 2; Thread
  B grabs lock 2 then tries lock 1. They wait for each other forever.

Fix:
  Always acquire locks in the same global order. If both threads grab
  lock 1 first, no cycle can form.

Why it matters in RTOS:
  A real-time system that deadlocks is broken — the deadline is missed
  and there is no recovery. Order rules and lock hierarchies are how
  kernels avoid this.
"""

import asyncio
import threading
import time

from .base import Sender, make_bridge


def _attempt(bridge, fix: bool, timeout_s: float) -> dict:
    lock1 = threading.Lock()
    lock2 = threading.Lock()

    state = {"A": "idle", "B": "idle"}
    state_lock = threading.Lock()

    def set_state(who: str, value: str):
        with state_lock:
            state[who] = value
        bridge.emit({"type": "tick", "state": dict(state), "fix": fix})

    finished = threading.Event()

    def thread_a():
        set_state("A", "want lock1")
        lock1.acquire()
        set_state("A", "holds lock1")
        time.sleep(0.05)  # give B time to grab lock2
        set_state("A", "want lock2")
        # In FIX mode both threads also want lock1 first — but A already
        # has it, so this branch only happens on the broken version.
        lock2.acquire()
        set_state("A", "holds 1+2")
        time.sleep(0.05)
        lock2.release()
        lock1.release()
        set_state("A", "done")

    def thread_b_broken():
        set_state("B", "want lock2")
        lock2.acquire()
        set_state("B", "holds lock2")
        time.sleep(0.05)  # give A time to grab lock1
        set_state("B", "want lock1")
        lock1.acquire()           # ← will block forever vs A
        set_state("B", "holds 1+2")
        time.sleep(0.05)
        lock1.release()
        lock2.release()
        set_state("B", "done")

    def thread_b_fixed():
        # Same global order: lock1 first, lock2 second.
        set_state("B", "want lock1")
        lock1.acquire()
        set_state("B", "holds lock1")
        time.sleep(0.05)
        set_state("B", "want lock2")
        lock2.acquire()
        set_state("B", "holds 1+2")
        time.sleep(0.05)
        lock2.release()
        lock1.release()
        set_state("B", "done")

    target_b = thread_b_fixed if fix else thread_b_broken
    a = threading.Thread(target=thread_a, daemon=True)
    b = threading.Thread(target=target_b, daemon=True)
    a.start()
    b.start()

    start = time.monotonic()
    a.join(timeout=timeout_s)
    b.join(timeout=max(0.0, timeout_s - (time.monotonic() - start)))

    deadlocked = a.is_alive() or b.is_alive()
    return {
        "deadlocked": deadlocked,
        "elapsed_ms": round((time.monotonic() - start) * 1000.0, 1),
    }


async def run(send: Sender, params: dict) -> None:
    fix = bool(params.get("fix", False))
    timeout_s = float(params.get("timeout_s", 2.5))
    bridge = make_bridge(send)

    await send({"type": "phase", "label": "Fixed order" if fix else "Broken order"})
    result = await asyncio.to_thread(_attempt, bridge, fix, timeout_s)
    await send({"type": "result", **result})
    await send({"type": "done"})
