"""
Demo 4 — Readers / Writers

What it shows:
  Many threads can read at the same time, but a writer needs the resource
  to itself. This is what `pthread_rwlock_t` does on Linux.

We implement a writer-priority RWLock so readers cannot starve a waiting
writer (a common bug in naive readers-writers code).

Why it matters in RTOS:
  Configuration tables, sensor caches, routing tables — all read-heavy,
  occasionally written. A plain mutex would serialize readers and waste
  parallelism.
"""

import asyncio
import random
import threading
import time

from .base import Sender, make_bridge


class RWLock:
    """Writer-priority read-write lock."""

    def __init__(self):
        self._cond = threading.Condition(threading.Lock())
        self._readers = 0
        self._writer = False
        self._waiting_writers = 0

    def acquire_read(self) -> None:
        with self._cond:
            while self._writer or self._waiting_writers > 0:
                self._cond.wait()
            self._readers += 1

    def release_read(self) -> None:
        with self._cond:
            self._readers -= 1
            if self._readers == 0:
                self._cond.notify_all()

    def acquire_write(self) -> None:
        with self._cond:
            self._waiting_writers += 1
            while self._writer or self._readers > 0:
                self._cond.wait()
            self._waiting_writers -= 1
            self._writer = True

    def release_write(self) -> None:
        with self._cond:
            self._writer = False
            self._cond.notify_all()


def _run(bridge, n_readers: int, n_writers: int, duration_s: float) -> None:
    lock = RWLock()
    states: dict[str, str] = {}
    counts: dict[str, int] = {"reads": 0, "writes": 0}
    state_lock = threading.Lock()

    stop_at = time.monotonic() + duration_s

    def emit():
        bridge.emit({
            "type": "tick",
            "states": dict(states),
            "reads": counts["reads"],
            "writes": counts["writes"],
        })

    def set_state(name: str, value: str) -> None:
        with state_lock:
            states[name] = value
        emit()

    def reader(name: str):
        set_state(name, "idle")
        while time.monotonic() < stop_at:
            time.sleep(random.uniform(0.05, 0.2))
            set_state(name, "waiting")
            lock.acquire_read()
            try:
                set_state(name, "reading")
                time.sleep(random.uniform(0.1, 0.3))
                with state_lock:
                    counts["reads"] += 1
            finally:
                lock.release_read()
                set_state(name, "idle")

    def writer(name: str):
        set_state(name, "idle")
        while time.monotonic() < stop_at:
            time.sleep(random.uniform(0.4, 0.8))
            set_state(name, "waiting")
            lock.acquire_write()
            try:
                set_state(name, "writing")
                time.sleep(random.uniform(0.15, 0.3))
                with state_lock:
                    counts["writes"] += 1
            finally:
                lock.release_write()
                set_state(name, "idle")

    threads = []
    for i in range(n_readers):
        threads.append(threading.Thread(target=reader, args=(f"R{i + 1}",)))
    for i in range(n_writers):
        threads.append(threading.Thread(target=writer, args=(f"W{i + 1}",)))

    for t in threads:
        t.start()
    for t in threads:
        t.join()


async def run(send: Sender, params: dict) -> None:
    n_readers = int(params.get("readers", 4))
    n_writers = int(params.get("writers", 1))
    duration_s = float(params.get("duration_s", 8))
    bridge = make_bridge(send)

    await send({
        "type": "init",
        "readers": n_readers,
        "writers": n_writers,
    })
    await asyncio.to_thread(_run, bridge, n_readers, n_writers, duration_s)
    await send({"type": "done"})
