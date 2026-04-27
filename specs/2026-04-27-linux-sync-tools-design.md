# Linux Synchronization Tools for RTOS — Design Spec

**Date:** 2026-04-27
**Course:** Real-Time Operating Systems
**Topic:** Implementation of synchronization tools in Linux for RTOS
**Deliverable:** Interactive web app + README + short PowerPoint

## Goal

Build a single-page web application that explains and demonstrates, in real
time, the six fundamental synchronization mechanisms used in Linux for RTOS
work: race conditions, mutex vs spinlock, producer-consumer, readers-writers,
deadlock, and priority inversion. All explanations are written in simple
English so a non-native reader can follow along.

## Stack

| Layer | Technology | Rationale |
|---|---|---|
| Backend | Python 3.11 + FastAPI + `uvicorn` | Async + native WebSockets; one-command run |
| Concurrency | `threading`, `multiprocessing`, `queue` | POSIX-equivalent primitives, portable Win/Linux |
| Realtime | WebSocket (one socket per demo run) | Push results live to the UI |
| Frontend | HTML + Tailwind (CDN) + Vanilla JS + Chart.js | No build step, README stays simple |
| Aesthetic | Liquid glass on deep black | Apple Vision Pro / macOS Sequoia inspired |

## Aesthetic — "Obsidian Lab"

- **Background:** `#05060A` with a slow-moving cyan radial light (CSS only) and 2% schematic grid overlay
- **Glass panels:** `backdrop-filter: blur(28px) saturate(140%)`, white overlay at 4-6%, hairline border `rgba(255,255,255,0.08)`, inset highlight on top edge
- **Accents:** mint-cyan `#39FFB0` (healthy), amber `#FFB547` (warning), coral `#FF5C7A` (critical), violet `#8B7CFF` (info)
- **Fonts:** Geist (display + body) + JetBrains Mono (numbers, code) — both via Google Fonts / Vercel CDN
- **Motion:** 200-280ms ease-out for state changes; respects `prefers-reduced-motion`

## Layout

Single page with a sticky top bar (logo, server status, theme info) and a vertical stack of six demo cards. Each card has:

1. **Header** — title + one-sentence subtitle
2. **What is this?** collapsible — explains the problem in simple English
3. **Live visualization** — chart/animation specific to the demo
4. **Controls** — buttons to start/stop/configure
5. **Live numbers** — JetBrains Mono, tabular figures
6. **Code shown** — the snippet currently running, syntax highlighted

On mobile (≤640px) cards stack full-width with reduced blur (16px) for performance.

## The six demos

### 1. Race Condition
Two threads each increment a shared counter 200 000 times. Without a lock, the
final value is below 400 000 (lost updates). Toggle "Use mutex" — value becomes
exactly 400 000. Visualization: live counter + bar showing expected vs actual.

### 2. Mutex vs Spinlock
Same workload (short critical section), measured with `threading.Lock` (mutex,
sleeps when blocked) and a custom spinlock (`while not flag.compare_exchange`).
Visualization: bar chart comparing total time + CPU time. Shows that spinlocks
win for ultra-short critical sections at the cost of CPU.

### 3. Producer-Consumer
One producer, one consumer, bounded buffer of size 8. Uses `threading.Semaphore`
(empty/full) + mutex. Visualization: animated buffer slots filling and
emptying; live counters of produced/consumed items.

### 4. Readers-Writers
N readers + 1 writer using a custom RWLock (writer-priority). Visualization:
horizontal lane per thread showing R (reading) / W (writing) / · (idle); live
counts.

### 5. Deadlock
Two threads grab two locks in opposite order → hang. "Cause deadlock" button
triggers it (with a watchdog that cancels after 3s). "Fix" applies a global
lock-ordering rule. Visualization: two boxes (Thread A, Thread B) with which
lock each holds and which it waits for; arrows turn red on cycle.

### 6. Priority Inversion + PI mutex
Three threads (Low, Medium, High). Low holds a mutex; High waits for it;
Medium is CPU-bound and starves Low → High waits indirectly for Medium.
Toggle "Priority Inheritance" — Low inherits High's priority and finishes the
critical section quickly. Visualization: timeline (Gantt-style) showing each
thread's run intervals.

> Note on portability: real OS-level priority inheritance requires
> `PTHREAD_PRIO_INHERIT` (Linux). On Windows, we simulate the *effect* using
> Python thread scheduling and a yield-based emulation. The UI shows a banner
> "Real on Linux / Emulated on Windows" to keep this honest.

## Backend architecture

```
app/
  main.py                # FastAPI app, routes, WebSocket endpoint
  demos/
    __init__.py
    base.py              # DemoRunner ABC, WebSocket helpers
    race_condition.py
    mutex_vs_spinlock.py
    producer_consumer.py
    readers_writers.py
    deadlock.py
    priority_inversion.py
  static_files.py        # mount /web as static
  requirements.txt
```

- One WebSocket route: `/ws/{demo_name}`. The client sends `{"action": "start", "params": {...}}`, the server runs the demo in a background thread and pushes `{"type": "tick"|"event"|"done", ...}` events.
- Each demo exposes `start(params, send)` where `send` is an async callback. Demos run on `asyncio.to_thread` so concurrency primitives behave naturally.

## Frontend architecture

```
web/
  index.html             # all six panels
  styles.css             # liquid glass, animations, responsive
  app.js                 # router, WS client, panel controllers
  assets/                # SVG icons (Lucide) inlined
```

`app.js` exposes one `Demo(panelEl, name)` class per panel; each registers
its own start/stop button handlers and renders ticks. Chart.js is loaded
once via CDN.

## Run instructions (will go in README)

```bash
pip install -r app/requirements.txt
uvicorn app.main:app --reload
# open http://localhost:8000
```

## Acceptance criteria

- [ ] Server starts with `uvicorn app.main:app` and serves the page at `/`
- [ ] All six demos run and produce live updates over WebSocket
- [ ] Race condition demo shows lost updates without mutex, exact count with mutex
- [ ] Mutex/spinlock demo produces a comparable bar chart
- [ ] Producer-consumer animation tracks the real buffer state
- [ ] Readers-writers shows lane states matching thread state
- [ ] Deadlock demo hangs, watchdog recovers; "fix" version completes
- [ ] Priority inversion shows the effect; PI toggle resolves it
- [ ] Layout is usable on a 375px-wide viewport without horizontal scroll
- [ ] All on-screen explanations are A2-B1 English
- [ ] README is under one screen and works on a fresh Python install
- [ ] PowerPoint has ≤10 slides with one screenshot per demo

## Out of scope

- Authentication, persistence, multi-user
- Real C/POSIX bindings via ctypes (mentioned in spec, replaced by Python primitives for portability)
- Mobile app — the same web UI is responsive instead
- Tests beyond the manual acceptance criteria above (academic project, time-boxed)
