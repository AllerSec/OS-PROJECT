"""
Demo 6 — Priority Inversion (and Priority Inheritance fix)

What it shows:
  Three tasks: Low, Medium, High priority.
    1. Low grabs a shared mutex.
    2. High wakes up and waits for that mutex.
    3. Medium becomes runnable and pre-empts Low.
       → Now High is waiting for Low which is waiting for Medium to give
         up the CPU. The high-priority task is held up by an unrelated
         medium-priority one. This is the bug.

Fix (Priority Inheritance):
  When High blocks on a mutex held by Low, Low temporarily inherits
  High's priority. Medium can no longer pre-empt it; Low finishes the
  critical section quickly and releases the mutex.

Note on portability:
  Real OS-level priority inheritance needs `PTHREAD_PRIO_INHERIT` on
  Linux. We model the *effect* with a cooperative scheduler so the
  difference is visible on any platform. The web UI shows a banner
  reminding the user that this is an emulation.
"""

import asyncio
import threading
import time

from .base import Sender, make_bridge


def _run(bridge, use_pi: bool, duration_ms: int = 1500) -> dict:
    timeline: list[dict] = []
    timeline_lock = threading.Lock()
    start = time.monotonic()

    def now():
        return (time.monotonic() - start) * 1000.0

    def log(thread: str, event: str):
        with timeline_lock:
            timeline.append({
                "t": round(now(), 1),
                "thread": thread,
                "event": event,
            })
        bridge.emit({
            "type": "tick",
            "thread": thread,
            "event": event,
            "t": round(now(), 1),
            "use_pi": use_pi,
        })

    # Cooperative scheduler. A "running" flag picks which thread the
    # virtual CPU is on. Each thread checks every step whether it should
    # yield. This lets us reproduce inversion deterministically.
    cpu_holder = ["low"]
    sched_lock = threading.Lock()
    mutex_held_by: list = [None]

    # If priority inheritance is on, the CPU prefers whoever holds the
    # mutex when High is waiting on it.
    high_waiting = [False]

    def should_run(name: str, priority: int) -> bool:
        with sched_lock:
            if use_pi and high_waiting[0] and mutex_held_by[0] == name:
                # Inherited high priority.
                return True
            # Plain priority scheduling: highest runnable wins.
            return cpu_holder[0] == name

    def claim_cpu(name: str) -> None:
        with sched_lock:
            cpu_holder[0] = name

    def low():
        log("Low", "start")
        # Acquire the mutex.
        with sched_lock:
            mutex_held_by[0] = "Low"
        log("Low", "mutex acquired")
        # Simulate critical section work in small slices.
        slices = 12
        for i in range(slices):
            # Wait until we are scheduled.
            while not should_run("Low", 1):
                time.sleep(0.005)
            log("Low", f"work {i + 1}/{slices}")
            time.sleep(0.04)
        with sched_lock:
            mutex_held_by[0] = None
        log("Low", "mutex released")
        log("Low", "done")

    def medium():
        time.sleep(0.05)  # arrives slightly after Low
        log("Medium", "ready")
        # Medium would pre-empt Low under plain priority scheduling.
        if not use_pi:
            claim_cpu("Medium")
        slices = 10
        for i in range(slices):
            while not should_run("Medium", 2):
                time.sleep(0.005)
            log("Medium", f"cpu burn {i + 1}/{slices}")
            time.sleep(0.04)
        log("Medium", "done")
        # Hand the CPU back to Low so it can finish.
        claim_cpu("Low")

    def high():
        time.sleep(0.12)  # arrives after Low has the mutex
        log("High", "ready")
        log("High", "wait for mutex")
        with sched_lock:
            high_waiting[0] = True
        # If PI on, the holder (Low) gets the CPU now.
        if use_pi:
            claim_cpu("Low")
        # Spin until the mutex is free.
        while True:
            with sched_lock:
                if mutex_held_by[0] is None:
                    mutex_held_by[0] = "High"
                    high_waiting[0] = False
                    break
            time.sleep(0.01)
        claim_cpu("High")
        log("High", "mutex acquired")
        # Tiny critical section, then release.
        time.sleep(0.05)
        with sched_lock:
            mutex_held_by[0] = None
        log("High", "done")

    threads = [
        threading.Thread(target=low, daemon=True),
        threading.Thread(target=medium, daemon=True),
        threading.Thread(target=high, daemon=True),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=duration_ms / 1000.0 * 3)

    high_done_at = next(
        (e["t"] for e in timeline if e["thread"] == "High" and e["event"] == "done"),
        None,
    )
    high_ready_at = next(
        (e["t"] for e in timeline if e["thread"] == "High" and e["event"] == "ready"),
        None,
    )
    return {
        "use_pi": use_pi,
        "high_latency_ms": (round(high_done_at - high_ready_at, 1)
                            if high_done_at is not None and high_ready_at is not None
                            else None),
        "timeline": timeline,
    }


async def run(send: Sender, params: dict) -> None:
    bridge = make_bridge(send)

    await send({"type": "phase", "label": "Without priority inheritance"})
    bad = await asyncio.to_thread(_run, bridge, False)
    await send({"type": "result", "variant": "without_pi",
                "high_latency_ms": bad["high_latency_ms"]})

    await send({"type": "phase", "label": "With priority inheritance"})
    good = await asyncio.to_thread(_run, bridge, True)
    await send({"type": "result", "variant": "with_pi",
                "high_latency_ms": good["high_latency_ms"]})

    await send({"type": "done"})
