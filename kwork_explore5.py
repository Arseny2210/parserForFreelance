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

        # Listen for all requests
        requests = []
        page.on(
            "request",
            lambda req: (
                requests.append(req.url)
                if "kwork" in req.url and "api" in req.url
                else None
            ),
        )

        await page.goto(
            "https://kwork.ru/projects", wait_until="domcontentloaded", timeout=30000
        )
        await page.wait_for_timeout(3000)

        # Click on "Разработка и IT" in the sidebar
        print("=== CLICKING ON 'Разработка и IT' IN SIDEBAR ===")

        # The category is a span, so we need to click the label element
        cat_label = await page.query_selector(
            '.multilevel-list__label:has(.multilevel-list__label-title:text("Разработка"))'
        )
        if cat_label:
            await cat_label.click()
            await page.wait_for_timeout(3000)
            print(f"URL after click: {page.url}")
            print(f"Title: {await page.title()}")

            # Check what requests were made
            print(f"\n=== API REQUESTS (last 15) ===")
            for r in requests[-15:]:
                print(f"  {r}")

            # Check if subcategories appeared
            subcats = await page.evaluate("""() => {
                const items = document.querySelectorAll('.multilevel-list__item');
                return Array.from(items).slice(0, 25).map(el => {
                    const title = el.querySelector('.multilevel-list__label-title');
                    const count = el.querySelector('.multilevel-list__label-count');
                    return {
                        title: title ? title.innerText : '(no title)',
                        count: count ? count.innerText : '',
                        level: el.closest('ul').parentElement?.className || ''
                    };
                });
            }""")
            print(f"\n=== CATEGORIES AFTER CLICK ===")
            for s in subcats:
                print(f"  {s['title']:30s} {s['count']:10s} [{s['level'][:50]}]")

        # Now also click a deep subcategory to see what happens
        if cat_label:
            # Look for a subcategory like "Парсеры" or "Чат-боты"
            sub = await page.query_selector(
                '.multilevel-list__label:has(.multilevel-list__label-title:text("Парсеры"))'
            )
            if sub:
                await sub.click()
                await page.wait_for_timeout(3000)
                print(f"\nURL after subcategory click: {page.url}")
                print(f"Title: {await page.title()}")

                # Check what the project cards look like now
                cards = await page.evaluate("""() => {
                    const items = document.querySelectorAll('[class*="want-card"], .want, .project, .card');
                    return Array.from(items).slice(0, 5).map(el => ({
                        class: el.className.substring(0, 120),
                        text: el.innerText.trim().substring(0, 200)
                    }));
                }""")
                print(f"\n=== PROJECT CARDS ({len(cards)}) ===")
                for c in cards:
                    print(f"  class='{c['class']}'")
                    print(f"  text: {c['text']}")
                    print("  ---")

        # Now try the projects page with ?category=it param and check what cards look like
        print("\n\n=== PROJECTS WITH ?category=it ===")
        requests.clear()
        await page.goto(
            "https://kwork.ru/projects?category=it",
            wait_until="domcontentloaded",
            timeout=30000,
        )
        await page.wait_for_timeout(3000)
        print(f"URL: {page.url}")

        # Find the actual project card containers
        cards = await page.evaluate("""() => {
            const items = document.querySelectorAll('.want-card, .want-card--list, [class*="want-card"], .wants-list .want-card, .wants-list > div');
            return Array.from(items).slice(0, 5).map(el => ({
                class: el.className.substring(0, 120),
                text: el.innerText.trim().substring(0, 200)
            }));
        }""")
        print(f"\n=== CARDS ({len(cards)}) ===")
        if cards:
            for c in cards:
                print(f"  class='{c['class']}'")
                print(f"  text: {c['text']}")
                print("  ---")
        else:
            # Try broader selectors
            all_divs = await page.evaluate("""() => {
                const items = document.querySelectorAll('.wants-list > *, .content > div, main > div');
                return Array.from(items).slice(0, 20).map(el => ({
                    class: el.className.substring(0, 100),
                    tag: el.tagName,
                    id: el.id,
                    text: el.innerText.trim().substring(0, 100)
                }));
            }""")
            for d in all_divs:
                print(f"  <{d['tag']}#{d['id']} class='{d['class']}'> {d['text']}")

        await browser.close()


asyncio.run(main())
