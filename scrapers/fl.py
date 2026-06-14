import re
from typing import Optional, Any
from datetime import datetime, timezone
from urllib.parse import urljoin
from loguru import logger
from scrapers.base import BaseScraper, TaskData


class FLScraper(BaseScraper):
    def __init__(self) -> None:
        super().__init__()
        self.source_name = "fl"
        self.base_url = "https://www.fl.ru"
        self.search_url = "https://www.fl.ru/projects/"
        self.max_pages = 5

    async def _collect_raw(self) -> list[dict[str, Any]]:
        logger.info("Fetching FL.ru project listings (up to {} pages)", self.max_pages)
        jobs = []
        seen_ids: set[str] = set()

        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
            )

            page = await context.new_page()

            for page_num in range(1, self.max_pages + 1):
                try:
                    if page_num == 1:
                        url = self.search_url
                    else:
                        url = f"{self.search_url}page-{page_num}/"

                    await page.goto(url, wait_until="load", timeout=60000)
                    await page.wait_for_timeout(12000)

                    await page.evaluate(
                        "window.scrollTo(0, document.body.scrollHeight)"
                    )
                    await page.wait_for_timeout(3000)
                    await page.evaluate("window.scrollTo(0, 0)")
                    await page.wait_for_timeout(2000)

                    try:
                        await page.wait_for_selector("div.b-post", timeout=10000)
                    except Exception:
                        pass
                    cards = await page.query_selector_all("div.b-post")
                    card_count = len(cards)
                    logger.debug("FL.ru page {}: found {} cards", page_num, card_count)

                    if card_count == 0:
                        logger.warning("No cards on FL.ru page {}, stopping", page_num)
                        break

                    for card in cards:
                        try:
                            job = await self._parse_project_card_async(card, page_num)
                            if job:
                                jid = job.get("id", "")
                                if jid not in seen_ids:
                                    seen_ids.add(jid)
                                    jobs.append(job)
                        except Exception as e:
                            logger.debug(
                                "Error parsing FL.ru card on page {}: {}", page_num, e
                            )

                except Exception as e:
                    logger.error("Error fetching FL.ru page {}: {}", page_num, e)
                    break

            await browser.close()

        logger.info(
            "FL.ru collected {} unique tasks from {} pages", len(jobs), self.max_pages
        )
        return jobs

    async def _parse_project_card_async(
        self, card: Any, page_num: int
    ) -> Optional[dict]:
        try:
            title_el = await card.query_selector(
                "h2.b-post__title a[href*='/projects/']"
            )
            if not title_el:
                return None

            title = (await title_el.inner_text()).strip()
            href = await title_el.get_attribute("href") or ""
            job_url = urljoin(self.base_url, href)

            id_match = re.search(r"/projects/(\d+)", href)
            job_id = id_match.group(1) if id_match else str(hash(href))

            desc_el = await card.query_selector(
                "div.b-post__body div.b-post__txt.text-5"
            )
            description = (await desc_el.inner_text()).strip() if desc_el else None

            price_el = await card.query_selector("div.b-post__price span.text-4")
            budget_min, budget_max = None, None
            if price_el:
                price_text = (await price_el.inner_text()).strip()
                budget_min, budget_max = self._parse_fl_price(price_text)

            date_el = await card.query_selector("span.text-gray-opacity-4.text-7")
            posted_at = datetime.now(timezone.utc).replace(tzinfo=None)
            if date_el:
                date_text = (await date_el.inner_text()).strip()
                posted_at = self._parse_relative_date(date_text)

            proposals_el = await card.query_selector(
                "span[data-id='fl-view-count-href']"
            )
            proposals = None
            if proposals_el:
                proposals_text = (await proposals_el.inner_text()).strip()
                match = re.search(r"(\d+)", proposals_text)
                if match:
                    proposals = int(match.group(1))

            return {
                "id": job_id,
                "title": title,
                "description": description,
                "url": job_url,
                "budget_min": budget_min,
                "budget_max": budget_max,
                "currency": "RUB",
                "posted_at": posted_at,
                "proposals": proposals,
                "category": None,
                "skills": [],
                "country": "Russia",
                "rating": None,
                "payment_verified": False,
            }
        except Exception as e:
            logger.debug("Error in _parse_project_card_async: {}", e)
            return None

    def _parse_fl_price(
        self, price_text: str
    ) -> tuple[Optional[float], Optional[float]]:
        if not price_text or "договор" in price_text.lower():
            return None, None

        digits = re.findall(r"[\d\s]+", price_text)
        nums = []
        for d in digits:
            cleaned = d.strip().replace(" ", "").replace("\u00a0", "")
            if cleaned and cleaned.isdigit():
                nums.append(float(cleaned))

        if not nums:
            return None, None
        if len(nums) == 1:
            return nums[0], nums[0]
        return nums[0], nums[-1]

    def _parse_relative_date(self, date_str: str) -> Optional[datetime]:
        if not date_str:
            return None
        date_str = date_str.lower().strip()
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        from datetime import timedelta

        if "минут" in date_str or "минута" in date_str or "секунд" in date_str:
            return now
        if "час" in date_str:
            return now
        if "день" in date_str or "дня" in date_str or "дней" in date_str:
            match = re.search(r"(\d+)", date_str)
            days = int(match.group(1)) if match else 1
            return now - timedelta(days=days)
        if "недел" in date_str:
            match = re.search(r"(\d+)", date_str)
            weeks = int(match.group(1)) if match else 1
            return now - timedelta(weeks=weeks)
        if "месяц" in date_str:
            match = re.search(r"(\d+)", date_str)
            months = int(match.group(1)) if match else 1
            return now - timedelta(days=months * 30)
        if "сегодня" in date_str:
            return now
        if "вчера" in date_str:
            return now - timedelta(days=1)

        from calendar import month_name
        import locale

        try:
            locale.setlocale(locale.LC_TIME, "ru_RU.UTF-8")
        except Exception:
            pass

        ru_months = {
            "января": 1,
            "февраля": 2,
            "марта": 3,
            "апреля": 4,
            "мая": 5,
            "июня": 6,
            "июля": 7,
            "августа": 8,
            "сентября": 9,
            "октября": 10,
            "ноября": 11,
            "декабря": 12,
        }
        for ru_name, num in ru_months.items():
            if ru_name in date_str:
                match = re.search(r"(\d+)\s+" + re.escape(ru_name), date_str)
                if match:
                    day = int(match.group(1))
                    year = now.year
                    return datetime(year, num, day)

        formats = ["%d.%m.%Y", "%Y-%m-%d", "%d %b %Y", "%d %B %Y"]
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        return now

    async def parse_task(self, raw: dict[str, Any]) -> Optional[TaskData]:
        if not raw.get("title"):
            return None
        return TaskData(
            source=self.source_name,
            task_id=raw.get("id", str(hash(raw.get("url", "")))),
            url=raw.get("url", ""),
            title=raw.get("title", "").strip(),
            description=raw.get("description"),
            budget_min=raw.get("budget_min"),
            budget_max=raw.get("budget_max"),
            currency=raw.get("currency", "RUB"),
            posted_at=raw.get("posted_at"),
            proposals_count=raw.get("proposals"),
            category_raw=raw.get("category"),
            technologies=raw.get("skills", []),
            country=raw.get("country", "Russia"),
            client_rating=raw.get("rating"),
            payment_verified=raw.get("payment_verified", False),
        )

    async def normalize(self, task: TaskData) -> None:
        pass
