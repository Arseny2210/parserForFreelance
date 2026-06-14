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

        # Go to projects page
        await page.goto(
            "https://kwork.ru/projects", wait_until="domcontentloaded", timeout=30000
        )
        await page.wait_for_timeout(5000)

        # 1) Get ALL links from the "Разработка и IT" category menu by clicking it
        print("=== CLICK 'Разработка и IT' CATEGORY ===")

        # First let's check the hrefs of the category links
        cat_links = await page.evaluate("""() => {
            const items = document.querySelectorAll('.category-menu__list-item, ' +
                '.js-category-menu-item, .js-cat-menu-thin-link, ' +
                '.category-menu a, .cat-menu-wide a');
            return Array.from(items).map(a => ({
                text: a.innerText.trim().substring(0, 50),
                href: a.href || '(no href)',
                onclick: a.getAttribute('onclick') || '(none)',
                dataset: JSON.stringify(a.dataset || {})
            }));
        }""")
        print(f"Found {len(cat_links)} category items")
        for c in cat_links:
            print(f"  '{c['text']}'")
            print(f"    href: {c['href']}")
            print(f"    onclick: {c['onclick']}")
            if c["dataset"] != "{}":
                print(f"    data: {c['dataset']}")

        # 2) Try clicking on Разработка и IT
        dev_item = await page.query_selector("text=Разработка и IT")
        if dev_item:
            await dev_item.click()
            await page.wait_for_timeout(3000)
            print(f"\nAfter click URL: {page.url}")
            print(f"Title: {await page.title()}")

            # look for subcategories
            subcats = await page.evaluate("""() => {
                const links = document.querySelectorAll('a');
                return Array.from(links).slice(0, 80).map(a => ({
                    text: a.innerText.trim().substring(0, 60),
                    href: a.href
                })).filter(l => l.text.length > 0 && l.href.includes('kwork'));
            }""")
            print("\n=== SUBCATEGORIES / LINKS AFTER CLICK ===")
            for s in subcats[:30]:
                print(f"  {s['text']:50s} -> {s['href']}")

        # 3) Try to click on subcategory if it appears
        await page.wait_for_timeout(2000)

        # 4) Also try the classic category URL pattern
        for cat_path in [
            "/projects?category=it",
            "/projects?category=razrabotka-it",
            "/allprojects?category=it",
            "/projects/category/razrabotka-i-it",
            "/catalog/razrabotka-it",
            "/go/razrabotka-it",
        ]:
            await page.goto(
                f"https://kwork.ru{cat_path}",
                wait_until="domcontentloaded",
                timeout=15000,
            )
            await page.wait_for_timeout(2000)
            title = await page.title()
            print(f"\nTrying {cat_path}: title='{title}' url='{page.url}'")
            cards = await page.query_selector_all(
                "div.want-card.want-card--list, article, .card, [class*='project'], [class*='want']"
            )
            print(f"  Found {len(cards)} card-like elements")

        await browser.close()


asyncio.run(main())
