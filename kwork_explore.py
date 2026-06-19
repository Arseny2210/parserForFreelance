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

        # 1) Go to main projects page and look at the category navigation
        await page.goto(
            "https://kwork.ru/projects", wait_until="domcontentloaded", timeout=30000
        )
        await page.wait_for_timeout(5000)

        # Find all navigation links that might be categories
        print("=== ALL NAV LINKS / CATEGORIES ===")
        links = await page.evaluate("""() => {
            const links = document.querySelectorAll('a[href*="projects"], a[href*="category"], a[href*="search"]');
            return Array.from(links).slice(0, 50).map(a => ({
                href: a.href,
                text: a.innerText.trim().substring(0, 60)
            }));
        }""")
        for l in links:
            print(f"  {l['text']:50s} -> {l['href']}")

        # 2) Try search with IT keyword
        print("\n=== SEARCH TEST ===")
        await page.goto(
            "https://kwork.ru/search?query=сайт",
            wait_until="domcontentloaded",
            timeout=30000,
        )
        await page.wait_for_timeout(5000)

        cards = await page.query_selector_all("div.want-card.want-card--list")
        print(f"Search 'сайт': {len(cards)} cards")

        # 3) Try another IT search
        await page.goto(
            "https://kwork.ru/search?query=python",
            wait_until="domcontentloaded",
            timeout=30000,
        )
        await page.wait_for_timeout(5000)

        cards = await page.query_selector_all("div.want-card.want-card--list")
        print(f"Search 'python': {len(cards)} cards")

        # 4) Try category URL
        await page.goto(
            "https://kwork.ru/projects/programmirovanie",
            wait_until="domcontentloaded",
            timeout=30000,
        )
        await page.wait_for_timeout(5000)
        html = await page.content()
        with open("/tmp/kwork_cat.html", "w") as f:
            f.write(html)

        title = await page.title()
        print(f"\nCategory page /programmirovanie: title='{title}'")

        cards = await page.query_selector_all("div.want-card.want-card--list")
        print(f"Category cards: {len(cards)}")

        print(f"Final URL: {page.url}")

        await page.goto(
            "https://kwork.ru/projects", wait_until="domcontentloaded", timeout=30000
        )
        await page.wait_for_timeout(5000)

        categories = await page.evaluate("""() => {
            const selectors = document.querySelectorAll('select, .category, .dropdown, [class*="categ"], [class*="rubr"]');
            return Array.from(selectors).slice(0, 10).map(el => ({
                tag: el.tagName,
                class: el.className,
                text: el.innerText.trim().substring(0, 100)
            }));
        }""")
        print("\n=== CATEGORY SELECTORS ===")
        for c in categories:
            print(f"  <{c['tag']} class='{c['class']}'> {c['text']}")

        await browser.close()


asyncio.run(main())
