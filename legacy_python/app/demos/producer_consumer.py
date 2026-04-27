"""
Demo 3 — Producer / Consumer

What it shows:
  One producer thread fills a bounded buffer; one consumer thread drains
  it. They never touch the buffer at the same time and never overflow it.

How:
  Two semaphores plus a mutex.
    - `empty`  starts at BUFFER_SIZE — counts free slots.
    - `full`   starts at 0           — counts available items.
    - `mutex`  protects the buffer itself.

Why it matters in RTOS:
  This is the canonical pattern for any pipeline (sensor → processor,
  network → handler, ISR → task). Get it wrong and you either lose data
  or block forever.
"""

import asyncio
import random
import threading
import time

from .base import Sender, make_bridge


def _run(bridge, buffer_size: int, n_items: int, prod_delay_ms: int,
         cons_delay_ms: int) -> None:
    buffer: list = []
    empty = threading.Semaphore(buffer_size)
    full = threading.Semaphore(0)
    mutex = threading.Lock()

    produced = [0]
    consumed = [0]

    def emit_state(action: str, who: str, item=None) -> None:
        # Snapshot the buffer under lock (we may already hold it; this is
        # only for the tracer thread state).
        bridge.emit({
            "type": "tick",
            "action": action,
            "who": who,
            "item": item,
            "buffer": list(buffer),
            "produced": produced[0],
            "consumed": consumed[0],
        })

    def producer():
        for i in range(n_items):
            empty.acquire()
            with mutex:
                buffer.append(i)
                produced[0] += 1
                emit_state("put", "producer", i)
            full.release()
            time.sleep(prod_delay_ms / 1000.0 +
                      random.uniform(0, prod_delay_ms / 4000.0))

    def consumer():
        for _ in range(n_items):
            full.acquire()
            with mutex:
                item = buffer.pop(0)
                consumed[0] += 1
                emit_state("take", "consumer", item)
            empty.release()
            time.sleep(cons_delay_ms / 1000.0 +
                      random.uniform(0, cons_delay_ms / 4000.0))

    p = threading.Thread(target=producer)
    c = threading.Thread(target=consumer)
    p.start()
    c.start()
    p.join()
    c.join()


async def run(send: Sender, params: dict) -> None:
    buffer_size = int(params.get("buffer_size", 8))
    n_items = int(params.get("items", 30))
    prod_delay = int(params.get("producer_delay_ms", 120))
    cons_delay = int(params.get("consumer_delay_ms", 200))

    bridge = make_bridge(send)
    await send({
        "type": "init",
        "buffer_size": buffer_size,
        "n_items": n_items,
    })

    await asyncio.to_thread(_run, bridge, buffer_size, n_items,
                            prod_delay, cons_delay)
    await send({"type": "done"})
