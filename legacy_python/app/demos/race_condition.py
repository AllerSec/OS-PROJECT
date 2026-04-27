"""
Demo 1 — Race Condition

What it shows:
  Two threads each try to increment the same counter many times. Without a
  lock, some increments are lost because `counter += 1` is not atomic in
  Python (it is read-modify-write at the bytecode level under free-threaded
  builds, and the GIL release granularity still allows interleavings here
  via explicit yields).

Why it matters in RTOS:
  Race conditions corrupt shared state silently. Real-time tasks share
  buffers, hardware registers, and counters; lost updates can crash a
  control loop or, worse, look fine in testing and fail in production.
"""

import threading
import time

from .base import Sender, make_bridge


# We force the race by using a small sleep inside the increment so the
# scheduler reliably switches threads mid-update. A pure `+=` works on
# free-threaded Python but is hard to reproduce on standard CPython.
def _do_increments(counter_ref: list, lock, n: int, use_lock: bool) -> None:
    for _ in range(n):
        if use_lock:
            with lock:
                # Read, modify, write. Two threads inside this block at the
                # same time would both read the same value and one update
                # would be lost.
                v = counter_ref[0]
                counter_ref[0] = v + 1
        else:
            v = counter_ref[0]
            # Yield the CPU on purpose so the other thread can squeeze in
            # between the read and the write — this is what a real race
            # looks like, just sped up so you can see it in 1 second.
            time.sleep(0)
            counter_ref[0] = v + 1


def _experiment(n_per_thread: int, use_lock: bool) -> dict:
    counter_ref = [0]
    lock = threading.Lock()
    threads = [
        threading.Thread(target=_do_increments,
                         args=(counter_ref, lock, n_per_thread, use_lock))
        for _ in range(2)
    ]
    t0 = time.perf_counter()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    expected = n_per_thread * 2
    actual = counter_ref[0]
    return {
        "expected": expected,
        "actual": actual,
        "lost": expected - actual,
        "elapsed_ms": round(elapsed_ms, 1),
    }


async def run(send: Sender, params: dict) -> None:
    """
    Run two passes back-to-back: first without a lock, then with one.
    The UI shows both side-by-side so the difference is obvious.
    """
    n = int(params.get("iterations", 50_000))
    bridge = make_bridge(send)

    # Pass 1 — no lock
    await send({"type": "phase", "label": "Without mutex (broken)"})
    unsafe = await _run_in_thread(_experiment, n, False)
    await send({"type": "result", "variant": "unsafe", **unsafe})

    # Pass 2 — with lock
    await send({"type": "phase", "label": "With mutex (correct)"})
    safe = await _run_in_thread(_experiment, n, True)
    await send({"type": "result", "variant": "safe", **safe})

    await send({"type": "done"})


async def _run_in_thread(fn, *args):
    import asyncio
    return await asyncio.to_thread(fn, *args)
