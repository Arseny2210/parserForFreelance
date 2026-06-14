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

        await page.goto(
            "https://kwork.ru/projects", wait_until="domcontentloaded", timeout=30000
        )
        await page.wait_for_timeout(3000)

        # Click Разработка и IT to expand subcategories
        cat_label = await page.query_selector(
            '.multilevel-list__label:has(.multilevel-list__label-title:text("Разработка"))'
        )
        if cat_label:
            await cat_label.click()
            await page.wait_for_timeout(2000)

            # Now for each subcategory, check what happens when we click
            sub_titles = await page.evaluate("""() => {
                const items = document.querySelectorAll('.multilevel-list__item .multilevel-list__item .multilevel-list__label-title');
                return Array.from(items).map(el => el.innerText.trim());
            }""")
            print("=== SUBCATEGORIES ===")

            for sub_title in sub_titles:
                # Click each subcategory
                sub = await page.query_selector(
                    f'.multilevel-list__label:has(.multilevel-list__label-title:text("{sub_title}"))'
                )
                if sub:
                    await sub.click()
                    await page.wait_for_timeout(1500)
                    url = page.url
                    title = await page.title()

                    # Count visible cards
                    card_count = await page.evaluate("""() => {
                        return document.querySelectorAll('.want-card.want-card--list').length;
                    }""")

                    print(
                        f"  {sub_title:35s} -> c={url.split('c=')[-1].split('&')[0] if 'c=' in url else 'N/A'}"
                    )
                    print(f"      Title: {title}")
                    print(f"      Cards: {card_count}")
                    print(f"      URL:   {url}")
                    print()

                    # Go back to parent category
                    await page.go_back()
                    await page.wait_for_timeout(1500)

        # Also explore the subcategories further
        print("\n=== DEEP SUBCATEGORIES (expand Скрипты, боты и mini apps) ===")
        await page.goto(
            "https://kwork.ru/projects?c=11",
            wait_until="domcontentloaded",
            timeout=30000,
        )
        await page.wait_for_timeout(3000)

        # Expand subcategories
        script_cat = await page.query_selector(
            '.multilevel-list__label:has(.multilevel-list__label-title:text("Скрипты"))'
        )
        if script_cat:
            await script_cat.click()
            await page.wait_for_timeout(2000)

            deep_subs = await page.evaluate("""() => {
                const items = document.querySelectorAll('.multilevel-list__item .multilevel-list__item .multilevel-list__item .multilevel-list__label-title');
                return Array.from(items).map(el => el.innerText.trim());
            }""")
            print(f"Deep subcategories: {deep_subs}")

            for ds in deep_subs:
                sub = await page.query_selector(
                    f'.multilevel-list__label:has(.multilevel-list__label-title:text("{ds}"))'
                )
                if sub:
                    await sub.click()
                    await page.wait_for_timeout(1500)
                    url = page.url
                    card_count = len(
                        await page.query_selector_all(".want-card.want-card--list")
                    )
                    print(f"  {ds:35s} -> URL: {url}  Cards: {card_count}")
                    await page.go_back()
                    await page.wait_for_timeout(1500)

        # Check what category IDs are used for all top-level categories
        print("\n=== ALL TOP-LEVEL CATEGORY IDs ===")
        await page.goto(
            "https://kwork.ru/projects", wait_until="domcontentloaded", timeout=30000
        )
        await page.wait_for_timeout(3000)

        top_levels = await page.evaluate("""() => {
            const items = document.querySelectorAll('.multilevel-list__item > .multilevel-list__label');
            return Array.from(items).map(el => {
                const title = el.querySelector('.multilevel-list__label-title');
                const count = el.querySelector('.multilevel-list__label-count');
                return title ? title.innerText.trim() : 'unknown';
            });
        }""")

        for tl in top_levels:
            cat = await page.query_selector(
                f'.multilevel-list__label:has(.multilevel-list__label-title:text("{tl[:20]}"))'
            )
            if cat:
                await cat.click()
                await page.wait_for_timeout(1500)
                url = page.url
                c_id = url.split("c=")[-1].split("&")[0] if "c=" in url else "N/A"
                print(f"  {tl:30s} -> ?c={c_id}")
                # click again to collapse
                await cat.click()
                await page.wait_for_timeout(500)

        await browser.close()


asyncio.run(main())
