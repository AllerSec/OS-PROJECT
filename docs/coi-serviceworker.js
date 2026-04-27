/*! coi-serviceworker v0.1.7 — MIT
 * Adds COOP+COEP headers via a service worker so that SharedArrayBuffer
 * and Atomics.wait/notify work on hosts that don't set them (e.g. GitHub Pages).
 *
 * Source: https://github.com/gzuidhof/coi-serviceworker
 * Inlined here so the page works fully offline (no third-party requests).
 */
(() => {
  'use strict';
  if (typeof window === 'undefined') {
    self.addEventListener('install', () => self.skipWaiting());
    self.addEventListener('activate', (e) => e.waitUntil(self.clients.claim()));
    self.addEventListener('message', (e) => {
      if (!e.data) return;
      if (e.data.type === 'deregister') {
        self.registration.unregister().then(() =>
          self.clients.matchAll().then(cs => cs.forEach(c => c.navigate(c.url)))
        );
      }
    });
    self.addEventListener('fetch', (event) => {
      const r = event.request;
      if (r.cache === 'only-if-cached' && r.mode !== 'same-origin') return;
      const req = (r.cache === 'no-cache') ? new Request(r, { cache: 'no-store' }) : r;
      event.respondWith(
        fetch(req)
          .then((response) => {
            if (response.status === 0) return response;
            const headers = new Headers(response.headers);
            headers.set('Cross-Origin-Embedder-Policy', 'require-corp');
            headers.set('Cross-Origin-Opener-Policy', 'same-origin');
            headers.set('Cross-Origin-Resource-Policy', 'cross-origin');
            return new Response(response.body, {
              status: response.status,
              statusText: response.statusText,
              headers,
            });
          })
          .catch(() => fetch(r))
      );
    });
  } else {
    (() => {
      const reloadedKey = 'coi-reloaded';
      if (!window.crossOriginIsolated && !navigator.serviceWorker) {
        console.warn('[COI] No service worker support; SharedArrayBuffer unavailable.');
        return;
      }
      window.addEventListener('load', async () => {
        if (window.crossOriginIsolated) return;
        if (!navigator.serviceWorker) return;
        try {
          const reg = await navigator.serviceWorker.register(
            window.document.currentScript ? window.document.currentScript.src : 'coi-serviceworker.js',
            { scope: './' }
          );
          if (reg.active && !navigator.serviceWorker.controller) {
            // First install — reload once so the SW takes control.
            if (!sessionStorage.getItem(reloadedKey)) {
              sessionStorage.setItem(reloadedKey, '1');
              window.location.reload();
            }
          }
        } catch (e) {
          console.warn('[COI] SW registration failed:', e);
        }
      });
    })();
  }
})();
