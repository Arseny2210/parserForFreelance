import re
import json
from typing import Optional, Any
from datetime import datetime, timezone
from urllib.parse import urljoin, urlencode
from loguru import logger
from scrapers.base import BaseScraper, TaskData


class KworkScraper(BaseScraper):
    def __init__(self) -> None:
        super().__init__()
        self.source_name = "kwork"
        self.base_url = "https://kwork.ru"
        self.search_url = "https://kwork.ru/projects"
        self.pages_per_category = 10

    CATEGORIES: dict[str, int] = {
        "it": 11,
        "design": 15,
    }

    async def _collect_raw(self) -> list[dict[str, Any]]:
        logger.info("Fetching Kwork.ru project listings by IT/Design categories")
        jobs = []
        seen_ids: set[str] = set()

        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-gpu",
                ],
            )
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
            )
            page = await context.new_page()
            try:
                from playwright_stealth import Stealth

                stealth = Stealth()
                await stealth.apply_stealth_async(page)
            except Exception:
                pass

            for cat_name, cat_id in self.CATEGORIES.items():
                for page_num in range(1, self.pages_per_category + 1):
                    try:
                        if page_num == 1:
                            url = f"{self.search_url}?c={cat_id}"
                        else:
                            url = f"{self.search_url}?c={cat_id}&page={page_num}"

                        await page.goto(
                            url, wait_until="domcontentloaded", timeout=30000
                        )
                        await page.wait_for_timeout(8000)

                        cards = await page.query_selector_all(
                            "div.want-card.want-card--list"
                        )
                        card_count = len(cards)
                        logger.debug(
                            "Kwork {} page {} (c={}): {} cards",
                            cat_name,
                            page_num,
                            cat_id,
                            card_count,
                        )

                        if card_count == 0:
                            logger.debug(
                                "No more cards for Kwork {} at page {}, stopping",
                                cat_name,
                                page_num,
                            )
                            break

                        for card in cards:
                            try:
                                job = await self._parse_project_card_async(
                                    card, page_num
                                )
                                if job:
                                    jid = job.get("id", "")
                                    if jid not in seen_ids:
                                        seen_ids.add(jid)
                                        jobs.append(job)
                            except Exception as e:
                                logger.debug(
                                    "Error parsing Kwork card on {} page {}: {}",
                                    cat_name,
                                    page_num,
                                    e,
                                )

                    except Exception as e:
                        logger.error(
                            "Error fetching Kwork {} page {}: {}", cat_name, page_num, e
                        )
                        break

            await browser.close()

        logger.info(
            "Kwork collected {} unique tasks from IT/Design categories",
            len(jobs),
        )
        return jobs

    async def _parse_project_card_async(
        self, card: Any, page_num: int
    ) -> Optional[dict]:
        try:
            title_el = await card.query_selector("h1.wants-card__header-title a")
            if not title_el:
                return None

            title = (await title_el.inner_text()).strip()
            href = await title_el.get_attribute("href") or ""
            job_url = urljoin(self.base_url, href)

            id_match = re.search(r"/(?:projects|project|want)/(\d+)", href)
            job_id = id_match.group(1) if id_match else str(hash(href))

            desc_el = await card.query_selector(".wants-card__description-text")
            description = (await desc_el.inner_text()).strip() if desc_el else None

            price_el = await card.query_selector(".wants-card__price")
            budget_min, budget_max = None, None
            if price_el:
                price_text = (await price_el.inner_text()).strip()
                budget_min, budget_max = self._parse_kwork_price(price_text)

            posted_at = datetime.now(timezone.utc).replace(tzinfo=None)

            return {
                "id": job_id,
                "title": title,
                "description": description,
                "url": job_url,
                "budget_min": budget_min,
                "budget_max": budget_max,
                "currency": "RUB",
                "posted_at": posted_at,
                "proposals": None,
                "category": None,
                "skills": [],
                "country": "Russia",
                "rating": None,
                "payment_verified": False,
            }
        except Exception as e:
            logger.debug("Error in _parse_project_card_async: {}", e)
            return None

    def _parse_kwork_price(
        self, price_text: str
    ) -> tuple[Optional[float], Optional[float]]:
        if not price_text:
            return None, None

        digits = re.findall(r"[\d\s]+", price_text)
        nums = []
        for d in digits:
            cleaned = d.strip().replace(" ", "")
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
