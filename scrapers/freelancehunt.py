import re
import json
from typing import Optional, Any
from datetime import datetime
from urllib.parse import urljoin, urlencode
from loguru import logger
from scrapers.base import BaseScraper, TaskData


class FreelancehuntScraper(BaseScraper):
    def __init__(self) -> None:
        super().__init__()
        self.source_name = "freelancehunt"
        self.base_url = "https://freelancehunt.com"
        self.search_url = "https://freelancehunt.com/projects"

    async def _collect_raw(self) -> list[dict[str, Any]]:
        logger.info("Fetching Freelancehunt.com job listings")
        jobs = []
        page = 1
        max_pages = 10

        while page <= max_pages:
            try:
                params = {"page": page, "sort": "recent"}
                url = f"{self.search_url}?{urlencode(params)}"
                html = await self._fetch_page(url, use_playwright=True)
                soup = self._parse_html(html)

                project_cards = soup.select(
                    "div.project-card, div.project, div[class*='project'], "
                    "li.project-item, div[class*='contest'], article.project"
                )

                if not project_cards:
                    scripts = soup.select(
                        "script[type='application/ld+json'], script[data-initial-state]"
                    )
                    for script in scripts:
                        if script.string:
                            try:
                                data = json.loads(script.string)
                                extracted = self._extract_from_json_ld(data)
                                jobs.extend(extracted)
                            except (json.JSONDecodeError, TypeError):
                                continue

                for card in project_cards:
                    job = self._parse_project_card(card)
                    if job:
                        jobs.append(job)

                await self._throttle()
                page += 1

                pagination = soup.select_one(
                    "a.pagination-next, a.next, a[rel='next'], li.next a, a.pg-next"
                )
                if not pagination:
                    break
            except Exception as e:
                logger.error("Error fetching Freelancehunt page {}: {}", page, e)
                break

        return jobs

    def _extract_from_json_ld(self, data: Any) -> list[dict]:
        jobs = []
        try:
            items = data if isinstance(data, list) else [data]
            for item in items:
                if isinstance(item, dict) and item.get("title"):
                    title = item.get("title", "")
                    description = item.get("description", "")

                    budget_str = (
                        item.get("baseSalary", {}).get("value", {}).get("value", "")
                    )
                    budget_min, budget_max = None, None
                    currency = "UAH"
                    if budget_str:
                        try:
                            budget_val = float(budget_str)
                            budget_min = budget_max = budget_val
                        except (ValueError, TypeError):
                            pass
                        currency = (
                            item.get("baseSalary", {})
                            .get("value", {})
                            .get("currency", "UAH")
                        )

                    date_posted = item.get("datePosted")
                    posted_at = None
                    if date_posted:
                        try:
                            posted_at = datetime.fromisoformat(
                                date_posted.replace("Z", "+00:00")
                            )
                        except (ValueError, AttributeError):
                            pass

                    url = item.get("url", "")
                    if url and not url.startswith("http"):
                        url = urljoin(self.base_url, url)

                    identifier = (
                        item.get("@id") or item.get("identifier") or str(hash(url))
                    )

                    skills = item.get("skills", [])
                    if isinstance(skills, str):
                        skills = [s.strip() for s in skills.split(",")]

                    jobs.append(
                        {
                            "id": str(identifier),
                            "title": title,
                            "description": description,
                            "url": url,
                            "budget_min": budget_min,
                            "budget_max": budget_max,
                            "currency": currency,
                            "posted_at": posted_at,
                            "proposals": None,
                            "category": item.get(
                                "occupationalCategory", item.get("category")
                            ),
                            "skills": skills,
                            "country": "Ukraine",
                            "rating": None,
                            "payment_verified": False,
                        }
                    )
        except Exception as e:
            logger.debug("Error extracting from Freelancehunt JSON: {}", e)
        return jobs

    def _parse_project_card(self, card: Any) -> Optional[dict]:
        try:
            title_el = card.select_one(
                "a[class*='title'], a[class*='name'], h2 a, h3 a, "
                "div[class*='title'] a, a[href*='/projects/']"
            )
            if not title_el:
                return None

            title = title_el.get_text(strip=True)
            href = title_el.get("href", "")
            job_url = urljoin(self.base_url, href) if href else ""

            id_match = re.search(r"/(?:projects|project)/(\d+)", href)
            job_id = id_match.group(1) if id_match else str(hash(href))

            desc_el = card.select_one(
                "div[class*='description'], div[class*='desc'], "
                "p[class*='desc'], div.project-description"
            )
            description = desc_el.get_text(strip=True) if desc_el else None

            budget_el = card.select_one(
                "span[class*='price'], span[class*='budget'], "
                "div[class*='price'] span, span[class*='cost'], "
                "div.budget span"
            )
            budget_min, budget_max = None, None
            currency = "UAH"
            if budget_el:
                budget_text = budget_el.get_text(strip=True)
                budget_min, budget_max, currency = self._parse_budget(budget_text)

            posted_el = card.select_one(
                "span[class*='date'], span[class*='time'], "
                "div[class*='date'], span.text-muted, "
                "span[class*='published']"
            )
            posted_at = None
            if posted_el:
                posted_at = self._parse_relative_date(posted_el.get_text(strip=True))

            proposals_el = card.select_one(
                "span[class*='proposal'], span[class*='bid'], "
                "span[class*='response'], span[class*='application']"
            )
            proposals = None
            if proposals_el:
                match = re.search(r"(\d+)", proposals_el.get_text(strip=True))
                if match:
                    proposals = int(match.group(1))

            skills = []
            skills_els = card.select(
                "a[class*='tag'], span[class*='tag'], "
                "span.tag, a[class*='skill'], li.tag a"
            )
            for skill_el in skills_els:
                skills.append(skill_el.get_text(strip=True))

            category_el = card.select_one(
                "a[class*='category'], span[class*='category'], "
                "div[class*='category'] a"
            )
            category = category_el.get_text(strip=True) if category_el else None

            return {
                "id": job_id,
                "title": title,
                "description": description,
                "url": job_url,
                "budget_min": budget_min,
                "budget_max": budget_max,
                "currency": currency,
                "posted_at": posted_at,
                "proposals": proposals,
                "category": category,
                "skills": skills,
                "country": "Ukraine",
                "rating": None,
                "payment_verified": False,
            }
        except Exception as e:
            logger.debug("Error parsing Freelancehunt card: {}", e)
            return None

    def _parse_budget(
        self, budget_text: str
    ) -> tuple[Optional[float], Optional[float], str]:
        if not budget_text:
            return None, None, "UAH"

        budget_text = budget_text.strip()
        currency = "UAH"

        if "$" in budget_text or "usd" in budget_text.lower():
            currency = "USD"
        elif "€" in budget_text or "eur" in budget_text.lower():
            currency = "EUR"
        elif (
            "₴" in budget_text
            or "uah" in budget_text.lower()
            or "грн" in budget_text.lower()
        ):
            currency = "UAH"
        elif "₽" in budget_text or "руб" in budget_text.lower():
            currency = "RUB"

        budget_text = re.sub(
            r"[₴$€₽]|\bгрн\b|\bруб\b|\buah\b|\busd\b|\beur\b",
            "",
            budget_text,
            flags=re.IGNORECASE,
        ).strip()

        if "договор" in budget_text.lower():
            return None, None, currency

        if "-" in budget_text or "–" in budget_text:
            parts = re.split(r"[-–]", budget_text)
            try:
                low = float(parts[0].strip().replace(" ", "").replace(",", "."))
                high = (
                    float(parts[1].strip().replace(" ", "").replace(",", "."))
                    if len(parts) > 1
                    else None
                )
                return low, high, currency
            except (ValueError, IndexError):
                pass

        try:
            val = float(budget_text.replace(" ", "").replace(",", "."))
            return val, val, currency
        except ValueError:
            pass

        return None, None, currency

    def _parse_relative_date(self, date_str: str) -> Optional[datetime]:
        if not date_str:
            return None
        date_str = date_str.lower().strip()
        now = datetime.utcnow()
        from datetime import timedelta

        if "минут" in date_str or "хвилин" in date_str or "секунд" in date_str:
            return now
        if "час" in date_str or "годин" in date_str:
            return now
        if (
            "день" in date_str
            or "дня" in date_str
            or "днів" in date_str
            or "дней" in date_str
        ):
            match = re.search(r"(\d+)", date_str)
            days = int(match.group(1)) if match else 1
            return now - timedelta(days=days)
        if "недел" in date_str or "тиждн" in date_str:
            match = re.search(r"(\d+)", date_str)
            weeks = int(match.group(1)) if match else 1
            return now - timedelta(weeks=weeks)
        if "месяц" in date_str or "місяц" in date_str:
            match = re.search(r"(\d+)", date_str)
            months = int(match.group(1)) if match else 1
            return now - timedelta(days=months * 30)
        if "сегодня" in date_str or "сьогодні" in date_str:
            return now
        if "вчера" in date_str or "вчора" in date_str:
            return now - timedelta(days=1)
        formats = ["%d.%m.%Y", "%Y-%m-%d", "%d %b %Y", "%d %B %Y", "%Y-%m-%dT%H:%M:%S"]
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
            currency=raw.get("currency", "UAH"),
            posted_at=raw.get("posted_at"),
            proposals_count=raw.get("proposals"),
            category_raw=raw.get("category"),
            technologies=raw.get("skills", []),
            country=raw.get("country", "Ukraine"),
            client_rating=raw.get("rating"),
            payment_verified=raw.get("payment_verified", False),
        )

    async def normalize(self, task: TaskData) -> None:
        pass
