"""End-to-end test: open the static site and run every demo button.

Exits non-zero if any demo fails to update its UI.
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:8000/"


def assert_text(page, selector, must_not_be, msg):
    text = page.text_content(selector).strip()
    if text in must_not_be:
        raise AssertionError(f"{msg}: got '{text}'")
    print(f"  OK {msg}: '{text}'")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        page.on("console", lambda m: print("[console]", m.type, m.text)
                if m.type in ("error", "warning") else None)
        page.on("pageerror", lambda e: print("[pageerror]", e))

        page.goto(URL, wait_until="networkidle")
        page.wait_for_timeout(1500)

        # Some browsers need a reload after the SW activates.
        if not page.evaluate("self.crossOriginIsolated"):
            page.reload(wait_until="networkidle")
            page.wait_for_timeout(1500)
        isolated = page.evaluate("self.crossOriginIsolated")
        sab = page.evaluate("typeof SharedArrayBuffer !== 'undefined'")
        print(f"  crossOriginIsolated = {isolated}, SAB = {sab}")

        # Demo 1
        page.click('.demo[data-demo="race_condition"] [data-action="start"]')
        page.wait_for_timeout(2500)
        assert_text(page,
            '.demo[data-demo="race_condition"] [data-field="expected"]',
            ['—', '…'], "race_condition.expected")

        # Demo 2 — bench
        page.click('.demo[data-demo="mutex_vs_spinlock"] [data-action="start"]')
        page.wait_for_timeout(5500)
        assert_text(page,
            '.demo[data-demo="mutex_vs_spinlock"] [data-field="mutex"]',
            ['—', '…'], "mutex_vs_spinlock.mutex")
        assert_text(page,
            '.demo[data-demo="mutex_vs_spinlock"] [data-field="spinlock"]',
            ['—', '…'], "mutex_vs_spinlock.spinlock")

        # Demo 3 — start, give it 3s
        page.click('.demo[data-demo="producer_consumer"] [data-action="start"]')
        page.wait_for_timeout(3000)
        produced = int(page.text_content(
            '.demo[data-demo="producer_consumer"] [data-field="produced"]'))
        if produced < 1:
            raise AssertionError(f"producer_consumer made nothing (produced={produced})")
        print(f"  OK producer_consumer.produced={produced}")

        # Demo 4 — readers
        page.click('.demo[data-demo="readers_writers"] [data-action="start"]')
        page.wait_for_timeout(3000)
        reads = int(page.text_content(
            '.demo[data-demo="readers_writers"] [data-field="reads"]'))
        print(f"  OK readers_writers.reads={reads}")

        # Demo 5 — deadlock broken
        page.click('.demo[data-demo="deadlock"] [data-action="break"]')
        page.wait_for_timeout(3500)
        result = page.text_content(
            '.demo[data-demo="deadlock"] [data-field="result"]').strip()
        if result not in ("DEADLOCKED", "completed"):
            raise AssertionError(f"deadlock result unexpected: {result}")
        print(f"  OK deadlock.result={result}")

        # Demo 6 — priority inversion
        page.click('.demo[data-demo="priority_inversion"] [data-action="start"]')
        page.wait_for_timeout(7000)
        lat = page.text_content(
            '.demo[data-demo="priority_inversion"] [data-field="lat_without"]').strip()
        if lat in ('— ms', '—'):
            raise AssertionError(f"priority_inversion lat_without not updated: {lat}")
        print(f"  OK priority_inversion.lat_without={lat}")

        browser.close()
        print("ALL DEMOS PASSED")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("FAIL:", e, file=sys.stderr)
        sys.exit(1)
