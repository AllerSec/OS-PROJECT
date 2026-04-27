/* Demo 3 — Producer / Consumer.
 *
 * Bounded buffer with two semaphores ("empty", "full") plus a mutex.
 * Producer waits when the buffer is full; consumer waits when empty.
 *
 * We simulate the two threads with cooperative async/await. The semaphore
 * itself is a real, correctly-implemented counting semaphore — the same
 * algorithm as Linux POSIX semaphores.
 */

class Semaphore {
  constructor(value) { this.value = value; this.waiters = []; }
  async acquire() {
    if (this.value > 0) { this.value -= 1; return; }
    await new Promise((res) => this.waiters.push(res));
  }
  release() {
    if (this.waiters.length > 0) {
      const next = this.waiters.shift();
      next();
    } else {
      this.value += 1;
    }
  }
}

class Mutex {
  constructor() { this.locked = false; this.waiters = []; }
  async acquire() {
    if (!this.locked) { this.locked = true; return; }
    await new Promise((res) => this.waiters.push(res));
  }
  release() {
    if (this.waiters.length > 0) {
      const next = this.waiters.shift();
      next();
    } else {
      this.locked = false;
    }
  }
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

export async function run(params, send) {
  const bufSize = params?.buffer_size ?? 8;
  const nItems = params?.items ?? 24;
  const prodDelay = params?.producer_delay_ms ?? 140;
  const consDelay = params?.consumer_delay_ms ?? 240;

  const buffer = [];
  const empty = new Semaphore(bufSize);  // free slots
  const full = new Semaphore(0);         // ready items
  const mutex = new Mutex();

  const counts = { produced: 0, consumed: 0 };

  await send({ type: 'init', buffer_size: bufSize, n_items: nItems });

  function emitState(action, who, item) {
    send({
      type: 'tick', action, who, item,
      buffer: [...buffer],
      produced: counts.produced,
      consumed: counts.consumed,
    });
  }

  async function producer() {
    for (let i = 0; i < nItems; i++) {
      await empty.acquire();
      await mutex.acquire();
      buffer.push(i);
      counts.produced += 1;
      emitState('put', 'producer', i);
      mutex.release();
      full.release();
      await sleep(prodDelay + Math.random() * (prodDelay / 4));
    }
  }

  async function consumer() {
    for (let i = 0; i < nItems; i++) {
      await full.acquire();
      await mutex.acquire();
      const item = buffer.shift();
      counts.consumed += 1;
      emitState('take', 'consumer', item);
      mutex.release();
      empty.release();
      await sleep(consDelay + Math.random() * (consDelay / 4));
    }
  }

  await Promise.all([producer(), consumer()]);
  await send({ type: 'done' });
}
