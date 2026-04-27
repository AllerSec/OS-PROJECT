/* Demo 2 — Mutex vs Spinlock.
 *
 * Same workload, two locking strategies:
 *   - mutex     : Atomics.wait / Atomics.notify  (sleeps when blocked)
 *   - spinlock  : compareExchange busy-wait      (burns CPU until free)
 *
 * Linux uses both. Spinlocks are faster for very short critical sections
 * (< context switch cost), mutexes are better when the section is long.
 */

const THREADS = 4;
const ITERATIONS = 30_000;

function bench(mode, nThreads, iterations) {
  return new Promise((resolve) => {
    const sab = new SharedArrayBuffer(3 * 4);
    const view = new Int32Array(sab);
    view[0] = 0; view[1] = 0; view[2] = 0;

    const workers = [];
    let returned = 0;
    let maxElapsed = 0;
    const t0 = performance.now();

    function onDone(e) {
      returned += 1;
      maxElapsed = Math.max(maxElapsed, e.data.elapsed);
      if (returned === nThreads) {
        for (const w of workers) w.terminate();
        const wall = performance.now() - t0;
        resolve({
          elapsed_ms: Math.round(wall * 100) / 100,
          worker_max_ms: Math.round(maxElapsed * 100) / 100,
          final_count: view[0],
          expected: iterations * nThreads,
        });
      }
    }

    for (let i = 0; i < nThreads; i++) {
      const w = new Worker('demos/worker_counter.js');
      w.onmessage = onDone;
      workers.push(w);
      w.postMessage({ sab, iterations, mode, threadId: i + 1 });
    }
  });
}

export async function run(params, send) {
  const nThreads = params?.threads ?? THREADS;
  const iterations = params?.iterations ?? ITERATIONS;

  await send({ type: 'phase', label: 'Running mutex benchmark' });
  const mu = await bench('mutex', nThreads, iterations);
  await send({ type: 'result', variant: 'mutex', ...mu });

  await send({ type: 'phase', label: 'Running spinlock benchmark' });
  const sp = await bench('spinlock', nThreads, iterations);
  await send({ type: 'result', variant: 'spinlock', ...sp });

  await send({ type: 'done' });
}
