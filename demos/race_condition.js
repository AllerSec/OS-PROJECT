/* Demo 1 — Race condition.
 *
 * Two real Web Workers share a SharedArrayBuffer. We run two passes:
 *   (a) without any synchronization — the count is wrong.
 *   (b) with an Atomics-based mutex   — the count is exact.
 *
 * Atomics.wait / Atomics.notify are the JS equivalent of Linux futex(2).
 */

const ITERATIONS = 60_000;

function spawnPair(mode, iterations) {
  return new Promise((resolve) => {
    const sab = new SharedArrayBuffer(3 * 4);   // 3 × Int32
    const view = new Int32Array(sab);
    view[0] = 0; view[1] = 0; view[2] = 0;

    const w1 = new Worker('demos/worker_counter.js');
    const w2 = new Worker('demos/worker_counter.js');
    let returned = 0;
    let totalElapsed = 0;

    function onDone(e) {
      returned += 1;
      totalElapsed = Math.max(totalElapsed, e.data.elapsed);
      if (returned === 2) {
        w1.terminate(); w2.terminate();
        resolve({
          actual: view[0],
          expected: iterations * 2,
          elapsedMs: totalElapsed,
        });
      }
    }
    w1.onmessage = onDone;
    w2.onmessage = onDone;

    w1.postMessage({ sab, iterations, mode, threadId: 1 });
    w2.postMessage({ sab, iterations, mode, threadId: 2 });
  });
}

export async function run(params, send) {
  const iterations = params?.iterations ?? ITERATIONS;

  await send({ type: 'phase', label: 'Without mutex (broken)' });
  const unsafe = await spawnPair('unsafe', iterations);
  await send({
    type: 'result', variant: 'unsafe',
    expected: unsafe.expected,
    actual: unsafe.actual,
    lost: unsafe.expected - unsafe.actual,
    elapsed_ms: Math.round(unsafe.elapsedMs * 10) / 10,
  });

  await send({ type: 'phase', label: 'With mutex (correct)' });
  const safe = await spawnPair('mutex', iterations);
  await send({
    type: 'result', variant: 'safe',
    expected: safe.expected,
    actual: safe.actual,
    lost: safe.expected - safe.actual,
    elapsed_ms: Math.round(safe.elapsedMs * 10) / 10,
  });

  await send({ type: 'done' });
}
