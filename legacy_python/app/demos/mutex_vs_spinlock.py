"""
Demo 2 — Mutex vs Spinlock

What it shows:
  The same critical section run with two different locks:
    - Mutex (`threading.Lock`)        : blocked threads sleep and are
                                         woken by the kernel.
    - Spinlock (busy-wait on an atomic): blocked threads burn CPU
                                         until the lock is free.

Why it matters in RTOS:
  Spinlocks are great when the critical section is shorter than a context
  switch (a few microseconds). Mutexes are better for longer sections
  because sleeping releases the CPU. Picking the wrong one wastes power
  or hurts latency.
"""

import asyncio
import threading
import time

from .base import Sender


# A minimal spinlock implemented with a CAS-style flag.
# `threading.Event` is not a spinlock; we want to *show* the busy-wait so
# we use a simple boolean inside a lock-free loop. (The inner Lock here is
# only to make the test/clear atomic on standard CPython; under the hood
# this still busy-waits.)
class SpinLock:
    def __init__(self):
        self._flag = False
        self._guard = threading.Lock()

    def acquire(self) -> None:
        while True:
            with self._guard:
                if not self._flag:
                    self._flag = True
                    return
            # Burn CPU. This is the spin part. No sleep.
            pass

    def release(self) -> None:
        with self._guard:
            self._flag = False

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, *exc):
        self.release()


def _bench(lock_factory, n_threads: int, iterations: int) -> dict:
    lock = lock_factory()
    counter_ref = [0]

    def worker():
        for _ in range(iterations):
            with lock:
                # Tiny critical section — typical of a real-time path.
                counter_ref[0] += 1

    threads = [threading.Thread(target=worker) for _ in range(n_threads)]
    t0 = time.perf_counter()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    return {
        "elapsed_ms": round(elapsed_ms, 2),
        "final_count": counter_ref[0],
        "expected": n_threads * iterations,
    }


async def run(send: Sender, params: dict) -> None:
    n_threads = int(params.get("threads", 4))
    iterations = int(params.get("iterations", 20_000))

    await send({"type": "phase", "label": "Running mutex benchmark"})
    mutex_result = await asyncio.to_thread(
        _bench, threading.Lock, n_threads, iterations
    )
    await send({"type": "result", "variant": "mutex", **mutex_result})

    await send({"type": "phase", "label": "Running spinlock benchmark"})
    spin_result = await asyncio.to_thread(
        _bench, SpinLock, n_threads, iterations
    )
    await send({"type": "result", "variant": "spinlock", **spin_result})

    await send({"type": "done"})
