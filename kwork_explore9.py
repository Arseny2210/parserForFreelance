import asyncio
from playwright.async_api import async_playwright


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        )
        page = await context.new_page()

        await page.goto(
            "https://kwork.ru/projects?c=11",
            wait_until="domcontentloaded",
            timeout=30000,
        )
        await page.wait_for_timeout(3000)

        # Collect all subcategory labels
        print("=== ALL IT SUBCATEGORY URLs ===")
        all_subs = await page.query_selector_all(
            ".multilevel-list__item .multilevel-list__item > .multilevel-list__label"
        )
        for s in all_subs:
            title_el = await s.query_selector(".multilevel-list__label-title")
            if not title_el:
                continue
            title = (await title_el.inner_text()).strip()

            await s.click()
            await page.wait_for_timeout(1500)
            url = page.url
            cards = len(await page.query_selector_all(".want-card.want-card--list"))
            print(f"{title:35s} {url}  cards={cards}")

            # Go back to IT root
            await page.goto(
                "https://kwork.ru/projects?c=11",
                wait_until="domcontentloaded",
                timeout=15000,
            )
            await page.wait_for_timeout(2000)

        # Also get search page with IT keyword
        print("\n=== SEARCH PAGE ===")
        await page.goto(
            "https://kwork.ru/search?query=python+разработка",
            wait_until="domcontentloaded",
            timeout=30000,
        )
        await page.wait_for_timeout(3000)

        # Check what elements exist on search page
        search_elements = await page.evaluate("""() => {
            const all = document.querySelectorAll('[class*="want"], [class*="card"], [class*="search"], .content > *, main > *, .wants-list > *');
            return Array.from(all).slice(0, 30).map(el => ({
                tag: el.tagName,
                id: el.id || '',
                class: (el.className || '').substring(0, 100),
                text: el.innerText.trim().substring(0, 120)
            }));
        }""")
        print(f"Search page elements ({len(search_elements)}):")
        for e in search_elements[:15]:
            print(f"  <{e['tag']}#{e['id']} class='{e['class'][:70]}'>")
            if e["text"]:
                print(f"    text: {e['text'][:100]}")

        await browser.close()


asyncio.run(main())
