import asyncio
from playwright.async_api import async_playwright


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
        )
        page = await context.new_page()

        # First check what the default projects page looks like
        print("=== DEFAULT PROJECTS PAGE ===")
        await page.goto(
            "https://kwork.ru/projects", wait_until="domcontentloaded", timeout=30000
        )
        await page.wait_for_timeout(3000)

        # Check the page structure - look for category filter/tabs
        filters = await page.evaluate("""() => {
            // Look for filter elements, tabs, category buttons
            const all = document.querySelectorAll('a[href], button, [role="tab"], .filter, .tab, [class*="filter"], [class*="tab"], [class*="categ"], select, option, .nav, nav a');
            return Array.from(all).filter(el => {
                const text = el.innerText.trim();
                return text.length > 0 && text.length < 80;
            }).slice(0, 100).map(el => ({
                tag: el.tagName,
                text: el.innerText.trim().substring(0, 60),
                href: el.href || el.getAttribute('data-href') || '(none)',
                class: (el.className || '').substring(0, 80)
            }));
        }""")
        print(f"\n=== FILTERS / TABS / BUTTONS ({len(filters)} items) ===")
        for f in filters:
            print(
                f"  [{f['tag']}] class='{f['class']}' text='{f['text']}' href='{f['href']}'"
            )

        # Also check what cards look like
        cards = await page.evaluate("""() => {
            const cards = document.querySelectorAll('[class*="want"], [class*="card"], [class*="project"], article, .item, .row > div');
            return Array.from(cards).slice(0, 10).map(el => ({
                class: el.className.substring(0, 100),
                text: el.innerText.trim().substring(0, 100),
                tag: el.tagName
            }));
        }""")
        print(f"\n=== SAMPLE CARDS ({len(cards)} items) ===")
        for c in cards:
            print(f"  <{c['tag']}> class='{c['class']}'")
            print(f"    text: {c['text']}")

        # Now check the category-filtered projects page
        print("\n\n=== PROJECTS WITH category=it PARAM ===")
        await page.goto(
            "https://kwork.ru/projects?category=it",
            wait_until="domcontentloaded",
            timeout=30000,
        )
        await page.wait_for_timeout(3000)
        print(f"URL: {page.url}")
        print(f"Title: {await page.title()}")

        filters2 = await page.evaluate("""() => {
            const all = document.querySelectorAll('a[href], button, [role="tab"], .filter, .tab, [class*="filter"], [class*="tab"], [class*="categ"], select, option, .nav, nav a');
            return Array.from(all).filter(el => {
                const text = el.innerText.trim();
                return text.length > 0 && text.length < 80;
            }).slice(0, 100).map(el => ({
                tag: el.tagName,
                text: el.innerText.trim().substring(0, 60),
                href: el.href || el.getAttribute('data-href') || '(none)',
                class: (el.className || '').substring(0, 80)
            }));
        }""")
        print(f"\n=== FILTERS ({len(filters2)} items) ===")
        for f in filters2:
            print(
                f"  [{f['tag']}] class='{f['class']}' text='{f['text']}' href='{f['href']}'"
            )

        # Check what the page actually shows - look at ALL select/option elements
        print("\n=== ALL SELECT ELEMENTS ===")
        selects = await page.evaluate("""() => {
            return Array.from(document.querySelectorAll('select')).map(sel => ({
                name: sel.name,
                id: sel.id,
                class: sel.className,
                options: Array.from(sel.options).map(o => ({
                    text: o.innerText.trim().substring(0, 50),
                    value: o.value
                }))
            }));
        }""")
        for s in selects:
            print(f"  <select name='{s['name']}' id='{s['id']}' class='{s['class']}'>")
            for o in s["options"]:
                print(f"    <option value='{o['value']}'>{o['text']}</option>")

        await browser.close()


asyncio.run(main())
