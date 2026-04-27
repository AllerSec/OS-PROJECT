"""Capture one demo with the new code panel expanded."""
from pathlib import Path
from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:8000/"
OUT = Path(__file__).parent / "screenshots"


def main():
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={"width": 1440, "height": 900},
                             device_scale_factor=2)
        page = ctx.new_page()
        page.goto(URL, wait_until="networkidle")
        page.wait_for_timeout(800)
        if not page.evaluate("self.crossOriginIsolated"):
            page.reload(wait_until="networkidle")
            page.wait_for_timeout(800)

        # Open the code panel on demo 1
        page.evaluate("""
            const card = document.querySelector('.demo[data-demo=\"race_condition\"]');
            const det = card.querySelector('.code-panel');
            det.open = true;
            card.scrollIntoView({block:'center'});
        """)
        page.wait_for_timeout(500)
        card = page.query_selector('.demo[data-demo="race_condition"]')
        card.screenshot(path=str(OUT / "demo_with_code_panel.png"))
        print("wrote demo_with_code_panel.png")
        b.close()


if __name__ == "__main__":
    main()
