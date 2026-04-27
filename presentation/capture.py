"""
Headless screenshot capture for the presentation.

Run AFTER `uvicorn app.main:app` is up. Defaults to port 8911.
Outputs to presentation/screenshots/.
"""
import os
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = os.environ.get("OBSIDIAN_URL", "http://127.0.0.1:8000/")
OUT = Path(__file__).parent / "screenshots"
OUT.mkdir(exist_ok=True)


def shoot(page, selector, name, full_page=False, pad=False):
    path = OUT / f"{name}.png"
    if full_page:
        page.screenshot(path=str(path), full_page=True)
    else:
        el = page.query_selector(selector)
        if not el:
            print(f"!! {selector} not found, skipping {name}")
            return
        el.scroll_into_view_if_needed()
        page.wait_for_timeout(250)
        el.screenshot(path=str(path))
    print(f"   wrote {path.name}")


def run_demo_and_wait(page, demo, button_text="Run", wait_ms=4500):
    card = page.query_selector(f'.demo[data-demo="{demo}"]')
    btn = card.query_selector(f'button:has-text("{button_text}")')
    btn.click()
    page.wait_for_timeout(wait_ms)


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()

        # ---------- Desktop captures ----------
        ctx = browser.new_context(viewport={"width": 1440, "height": 900},
                                  device_scale_factor=2)
        page = ctx.new_page()
        page.goto(URL, wait_until="networkidle")
        page.wait_for_timeout(900)
        if not page.evaluate("self.crossOriginIsolated"):
            page.reload(wait_until="networkidle")
            page.wait_for_timeout(900)

        # 0. Full page (idle) — scroll to top first to settle layout
        page.evaluate("window.scrollTo(0,0)")
        page.wait_for_timeout(400)
        try:
            shoot(page, "html", "00_full_page", full_page=True)
        except Exception as e:
            print(f"!! full_page failed: {e}; trying viewport-only")
            page.screenshot(path=str(OUT / "00_full_page.png"))

        # 1. Hero
        shoot(page, ".hero", "01_hero")

        # 2-7. Each demo card, idle
        for i, demo in enumerate([
            "race_condition", "mutex_vs_spinlock", "producer_consumer",
            "readers_writers", "deadlock", "priority_inversion",
        ], start=2):
            shoot(page, f'.demo[data-demo="{demo}"]', f"{i:02d}_demo_{demo}")

        # 8. Race condition with results
        run_demo_and_wait(page, "race_condition", "Run", wait_ms=2500)
        shoot(page, '.demo[data-demo="race_condition"]', "08_race_condition_results")

        # 9. Mutex vs spinlock with chart populated
        run_demo_and_wait(page, "mutex_vs_spinlock", "Benchmark", wait_ms=4500)
        shoot(page, '.demo[data-demo="mutex_vs_spinlock"]', "09_mvs_results")

        # 10. Deadlock — broken
        page.click('.demo[data-demo="deadlock"] button:has-text("Cause")')
        page.wait_for_timeout(3200)
        shoot(page, '.demo[data-demo="deadlock"]', "10_deadlock_broken")

        # 11. Producer/consumer mid-run
        page.click('.demo[data-demo="producer_consumer"] button:has-text("Run")')
        page.wait_for_timeout(2200)
        shoot(page, '.demo[data-demo="producer_consumer"]', "11_producer_consumer_running")

        # ---------- Mobile capture ----------
        ctx2 = browser.new_context(
            viewport={"width": 390, "height": 844},
            device_scale_factor=3,
            is_mobile=True, has_touch=True,
        )
        m = ctx2.new_page()
        m.goto(URL, wait_until="networkidle")
        m.wait_for_timeout(900)
        if not m.evaluate("self.crossOriginIsolated"):
            m.reload(wait_until="networkidle")
            m.wait_for_timeout(900)
        m.screenshot(path=str(OUT / "12_mobile_view.png"), full_page=True)
        print("   wrote 12_mobile_view.png")

        browser.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("ERROR:", e, file=sys.stderr)
        raise
