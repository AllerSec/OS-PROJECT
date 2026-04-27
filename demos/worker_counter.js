/* Worker for demos 1 (race condition) and 2 (mutex vs spinlock).
 *
 * Receives a SharedArrayBuffer with this layout (Int32Array):
 *   [0] counter           — the shared variable
 *   [1] mutex (futex)     — 0 = unlocked, 1 = locked
 *   [2] spin flag         — 0 = unlocked, 1 = locked
 *
 * The main thread tells us which lock mode to use.
 *
 * Atomics.compareExchange and Atomics.wait/notify are real lock-free
 * primitives — the same idea as Linux futex(2).
 */

self.onmessage = (e) => {
  const { sab, iterations, mode, threadId } = e.data;
  const view = new Int32Array(sab);
  const COUNTER = 0, MUTEX = 1, SPIN = 2;

  function mutexLock() {
    // Try fast path first.
    while (Atomics.compareExchange(view, MUTEX, 0, 1) !== 0) {
      // Slow path — sleep until notified.
      Atomics.wait(view, MUTEX, 1);
    }
  }
  function mutexUnlock() {
    Atomics.store(view, MUTEX, 0);
    Atomics.notify(view, MUTEX, 1);
  }

  function spinLock() {
    while (Atomics.compareExchange(view, SPIN, 0, 1) !== 0) {
      // pure busy-wait, burning CPU
    }
  }
  function spinUnlock() {
    Atomics.store(view, SPIN, 0);
  }

  const t0 = performance.now();

  if (mode === 'unsafe') {
    // No lock. Two workers racing on the same counter: lost updates.
    for (let i = 0; i < iterations; i++) {
      const v = view[COUNTER];      // plain (non-atomic) read
      // Tiny burn to widen the race window.
      let x = 0; for (let k = 0; k < 50; k++) x = (x + k) | 0;
      view[COUNTER] = v + 1;        // plain write
    }
  } else if (mode === 'mutex') {
    for (let i = 0; i < iterations; i++) {
      mutexLock();
      view[COUNTER] += 1;
      mutexUnlock();
    }
  } else if (mode === 'spinlock') {
    for (let i = 0; i < iterations; i++) {
      spinLock();
      view[COUNTER] += 1;
      spinUnlock();
    }
  }

  const elapsed = performance.now() - t0;
  self.postMessage({ threadId, elapsed });
};
