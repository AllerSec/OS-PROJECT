/* Demo 5 — Deadlock.
 *
 * Two threads, two locks, opposite acquisition order.
 *  - Broken: A grabs lock1 then lock2; B grabs lock2 then lock1 → cycle.
 *  - Fixed:  Both grab lock1 first, then lock2.
 *
 * A 2.5-second watchdog stops the broken run so the page does not hang.
 */

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

class Mutex {
  constructor() { this.locked = false; this.waiters = []; }
  async acquire(signal) {
    while (this.locked) {
      if (signal?.aborted) throw new Error('abort');
      await new Promise((res) => {
        this.waiters.push(res);
        if (signal) signal.addEventListener('abort', res, { once: true });
      });
    }
    this.locked = true;
  }
  release() {
    this.locked = false;
    if (this.waiters.length) {
      const r = this.waiters.shift(); r();
    }
  }
}

async function attempt(send, fix, timeoutMs) {
  const lock1 = new Mutex();
  const lock2 = new Mutex();
  const state = { A: 'idle', B: 'idle' };

  function emit() { send({ type: 'tick', state: { ...state }, fix }); }
  function setState(who, v) { state[who] = v; emit(); }

  const ctrl = new AbortController();
  const start = performance.now();

  async function threadA() {
    setState('A', 'want lock1');
    await lock1.acquire(ctrl.signal);
    setState('A', 'holds lock1');
    await sleep(50);
    setState('A', 'want lock2');
    await lock2.acquire(ctrl.signal);
    setState('A', 'holds 1+2');
    await sleep(50);
    lock2.release();
    lock1.release();
    setState('A', 'done');
  }
  async function threadB_broken() {
    setState('B', 'want lock2');
    await lock2.acquire(ctrl.signal);
    setState('B', 'holds lock2');
    await sleep(50);
    setState('B', 'want lock1');
    await lock1.acquire(ctrl.signal);   // hangs
    setState('B', 'holds 1+2');
    await sleep(50);
    lock1.release();
    lock2.release();
    setState('B', 'done');
  }
  async function threadB_fixed() {
    setState('B', 'want lock1');
    await lock1.acquire(ctrl.signal);
    setState('B', 'holds lock1');
    await sleep(50);
    setState('B', 'want lock2');
    await lock2.acquire(ctrl.signal);
    setState('B', 'holds 1+2');
    await sleep(50);
    lock2.release();
    lock1.release();
    setState('B', 'done');
  }

  const watchdog = sleep(timeoutMs).then(() => {
    ctrl.abort();
    return 'timeout';
  });

  const a = threadA().catch(() => {});
  const b = (fix ? threadB_fixed() : threadB_broken()).catch(() => {});

  const winner = await Promise.race([
    Promise.all([a, b]).then(() => 'done'),
    watchdog,
  ]);

  return {
    deadlocked: winner === 'timeout',
    elapsed_ms: Math.round((performance.now() - start) * 10) / 10,
  };
}

export async function run(params, send) {
  const fix = !!params?.fix;
  const timeout = (params?.timeout_s ?? 2.5) * 1000;
  await send({ type: 'phase', label: fix ? 'Fixed order' : 'Broken order' });
  const r = await attempt(send, fix, timeout);
  await send({ type: 'result', ...r });
  await send({ type: 'done' });
}
