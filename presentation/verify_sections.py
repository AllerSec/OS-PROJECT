"""Quick visual check after restructuring index.html.
   Captures the new sections individually."""
from pathlib import Path
from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:8000/"
OUT = Path(__file__).parent / "screenshots"
OUT.mkdir(exist_ok=True)


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

        targets = {
            "section_cover": "#cover",
            "section_motivation": "#motivation",
            "section_concepts": "#concepts",
            "section_architecture": "#architecture",
            "section_conclusions": "#conclusions",
            "section_repo": "#repo",
        }
        for name, sel in targets.items():
            el = page.query_selector(sel)
            if not el:
                print(f"!! {sel} missing")
                continue
            el.scroll_into_view_if_needed()
            page.wait_for_timeout(350)
            el.screenshot(path=str(OUT / f"{name}.png"))
            print(f"   wrote {name}.png")

        b.close()


if __name__ == "__main__":
    main()
