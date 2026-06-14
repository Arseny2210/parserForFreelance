import re
import json
from typing import Optional, Any
from datetime import datetime
from urllib.parse import urljoin
from loguru import logger
from scrapers.base import BaseScraper, TaskData


class FreelancerScraper(BaseScraper):
    def __init__(self) -> None:
        super().__init__()
        self.source_name = "freelancer"
        self.base_url = "https://www.freelancer.com"
        self.api_url = "https://www.freelancer.com/api/projects/0.1/projects/"

    async def _collect_raw(self) -> list[dict[str, Any]]:
        logger.info("Fetching Freelancer.com job listings")
        jobs = []
        page = 1
        max_pages = 10

        while page <= max_pages:
            try:
                url = f"{self.api_url}?limit=50&offset={(page - 1) * 50}&job_details=true&user_details=true"
                html = await self._fetch_page(url)
                try:
                    data = json.loads(html)
                    projects = data.get("result", {}).get("projects", [])
                    if not projects:
                        break

                    for proj in projects:
                        job = self._parse_api_project(proj)
                        if job:
                            jobs.append(job)
                except json.JSONDecodeError:
                    soup = self._parse_html(html)
                    project_cards = soup.select(
                        "div.ProjectList-item, div.project-card, div[class*='project']"
                    )
                    for card in project_cards:
                        job = self._parse_project_card(card)
                        if job:
                            jobs.append(job)

                await self._throttle()
                page += 1
            except Exception as e:
                logger.error("Error fetching Freelancer page {}: {}", page, e)
                break

        return jobs

    def _parse_api_project(self, proj: dict) -> Optional[dict]:
        try:
            title = proj.get("title", "")
            if not title:
                return None

            project_id = str(proj.get("id", ""))
            budget = proj.get("budget", {})
            currency = (
                budget.get("currency", {}).get("code", "USD")
                if isinstance(budget, dict)
                else "USD"
            )

            min_budget = None
            max_budget = None
            if isinstance(budget, dict):
                min_budget = budget.get("minimum")
                max_budget = budget.get("maximum")

            posted_str = proj.get("submitdate") or proj.get("posted_date")
            posted_at = None
            if posted_str:
                try:
                    posted_at = datetime.fromisoformat(
                        posted_str.replace("Z", "+00:00")
                    )
                except (ValueError, AttributeError):
                    posted_at = self._parse_relative_date(str(posted_str))

            bids = proj.get("bid_count") or proj.get("bids", {}).get("count")
            bids_count = int(bids) if bids else None

            owner = proj.get("owner", {}) or proj.get("user", {})
            country = None
            rating = None
            if isinstance(owner, dict):
                country = owner.get("country", {}).get("name") or owner.get(
                    "location", {}
                ).get("country")
                rating = owner.get("rating") or owner.get("reputation")

            skills = []
            for skill in proj.get("jobs", []) or proj.get("skills", []):
                if isinstance(skill, dict):
                    skills.append(skill.get("name", ""))
                elif isinstance(skill, str):
                    skills.append(skill)

            return {
                "id": project_id,
                "title": title,
                "description": proj.get("description")
                or proj.get("preview_description"),
                "url": urljoin(self.base_url, f"/projects/{project_id}"),
                "budget_min": min_budget,
                "budget_max": max_budget,
                "currency": currency,
                "posted_at": posted_at,
                "proposals": bids_count,
                "category": proj.get("category", {}).get("name")
                if isinstance(proj.get("category"), dict)
                else None,
                "skills": skills,
                "country": country,
                "rating": rating,
                "payment_verified": proj.get("verified")
                or proj.get("payment_verified", False),
            }
        except Exception as e:
            logger.debug("Error parsing Freelancer API project: {}", e)
            return None

    def _parse_project_card(self, card: Any) -> Optional[dict]:
        try:
            title_el = card.select_one(
                "a.ProjectInfo-title, h3 a, a[class*='title'], a[class*='project']"
            )
            if not title_el:
                return None

            title = title_el.get_text(strip=True)
            href = title_el.get("href", "")
            job_url = urljoin(self.base_url, href)

            id_match = re.search(r"/projects/(\d+)", href)
            project_id = id_match.group(1) if id_match else str(hash(href))

            desc_el = card.select_one(
                "div.ProjectInfo-description, p.description, div[class*='desc']"
            )
            description = desc_el.get_text(strip=True) if desc_el else None

            budget_el = card.select_one(
                "span.ProjectInfo-budget, span.budget, span[class*='budget']"
            )
            budget_min, budget_max = None, None
            if budget_el:
                budget_str = budget_el.get_text(strip=True)
                budget_min, budget_max = self._parse_budget(budget_str)

            posted_el = card.select_one(
                "span.ProjectInfo-date, span.date, span[class*='date'], span[class*='time']"
            )
            posted_at = None
            if posted_el:
                posted_at = self._parse_relative_date(posted_el.get_text(strip=True))

            bids_el = card.select_one(
                "span.ProjectInfo-bids, span.bids, span[class*='bid']"
            )
            proposals = None
            if bids_el:
                bids_text = bids_el.get_text(strip=True)
                match = re.search(r"(\d+)", bids_text)
                if match:
                    proposals = int(match.group(1))

            skills_els = card.select(
                "a.ProjectInfo-tag, span.tag, a[class*='skill'], a[class*='tag']"
            )
            skills = [s.get_text(strip=True) for s in skills_els]

            country_el = card.select_one(
                "span.ProjectInfo-location, span.location, span[class*='country']"
            )
            country = country_el.get_text(strip=True) if country_el else None

            return {
                "id": project_id,
                "title": title,
                "description": description,
                "url": job_url,
                "budget_min": budget_min,
                "budget_max": budget_max,
                "currency": "USD",
                "posted_at": posted_at,
                "proposals": proposals,
                "category": None,
                "skills": skills,
                "country": country,
                "rating": None,
                "payment_verified": False,
            }
        except Exception as e:
            logger.debug("Error parsing Freelancer card: {}", e)
            return None

    def _parse_budget(self, budget_str: str) -> tuple[Optional[float], Optional[float]]:
        if not budget_str:
            return None, None
        budget_str = (
            budget_str.replace("$", "")
            .replace(",", "")
            .replace("EUR", "")
            .replace("USD", "")
            .strip()
        )
        if "-" in budget_str:
            parts = budget_str.split("-")
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
        formats = [
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%d %b %Y",
            "%b %d, %Y",
            "%d/%m/%Y",
        ]
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
