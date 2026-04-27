/* =========================================================================
   Obsidian Lab — frontend controller (GitHub Pages, 100% client-side).
   No backend. Demos are ES modules. The "send" callback in each demo is
   simulated locally — same shape as the WebSocket events in the legacy
   Python version.
   ========================================================================= */

import { run as runRaceCondition }     from './demos/race_condition.js';
import { run as runMutexVsSpinlock }   from './demos/mutex_vs_spinlock.js';
import { run as runProducerConsumer }  from './demos/producer_consumer.js';
import { run as runReadersWriters }    from './demos/readers_writers.js';
import { run as runDeadlock }          from './demos/deadlock.js';
import { run as runPriorityInversion } from './demos/priority_inversion.js';

const DEMOS = {
  race_condition:     runRaceCondition,
  mutex_vs_spinlock:  runMutexVsSpinlock,
  producer_consumer:  runProducerConsumer,
  readers_writers:    runReadersWriters,
  deadlock:           runDeadlock,
  priority_inversion: runPriorityInversion,
};

// ---------- Status pill ----------
function updateStatus() {
  const el = document.getElementById('status-text');
  const isolated = self.crossOriginIsolated;
  const sab = typeof SharedArrayBuffer !== 'undefined';
  if (isolated && sab) {
    el.textContent = `online · 6 demos · isolated`;
  } else if (sab) {
    el.textContent = `partial · no isolation`;
  } else {
    el.textContent = `limited · no SAB`;
  }
}
window.addEventListener('load', updateStatus);
window.addEventListener('keydown', (e) => {
  if (e.key === 'r' || e.key === 'R') updateStatus();
});

// ---------- Demo runner ----------
async function runDemo(name, params, onEvent) {
  const fn = DEMOS[name];
  if (!fn) throw new Error('unknown demo: ' + name);
  const send = async (event) => { onEvent(event); };
  await fn(params || {}, send);
}

// ---------- DOM helpers ----------
function $(sel, root = document) { return root.querySelector(sel); }
function $$(sel, root = document) { return [...root.querySelectorAll(sel)]; }

function setField(card, name, value) {
  const el = card.querySelector(`[data-field="${name}"]`);
  if (el) el.textContent = value;
}

function setPhase(card, label) {
  const el = card.querySelector('[data-field="phase"]');
  if (!el) return;
  if (!label) { el.hidden = true; return; }
  el.hidden = false;
  el.textContent = label;
}

function disable(card, action, on) {
  const btn = card.querySelector(`[data-action="${action}"]`);
  if (btn) btn.disabled = on;
}

// ---------- Demo 1 — Race condition ----------
function bindRaceCondition(card) {
  $('[data-action="start"]', card).addEventListener('click', async () => {
    disable(card, 'start', true);
    setField(card, 'expected', '—');
    setField(card, 'unsafe', '…');
    setField(card, 'safe', '—');
    setField(card, 'lost', '—');
    setPhase(card, '');

    try {
      await runDemo('race_condition', { iterations: 60_000 }, (e) => {
        if (e.type === 'phase') setPhase(card, e.label);
        if (e.type === 'result') {
          setField(card, 'expected', e.expected.toLocaleString());
          if (e.variant === 'unsafe') {
            setField(card, 'unsafe', e.actual.toLocaleString());
            setField(card, 'lost', e.lost.toLocaleString());
          } else {
            setField(card, 'safe', e.actual.toLocaleString());
          }
        }
      });
    } catch (err) {
      console.error(err);
      setField(card, 'unsafe', 'no SAB');
    }

    setPhase(card, '');
    disable(card, 'start', false);
  });
}

// ---------- Demo 2 — Mutex vs Spinlock ----------
let mvsChart;
function ensureMvsChart() {
  if (mvsChart) return mvsChart;
  const ctx = document.getElementById('chart-mvs');
  mvsChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: ['Mutex', 'Spinlock'],
      datasets: [{
        label: 'Time (ms)',
        data: [0, 0],
        backgroundColor: ['rgba(91,224,255,0.65)', 'rgba(255,181,71,0.65)'],
        borderColor:     ['rgba(91,224,255,1)',     'rgba(255,181,71,1)'],
        borderWidth: 1, borderRadius: 8,
      }],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      animation: { duration: 600, easing: 'easeOutCubic' },
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { label: (c) => `${c.parsed.y} ms` } },
      },
      scales: {
        x: { ticks: { color: 'rgba(255,255,255,0.6)' }, grid: { color: 'rgba(255,255,255,0.04)' } },
        y: { ticks: { color: 'rgba(255,255,255,0.6)' }, grid: { color: 'rgba(255,255,255,0.04)' }, beginAtZero: true },
      },
    },
  });
  return mvsChart;
}

function bindMutexVsSpinlock(card) {
  $('[data-action="start"]', card).addEventListener('click', async () => {
    disable(card, 'start', true);
    const chart = ensureMvsChart();
    chart.data.datasets[0].data = [0, 0]; chart.update();
    setField(card, 'mutex', '…'); setField(card, 'spinlock', '—');

    try {
      await runDemo('mutex_vs_spinlock', { threads: 4, iterations: 30_000 }, (e) => {
        if (e.type === 'result') {
          if (e.variant === 'mutex') {
            chart.data.datasets[0].data[0] = e.elapsed_ms;
            setField(card, 'mutex', `${e.elapsed_ms} ms`);
          } else {
            chart.data.datasets[0].data[1] = e.elapsed_ms;
            setField(card, 'spinlock', `${e.elapsed_ms} ms`);
          }
          chart.update();
        }
      });
    } catch (err) { console.error(err); }

    disable(card, 'start', false);
  });
}

// ---------- Demo 3 — Producer / Consumer ----------
function bindProducerConsumer(card) {
  const bufEl = $('#pc-buffer');
  let bufferSize = 8;

  function renderBuffer(items) {
    bufEl.innerHTML = '';
    for (let i = 0; i < bufferSize; i++) {
      const slot = document.createElement('div');
      slot.className = 'slot' + (i < items.length ? ' filled' : '');
      slot.textContent = i < items.length ? items[i] : '';
      bufEl.appendChild(slot);
    }
  }

  $('[data-action="start"]', card).addEventListener('click', async () => {
    disable(card, 'start', true);
    setField(card, 'produced', 0);
    setField(card, 'consumed', 0);
    setField(card, 'inflight', 0);

    await runDemo('producer_consumer', {
      buffer_size: 8, items: 24, producer_delay_ms: 140, consumer_delay_ms: 240,
    }, (e) => {
      if (e.type === 'init') {
        bufferSize = e.buffer_size;
        setField(card, 'buffer_size', e.buffer_size);
        renderBuffer([]);
      }
      if (e.type === 'tick') {
        renderBuffer(e.buffer || []);
        setField(card, 'produced', e.produced);
        setField(card, 'consumed', e.consumed);
        setField(card, 'inflight', e.buffer.length);
      }
    });

    disable(card, 'start', false);
  });
}

// ---------- Demo 4 — Readers / Writers ----------
function bindReadersWriters(card) {
  const lanesEl = $('#rw-lanes');

  function ensureLane(name) {
    let lane = lanesEl.querySelector(`[data-thread="${name}"]`);
    if (lane) return lane;
    lane = document.createElement('div');
    lane.className = 'lane idle';
    lane.dataset.thread = name;
    lane.innerHTML = `<span class="name">${name}</span><span class="state">idle</span>`;
    lanesEl.appendChild(lane);
    return lane;
  }
  function setLaneState(name, state) {
    const lane = ensureLane(name);
    lane.className = `lane ${state}`;
    lane.querySelector('.state').textContent = state;
  }

  $('[data-action="start"]', card).addEventListener('click', async () => {
    disable(card, 'start', true);
    lanesEl.innerHTML = '';
    setField(card, 'reads', 0); setField(card, 'writes', 0);

    await runDemo('readers_writers', { readers: 4, writers: 1, duration_s: 8 }, (e) => {
      if (e.type === 'init') {
        for (let i = 0; i < e.readers; i++) ensureLane(`R${i + 1}`);
        for (let i = 0; i < e.writers; i++) ensureLane(`W${i + 1}`);
      }
      if (e.type === 'tick') {
        for (const [name, state] of Object.entries(e.states || {})) {
          setLaneState(name, state);
        }
        setField(card, 'reads', e.reads ?? 0);
        setField(card, 'writes', e.writes ?? 0);
      }
    });

    disable(card, 'start', false);
  });
}

// ---------- Demo 5 — Deadlock ----------
function bindDeadlock(card) {
  const a = $('#dl-a'), b = $('#dl-b');
  function reset() {
    for (const el of [a, b]) {
      el.classList.remove('holding', 'waiting', 'deadlocked');
      el.querySelector('.what').textContent = 'idle';
    }
    setField(card, 'result', '—');
    setField(card, 'elapsed', '— ms');
  }
  function applyState(state) {
    const map = [['A', a], ['B', b]];
    for (const [k, el] of map) {
      const s = state[k] || 'idle';
      el.querySelector('.what').textContent = s;
      el.classList.remove('holding', 'waiting');
      if (s.startsWith('want')) el.classList.add('waiting');
      if (s.startsWith('holds')) el.classList.add('holding');
    }
  }

  async function run(fix) {
    disable(card, 'break', true); disable(card, 'fix', true);
    reset();
    await runDemo('deadlock', { fix, timeout_s: 2.5 }, (e) => {
      if (e.type === 'tick') applyState(e.state);
      if (e.type === 'result') {
        if (e.deadlocked) {
          a.classList.add('deadlocked'); b.classList.add('deadlocked');
          setField(card, 'result', 'DEADLOCKED');
        } else {
          setField(card, 'result', 'completed');
        }
        setField(card, 'elapsed', `${e.elapsed_ms} ms`);
      }
    });
    disable(card, 'break', false); disable(card, 'fix', false);
  }

  $('[data-action="break"]', card).addEventListener('click', () => run(false));
  $('[data-action="fix"]',   card).addEventListener('click', () => run(true));
}

// ---------- Demo 6 — Priority Inversion ----------
function bindPriorityInversion(card) {
  const wraps = {
    without: $('#pi-timeline-without', card),
    'with':  $('#pi-timeline-with', card),
  };
  function clear() {
    for (const w of Object.values(wraps)) {
      $$('.tl-track', w).forEach(t => { t.innerHTML = ''; });
    }
    setField(card, 'lat_without', '— ms');
    setField(card, 'lat_with', '— ms');
  }
  const TOTAL_MS = 1500;
  const state = { without: {}, 'with': {} };
  function addEvent(variant, ev) {
    const wrap = wraps[variant];
    const tracks = {};
    $$('.tl-track', wrap).forEach(t => { tracks[t.dataset.track] = t; });
    const track = tracks[ev.thread];
    if (!track) return;
    const x = Math.min(100, (ev.t / TOTAL_MS) * 100);
    const last = state[variant][ev.thread];
    if (last && Math.abs(last.x - x) < 0.6) return;
    state[variant][ev.thread] = { x };
    const blocks = $$('.tl-block', track);
    const tail = blocks[blocks.length - 1];
    if (tail && parseFloat(tail.dataset.endx) >= x - 4) {
      tail.style.width = `${Math.max(2, x - parseFloat(tail.dataset.startx))}%`;
      tail.dataset.endx = x;
      return;
    }
    const block = document.createElement('div');
    block.className = `tl-block ${ev.thread.toLowerCase()}`;
    block.dataset.startx = x;
    block.dataset.endx = x;
    block.style.left = `${x}%`;
    block.style.width = '2%';
    block.title = `${ev.thread} · ${ev.event} · ${ev.t}ms`;
    track.appendChild(block);
  }

  $('[data-action="start"]', card).addEventListener('click', async () => {
    disable(card, 'start', true);
    clear();
    state.without = {}; state['with'] = {};

    await runDemo('priority_inversion', {}, (e) => {
      if (e.type === 'tick') {
        addEvent(e.use_pi ? 'with' : 'without', e);
      }
      if (e.type === 'result') {
        const field = e.variant === 'with_pi' ? 'lat_with' : 'lat_without';
        setField(card, field, e.high_latency_ms != null ? `${e.high_latency_ms} ms` : '—');
      }
    });

    disable(card, 'start', false);
  });
}

// ---------- Boot ----------
const BINDERS = {
  race_condition:     bindRaceCondition,
  mutex_vs_spinlock:  bindMutexVsSpinlock,
  producer_consumer:  bindProducerConsumer,
  readers_writers:    bindReadersWriters,
  deadlock:           bindDeadlock,
  priority_inversion: bindPriorityInversion,
};

document.querySelectorAll('.demo').forEach(card => {
  const name = card.dataset.demo;
  const binder = BINDERS[name];
  if (binder) binder(card);
});
