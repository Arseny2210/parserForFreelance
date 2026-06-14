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

        # Go to projects page and examine the category filter sidebar in detail
        await page.goto(
            "https://kwork.ru/projects", wait_until="domcontentloaded", timeout=30000
        )
        await page.wait_for_timeout(3000)

        # Look at the sidebar filter in detail - find all rubric/category links
        print("=== SIDEBAR CATEGORY FILTER (Рубрики) ===")
        filters = await page.evaluate("""() => {
            // Find the wants-filter-sidebar or projects-filter
            const sidebar = document.querySelector('.wants-filter-sidebar, .projects-filter, .wants-left-side');
            if (!sidebar) return "NOT FOUND";
            
            // Get all links inside the sidebar that look like category filters
            const catLinks = sidebar.querySelectorAll('a, [data-category], [data-rubric], .projects-filter__rubrics-list a, .projects-filter__item a');
            return Array.from(catLinks).map(a => ({
                text: a.innerText.trim().substring(0, 60),
                href: a.href || '(no href)',
                class: (a.className || '').substring(0, 80),
                onclick: a.getAttribute('onclick') || '(none)',
                dataCategory: a.getAttribute('data-category') || '(none)'
            }));
        }""")

        if isinstance(filters, list):
            for f in filters:
                print(f"  '{f['text']}'")
                print(f"    href: {f['href']}")
                print(f"    class: {f['class']}")
                print(f"    onclick: {f['onclick']}")
                print(f"    data-category: {f['dataCategory']}")
        else:
            print(filters)

        # Get the entire HTML of the filter sidebar
        sidebar_html = await page.evaluate("""() => {
            const el = document.querySelector('.wants-filter-sidebar, .projects-filter, .wants-left-side');
            return el ? el.innerHTML.substring(0, 5000) : 'NOT FOUND';
        }""")
        print(f"\n=== SIDEBAR HTML (first 5000 chars) ===")
        print(sidebar_html)

        # Also try clicking on "Разработка и IT(110)" in the sidebar
        print("\n=== CLICKING CATEGORY IN SIDEBAR ===")
        cat_link = await page.query_selector(
            '.projects-filter__rubrics-list a:has-text("Разработка")'
        )
        if cat_link:
            href = await cat_link.get_attribute("href")
            print(f"Found link href: {href}")
            await cat_link.click()
            await page.wait_for_timeout(3000)
            print(f"After click URL: {page.url}")
            print(f"After click title: {await page.title()}")
        else:
            print(
                "Could not find Разработка link with partial text, looking for all category links..."
            )
            all_cat_links = await page.evaluate("""() => {
                const sidebar = document.querySelector('.projects-filter__rubrics-list');
                if (!sidebar) return [];
                return Array.from(sidebar.querySelectorAll('a')).map(a => ({
                    text: a.innerText.trim(),
                    href: a.href
                }));
            }""")
            for link in all_cat_links:
                print(f"  '{link['text']}' -> {link['href']}")

        await browser.close()


asyncio.run(main())
