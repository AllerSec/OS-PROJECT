/* Demo 6 — Priority Inversion (with Priority Inheritance fix).
 *
 * Three cooperative tasks: Low, Medium, High.
 *  - Low takes a mutex first.
 *  - High wakes up later and waits for the mutex.
 *  - Medium is CPU-bound and pre-empts Low under plain priority scheduling.
 *
 * Without PI: High waits for Low, which is starved by Medium → long latency.
 * With PI:    Low inherits High's priority while it holds the mutex; Medium
 *             cannot pre-empt it; High gets the mutex quickly.
 */

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function simulate(usePI, send) {
  const timeline = [];
  const start = performance.now();
  const t = () => Math.round((performance.now() - start) * 10) / 10;

  // Cooperative scheduler state.
  const sched = { holder: 'low', mutexHolder: null, highWaiting: false };

  function emit(thread, event) {
    const ev = { t: t(), thread, event, use_pi: usePI };
    timeline.push(ev);
    send({ type: 'tick', ...ev });
  }

  function shouldRun(name) {
    if (usePI && sched.highWaiting && sched.mutexHolder === name) return true;
    return sched.holder === name;
  }
  async function waitTurn(name) {
    while (!shouldRun(name)) await sleep(5);
  }
  function claim(name) { sched.holder = name; }

  async function low() {
    emit('Low', 'start');
    sched.mutexHolder = 'Low';
    emit('Low', 'mutex acquired');
    for (let i = 0; i < 12; i++) {
      await waitTurn('Low');
      emit('Low', `work ${i + 1}/12`);
      await sleep(40);
    }
    sched.mutexHolder = null;
    emit('Low', 'mutex released');
    emit('Low', 'done');
  }

  async function medium() {
    await sleep(50);
    emit('Medium', 'ready');
    if (!usePI) claim('Medium');
    for (let i = 0; i < 10; i++) {
      await waitTurn('Medium');
      emit('Medium', `cpu burn ${i + 1}/10`);
      await sleep(40);
    }
    emit('Medium', 'done');
    claim('Low');
  }

  async function high() {
    await sleep(120);
    emit('High', 'ready');
    emit('High', 'wait for mutex');
    sched.highWaiting = true;
    if (usePI) claim('Low');
    while (sched.mutexHolder !== null) await sleep(10);
    sched.mutexHolder = 'High';
    sched.highWaiting = false;
    claim('High');
    emit('High', 'mutex acquired');
    await sleep(50);
    sched.mutexHolder = null;
    emit('High', 'done');
  }

  await Promise.all([low(), medium(), high()]);

  const ready = timeline.find(e => e.thread === 'High' && e.event === 'ready');
  const done = timeline.find(e => e.thread === 'High' && e.event === 'done');
  const latency = (ready && done) ? Math.round((done.t - ready.t) * 10) / 10 : null;

  return { use_pi: usePI, high_latency_ms: latency, timeline };
}

export async function run(params, send) {
  await send({ type: 'phase', label: 'Without priority inheritance' });
  const bad = await simulate(false, send);
  await send({ type: 'result', variant: 'without_pi', high_latency_ms: bad.high_latency_ms });

  await send({ type: 'phase', label: 'With priority inheritance' });
  const good = await simulate(true, send);
  await send({ type: 'result', variant: 'with_pi', high_latency_ms: good.high_latency_ms });

  await send({ type: 'done' });
}
