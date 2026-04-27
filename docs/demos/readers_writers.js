/* Demo 4 — Readers / Writers.
 *
 * Many readers may share the resource. Writers are exclusive.
 * Implementation uses writer-priority so writers cannot starve.
 */

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

class RWLock {
  constructor() {
    this.readers = 0;
    this.writer = false;
    this.waitingWriters = 0;
    this.waiters = [];
  }
  _wake() {
    // wake everyone; each will re-check its condition
    const w = this.waiters.splice(0);
    for (const r of w) r();
  }
  async _wait() { await new Promise((r) => this.waiters.push(r)); }

  async acquireRead() {
    while (this.writer || this.waitingWriters > 0) {
      await this._wait();
    }
    this.readers += 1;
  }
  releaseRead() {
    this.readers -= 1;
    if (this.readers === 0) this._wake();
  }
  async acquireWrite() {
    this.waitingWriters += 1;
    while (this.writer || this.readers > 0) {
      await this._wait();
    }
    this.waitingWriters -= 1;
    this.writer = true;
  }
  releaseWrite() {
    this.writer = false;
    this._wake();
  }
}

export async function run(params, send) {
  const nReaders = params?.readers ?? 4;
  const nWriters = params?.writers ?? 1;
  const durationMs = (params?.duration_s ?? 8) * 1000;

  const lock = new RWLock();
  const states = {};
  const counts = { reads: 0, writes: 0 };

  function emit() {
    send({ type: 'tick', states: { ...states },
           reads: counts.reads, writes: counts.writes });
  }
  function setState(name, value) { states[name] = value; emit(); }

  await send({ type: 'init', readers: nReaders, writers: nWriters });

  const stopAt = performance.now() + durationMs;

  async function reader(name) {
    setState(name, 'idle');
    while (performance.now() < stopAt) {
      await sleep(50 + Math.random() * 150);
      setState(name, 'waiting');
      await lock.acquireRead();
      setState(name, 'reading');
      await sleep(100 + Math.random() * 200);
      counts.reads += 1;
      lock.releaseRead();
      setState(name, 'idle');
    }
  }
  async function writer(name) {
    setState(name, 'idle');
    while (performance.now() < stopAt) {
      await sleep(400 + Math.random() * 400);
      setState(name, 'waiting');
      await lock.acquireWrite();
      setState(name, 'writing');
      await sleep(150 + Math.random() * 150);
      counts.writes += 1;
      lock.releaseWrite();
      setState(name, 'idle');
    }
  }

  const tasks = [];
  for (let i = 0; i < nReaders; i++) tasks.push(reader(`R${i + 1}`));
  for (let i = 0; i < nWriters; i++) tasks.push(writer(`W${i + 1}`));
  await Promise.all(tasks);
  await send({ type: 'done' });
}
