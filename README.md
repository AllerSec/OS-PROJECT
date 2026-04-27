# Obsidian Lab — Linux Synchronization Tools for RTOS

An interactive web app that **demonstrates live**, in your browser, the core
synchronization tools used in Linux real-time systems: mutex, spinlock,
semaphores, read-write locks, deadlock, and priority inversion.

> Real-Time Operating Systems coursework, 2025–2026.
> Single-page app · liquid-glass dark UI · responsive (web + mobile).
> 100 % static — runs entirely in your browser, deploys to **GitHub Pages**.

![status](https://img.shields.io/badge/status-ready-39FFB0?style=flat-square)
![github_pages](https://img.shields.io/badge/github-pages-5BE0FF?style=flat-square)
![license](https://img.shields.io/badge/license-MIT-FFB547?style=flat-square)

---

## Live demo

🔗 **<https://allersec.github.io/OS-PROJECT/>**

Repository: <https://github.com/AllerSec/OS-PROJECT>

Every push to `main` triggers `.github/workflows/pages.yml`, which redeploys
the site automatically.

---

## What is inside

Six interactive demos. Click **Run** on any card and watch real concurrent
code execute in your browser, with explanations in plain English.

| # | Demo                  | Concept                                        | How |
|---|-----------------------|-------------------------------------------------|-----|
| 1 | Race condition        | Mutex prevents lost updates                     | Real **Web Workers** + `SharedArrayBuffer` + `Atomics` |
| 2 | Mutex vs spinlock     | Sleeping vs busy-waiting locks                  | `Atomics.wait/notify` vs `Atomics.compareExchange` busy-loop |
| 3 | Producer / consumer   | Bounded buffer with semaphores                  | Counting semaphore + mutex |
| 4 | Readers / writers     | RW-lock with writer priority                    | Custom RWLock |
| 5 | Deadlock              | Cycle of waits + global lock-order fix          | Two mutexes, abort signal |
| 6 | Priority inversion    | The bug + the priority-inheritance fix          | Cooperative scheduler |

`Atomics.wait/notify` are the JS equivalent of Linux `futex(2)` — the
same primitive used inside `pthread_mutex_t`. Demo 1 and 2 are real
multi-threaded code, not simulations.

---

## Run it locally

You only need **Python 3** for the local dev server (it sets the
COOP/COEP headers needed for `SharedArrayBuffer`).

```bash
python serve_dev.py
# open http://localhost:8000
```

That is all. No build step, no Node, no database, no dependencies to
install.

> The local dev server adds `Cross-Origin-Opener-Policy: same-origin` and
> `Cross-Origin-Embedder-Policy: require-corp`. On GitHub Pages those
> headers are added by a tiny client-side service worker
> (`docs/coi-serviceworker.js`) so the site works the same way without
> any server config.

---

## Deploy to GitHub Pages

1. Push this repo to GitHub.
2. **Settings → Pages → Build and deployment → Source: GitHub Actions**.
3. Push to `main` (or trigger the workflow manually). Done.

The workflow uploads the `docs/` folder as the artifact and deploys it.
Your site will be live at
`https://<user>.github.io/<repo>/` within a couple of minutes.

---

## How it works

```
┌──────────────────────────────────────────────────────────────┐
│ Browser (zero backend)                                       │
│                                                              │
│  index.html  ──►  app.js  ──►  demos/*.js                    │
│                                                              │
│  Demo 1 & 2 spawn Web Workers; the workers share a           │
│  SharedArrayBuffer and synchronize with Atomics.wait/notify  │
│  (the same idea as Linux futex(2)).                          │
│                                                              │
│  Demos 3-6 run cooperatively in the main thread with         │
│  async/await — same algorithms, simpler to read.             │
│                                                              │
│  COOP+COEP headers (needed for SharedArrayBuffer) are        │
│  installed by coi-serviceworker.js on the client side.       │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

- **Frontend**: HTML + Tailwind-style custom CSS + Vanilla JS + Chart.js
  (CDN). The CSS is the only place where the look lives — open
  `docs/styles.css` to see the liquid-glass design system.
- **Concurrency**: real Web Workers and Atomics for race-condition / mutex
  / spinlock demos; cooperative async for producer-consumer,
  readers-writers, deadlock, and priority inversion.

---

## Project layout

```
PROJECT/
├── docs/                         ← GitHub Pages root
│   ├── index.html                six demo cards in one page
│   ├── styles.css                liquid glass + dark theme
│   ├── app.js                    panel controllers (ES modules)
│   ├── coi-serviceworker.js      enables SharedArrayBuffer on Pages
│   ├── .nojekyll                 disable Jekyll processing
│   ├── specs/                    design spec
│   └── demos/
│       ├── worker_counter.js     Web Worker for demos 1+2
│       ├── race_condition.js
│       ├── mutex_vs_spinlock.js
│       ├── producer_consumer.js
│       ├── readers_writers.js
│       ├── deadlock.js
│       └── priority_inversion.js
├── presentation/                 short PowerPoint
│   ├── ObsidianLab.pptx
│   ├── screenshots/              one per demo + mobile + hero
│   ├── capture.py                generates screenshots from a live page
│   └── build_pptx.py             builds the deck
├── legacy_python/                bonus: same demos as a FastAPI server
│   └── app/                      (run with uvicorn — see legacy_python/README is in main)
├── .github/workflows/pages.yml   auto-deploy on push to main
├── serve_dev.py                  local dev server with COOP/COEP
└── README.md                     this file
```

---

## Bonus: the original Python backend version

There is also a **server-side Python implementation** in `legacy_python/`
that uses real OS threads (`threading.Lock`, `threading.Semaphore`, etc.)
and streams results to the same UI over WebSockets. It is not used on
GitHub Pages but is included to show the same algorithms in two languages.

```bash
pip install -r legacy_python/requirements.txt
uvicorn legacy_python.app.main:app --reload
# the static UI is in docs/, but you would need to point it at the WS URL
```

---

## Troubleshooting

**"limited · no SAB" on the status pill.** The browser does not have
`SharedArrayBuffer`. Demos 1 and 2 will fall back; demos 3-6 still work.
On GitHub Pages, refresh the page once after the first visit so the
service worker can take control.

**Port 8000 is busy locally.** Edit `PORT = 8000` in `serve_dev.py`.

**The deadlock demo seems stuck.** That is the point — it deadlocks. A
2.5 s watchdog gives up and reports `DEADLOCKED`. Click **Fix** for the
working version.

---

## Course

**Subject:** Real-Time Operating Systems
**Year:** 2025–2026
**Topic:** Implementation of synchronization tools in Linux for RTOS

---

## License

MIT.
