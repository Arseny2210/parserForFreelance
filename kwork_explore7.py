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

        # Get all top-level category IDs by direct URL access with known categories
        # We know: Дизайн=c15, Разработка и IT=c11
        # Let's get others by checking the DOM directly
        await page.goto(
            "https://kwork.ru/projects", wait_until="domcontentloaded", timeout=30000
        )
        await page.wait_for_timeout(3000)

        # Get all category IDs from the data attributes or click handlers
        cats = await page.evaluate("""() => {
            const items = document.querySelectorAll('.multilevel-list__item > .multilevel-list__label');
            const results = [];
            items.forEach(el => {
                const title = el.querySelector('.multilevel-list__label-title');
                const count = el.querySelector('.multilevel-list__label-count');
                // Get onclick or data attributes
                const onclick = el.getAttribute('onclick') || '(none)';
                results.push({
                    title: title ? title.innerText.trim() : '?',
                    count: count ? count.innerText : '',
                    onclick: onclick.substring(0, 200)
                });
            });
            return results;
        }""")

        print("=== ALL TOP-LEVEL CATS WITH ONCLICK ===")
        for c in cats:
            print(f"  '{c['title']}' count={c['count']}")
            print(f"    onclick: {c['onclick']}")

        # Get ALL categories with their IDs by clicking one by one
        print("\n\n=== SYSTEMATIC CATEGORY EXPLORATION ===")
        # Use direct URL with ?c= to get each top category
        # We need to discover the IDs. Let's check a few known ones
        known_cats = {
            "Дизайн": 15,
            "Разработка и IT": 11,
            "Тексты и переводы": 21,
            "SEO и трафик": 8,
            "Соцсети и маркетинг": 27,
            "Аудио, видео, съемка": 22,
            "Бизнес и жизнь": 24,
        }

        # Also try popular IDs that we haven't confirmed
        for name, cid in known_cats.items():
            await page.goto(
                f"https://kwork.ru/projects?c={cid}",
                wait_until="domcontentloaded",
                timeout=15000,
            )
            await page.wait_for_timeout(2000)
            title = await page.title()
            card_count = len(
                await page.query_selector_all(".want-card.want-card--list")
            )
            print(f"  ?c={cid:3d} ({name:25s}) cards={card_count:3d} title='{title}'")

        # Get full details: scrape all subcategories for IT
        print("\n\n=== IT SUBCATEGORY DETAILS ===")
        await page.goto(
            "https://kwork.ru/projects?c=11",
            wait_until="domcontentloaded",
            timeout=15000,
        )
        await page.wait_for_timeout(3000)

        # Get all visible subcategory names and their IDs from the DOM
        it_subcats = await page.evaluate("""() => {
            const items = document.querySelectorAll('.multilevel-list__item .multilevel-list__item > .multilevel-list__label');
            const results = [];
            items.forEach(el => {
                const title = el.querySelector('.multilevel-list__label-title');
                const count = el.querySelector('.multilevel-list__label-count');
                results.push({
                    title: title ? title.innerText.trim() : '?',
                    count: count ? count.innerText : ''
                });
            });
            return results;
        }""")

        for sc in it_subcats:
            print(f"  Sub: '{sc['title']}' count={sc['count']}")

        # Click each sub to get its ID
        sub_labels = await page.query_selector_all(
            ".multilevel-list__item .multilevel-list__item > .multilevel-list__label"
        )
        for lbl in sub_labels:
            title_el = await lbl.query_selector(".multilevel-list__label-title")
            if not title_el:
                continue
            title = await title_el.inner_text()
            title = title.strip()

            await lbl.click()
            await page.wait_for_timeout(1500)
            url = page.url
            cards = len(await page.query_selector_all(".want-card.want-card--list"))
            print(f"  {title:35s} -> {url}  cards={cards}")

            # Check if there are deeper subcategories
            deep_items = await page.query_selector_all(
                ".multilevel-list__item .multilevel-list__item .multilevel-list__item > .multilevel-list__label"
            )
            if deep_items:
                print(f"      (has {len(deep_items)} deep subcategories)")
                for dlbl in deep_items:
                    dt = await (
                        await dlbl.query_selector(".multilevel-list__label-title")
                    ).inner_text()
                    dt = dt.strip()

                    await dlbl.click()
                    await page.wait_for_timeout(1500)
                    durl = page.url
                    dcards = len(
                        await page.query_selector_all(".want-card.want-card--list")
                    )
                    print(f"      Deep: {dt:30s} -> {durl}  cards={dcards}")

                    await page.goto(url, wait_until="domcontentloaded", timeout=15000)
                    await page.wait_for_timeout(2000)

            # Go back to parent category
            await page.goto(
                "https://kwork.ru/projects?c=11",
                wait_until="domcontentloaded",
                timeout=15000,
            )
            await page.wait_for_timeout(2000)

        await browser.close()


asyncio.run(main())
