import re
import json
from typing import Optional, Any
from datetime import datetime
from urllib.parse import urljoin
from loguru import logger
from scrapers.base import BaseScraper, TaskData


class GuruScraper(BaseScraper):
    def __init__(self) -> None:
        super().__init__()
        self.source_name = "guru"
        self.base_url = "https://www.guru.com"
        self.search_url = "https://www.guru.com/d/jobs/"

    async def _collect_raw(self) -> list[dict[str, Any]]:
        logger.info("Fetching Guru.com job listings")
        jobs = []
        page = 1
        max_pages = 10

        while page <= max_pages:
            try:
                url = f"{self.search_url}?page={page}&sort=relevance"
                html = await self._fetch_page(url)
                soup = self._parse_html(html)
                job_cards = soup.select(
                    "div.job-item, div.job-card, div[class*='job'] div.card, section[class*='job']"
                )

                if not job_cards:
                    scripts = soup.select(
                        "script[type='application/ld+json'], script[data-initial-state]"
                    )
                    for script in scripts:
                        if script.string:
                            try:
                                data = json.loads(script.string)
                                items = data if isinstance(data, list) else [data]
                                for item in items:
                                    job = self._parse_json_ld(item)
                                    if job:
                                        jobs.append(job)
                            except (json.JSONDecodeError, AttributeError):
                                continue

                for card in job_cards:
                    job = self._parse_job_card(card)
                    if job:
                        jobs.append(job)

                await self._throttle()
                page += 1

                next_btn = soup.select_one(
                    "a[rel='next'], a.next, li.next a, a.pagination-next"
                )
                if not next_btn:
                    break
            except Exception as e:
                logger.error("Error fetching Guru page {}: {}", page, e)
                break

        return jobs

    def _parse_json_ld(self, data: dict) -> Optional[dict]:
        try:
            if not data.get("title") or "@type" not in data:
                return None
            title = data.get("title", "")
            description = data.get("description", "")

            budget_str = data.get("baseSalary", {}).get("value", {}).get("value", "")
            budget_min, budget_max = None, None
            if budget_str:
                try:
                    budget_min = budget_max = float(budget_str)
                except (ValueError, TypeError):
                    pass

            date_posted = data.get("datePosted")
            posted_at = None
            if date_posted:
                try:
                    posted_at = datetime.fromisoformat(
                        date_posted.replace("Z", "+00:00")
                    )
                except (ValueError, AttributeError):
                    pass

            url = data.get("url", "")
            if url and not url.startswith("http"):
                url = urljoin(self.base_url, url)

            skills = data.get("skills", [])
            if isinstance(skills, str):
                skills = [s.strip() for s in skills.split(",")]

            return {
                "id": str(data.get("@id", data.get("identifier", hash(url)))),
                "title": title,
                "description": description,
                "url": url,
                "budget_min": budget_min,
                "budget_max": budget_max,
                "currency": data.get("baseSalary", {})
                .get("value", {})
                .get("currency", "USD"),
                "posted_at": posted_at,
                "proposals": None,
                "category": data.get("occupationalCategory", data.get("category")),
                "skills": skills,
                "country": data.get("applicantLocationRequirements", {}).get("name")
                if isinstance(data.get("applicantLocationRequirements"), dict)
                else None,
                "rating": None,
                "payment_verified": False,
            }
        except Exception as e:
            logger.debug("Error parsing Guru JSON-LD: {}", e)
            return None

    def _parse_job_card(self, card: Any) -> Optional[dict]:
        try:
            title_el = card.select_one(
                "a[class*='title'], h2 a, h3 a, div[class*='title'] a"
            )
            if not title_el:
                title_el = card.select_one("a[href*='/job/'], a[href*='/projects/']")
            if not title_el:
                return None

            title = title_el.get_text(strip=True)
            href = title_el.get("href", "")
            job_url = urljoin(self.base_url, href) if href else ""

            id_match = re.search(r"/(?:job|project)/(\d+)", href)
            job_id = id_match.group(1) if id_match else str(hash(href))

            desc_el = card.select_one(
                "div[class*='desc'], p[class*='desc'], div[class*='description']"
            )
            description = desc_el.get_text(strip=True) if desc_el else None

            budget_el = card.select_one(
                "span[class*='budget'], span[class*='price'], div[class*='budget'] span, span[class*='amount']"
            )
            budget_min, budget_max = None, None
            if budget_el:
                budget_str = budget_el.get_text(strip=True)
                budget_min, budget_max = self._parse_budget(budget_str)

            posted_el = card.select_one(
                "span[class*='date'], span[class*='time'], div[class*='date'], span.text-muted"
            )
            posted_at = None
            if posted_el:
                posted_at = self._parse_relative_date(posted_el.get_text(strip=True))

            skills = []
            skills_els = card.select(
                "a[class*='skill'], a[class*='tag'], span[class*='skill'], span[class*='tag']"
            )
            for skill_el in skills_els:
                skills.append(skill_el.get_text(strip=True))

            proposals_el = card.select_one(
                "span[class*='proposal'], span[class*='bid'], div[class*='proposal'] span"
            )
            proposals = None
            if proposals_el:
                match = re.search(r"(\d+)", proposals_el.get_text(strip=True))
                if match:
                    proposals = int(match.group(1))

            category_el = card.select_one(
                "span[class*='category'], a[class*='category'], div[class*='category'] span"
            )
            category = category_el.get_text(strip=True) if category_el else None

            country_el = card.select_one(
                "span[class*='location'], span[class*='country'], div[class*='location'] span"
            )
            country = country_el.get_text(strip=True) if country_el else None

            return {
                "id": job_id,
                "title": title,
                "description": description,
                "url": job_url,
                "budget_min": budget_min,
                "budget_max": budget_max,
                "currency": "USD",
                "posted_at": posted_at,
                "proposals": proposals,
                "category": category,
                "skills": skills,
                "country": country,
                "rating": None,
                "payment_verified": False,
            }
        except Exception as e:
            logger.debug("Error parsing Guru card: {}", e)
            return None

    def _parse_budget(self, budget_str: str) -> tuple[Optional[float], Optional[float]]:
        if not budget_str:
            return None, None
        budget_str = (
            budget_str.replace("$", "")
            .replace(",", "")
            .replace("USD", "")
            .replace("EUR", "")
            .strip()
        )
        if "-" in budget_str or "–" in budget_str:
            parts = re.split(r"[-–]", budget_str)
            try:
                return float(parts[0].strip()), float(parts[1].strip())
            except (ValueError, IndexError):
                pass
        try:
            val = float(budget_str)
            return val, val
        except ValueError:
            return None, None

    def _parse_relative_date(self, date_str: str) -> Optional[datetime]:
        if not date_str:
            return None
        date_str = date_str.lower().strip()
        now = datetime.utcnow()
        from datetime import timedelta

        if "minute" in date_str:
            return now
        if "hour" in date_str:
            return now
        if "day" in date_str:
            match = re.search(r"(\d+)", date_str)
            days = int(match.group(1)) if match else 1
            return now - timedelta(days=days)
        if "week" in date_str:
            match = re.search(r"(\d+)", date_str)
            weeks = int(match.group(1)) if match else 1
            return now - timedelta(weeks=weeks)
        if "month" in date_str:
            match = re.search(r"(\d+)", date_str)
            months = int(match.group(1)) if match else 1
            return now - timedelta(days=months * 30)
        formats = ["%Y-%m-%d", "%d %b %Y", "%b %d, %Y", "%d/%m/%Y", "%m/%d/%Y"]
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
            currency=raw.get("currency", "USD"),
            posted_at=raw.get("posted_at"),
            proposals_count=raw.get("proposals"),
            category_raw=raw.get("category"),
            technologies=raw.get("skills", []),
            country=raw.get("country"),
            client_rating=raw.get("rating"),
            payment_verified=raw.get("payment_verified", False),
        )

    async def normalize(self, task: TaskData) -> None:
        pass
