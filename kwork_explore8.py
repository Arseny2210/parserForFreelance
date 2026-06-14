import asyncio
from playwright.async_api import async_playwright


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        )
        page = await context.new_page()

        # Go to IT category and read all subcategory links directly from sidebar HTML
        await page.goto(
            "https://kwork.ru/projects?c=11",
            wait_until="domcontentloaded",
            timeout=30000,
        )
        await page.wait_for_timeout(3000)

        # Get the sidebar filter HTML and extract category info
        print("=== FULL IT SUBCATEGORY TREE ===")
        tree = await page.evaluate("""() => {
            function extractTree(root, depth=0) {
                const items = root.querySelectorAll(':scope > .multilevel-list__items > .multilevel-list__item');
                const result = [];
                items.forEach(item => {
                    const label = item.querySelector(':scope > .multilevel-list__label');
                    const title = label?.querySelector('.multilevel-list__label-title');
                    const count = label?.querySelector('.multilevel-list__label-count');
                    const subList = item.querySelector(':scope > .multilevel-list');
                    result.push({
                        title: title ? title.innerText.trim() : '?',
                        count: count ? count.innerText : '',
                        children: subList ? extractTree(subList, depth+1) : []
                    });
                });
                return result;
            }
            const root = document.querySelector('.multilevel-list--clickable');
            return root ? extractTree(root) : [];
        }""")

        def print_tree(nodes, indent=0):
            for node in nodes:
                prefix = "  " * indent
                print(f"{prefix}{node['title']:30s} {node['count']}")
                if node["children"]:
                    print_tree(node["children"], indent + 1)

        print_tree(tree)

        # Get page URL for each visible subcategory by clicking
        print("\n\n=== CLICKING EACH SUBCATEGORY TO GET URL ===")
        # First expand Скрипты, боты и mini apps if visible
        script_cat = await page.query_selector(
            '.multilevel-list__label:has(.multilevel-list__label-title:text("Скрипты"))'
        )
        if script_cat:
            await script_cat.click()
            await page.wait_for_timeout(1500)

        # Get all subcategory labels at second level
        subs = await page.query_selector_all(
            ".multilevel-list__item .multilevel-list__item > .multilevel-list__label"
        )
        for s in subs:
            title_el = await s.query_selector(".multilevel-list__label-title")
            if title_el:
                title = (await title_el.inner_text()).strip()
                await s.click()
                await page.wait_for_timeout(1500)
                print(
                    f"  {title:35s} -> {page.url.split('?')[1] if '?' in page.url else 'N/A'}"
                )
                await page.go_back()
                await page.wait_for_timeout(2000)
                # Re-expand if needed
                script_cat = await page.query_selector(
                    '.multilevel-list__label:has(.multilevel-list__label-title:text("Скрипты"))'
                )
                if script_cat:
                    await script_cat.click()
                    await page.wait_for_timeout(1000)

        await browser.close()


asyncio.run(main())
