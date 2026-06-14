import re
from typing import Optional, Any
from datetime import datetime
from urllib.parse import urljoin
from loguru import logger
from scrapers.base import BaseScraper, TaskData


class UpworkScraper(BaseScraper):
    def __init__(self) -> None:
        super().__init__()
        self.source_name = "upwork"
        self.base_url = "https://www.upwork.com"
        self.search_url = "https://www.upwork.com/search/jobs/"

    async def _collect_raw(self) -> list[dict[str, Any]]:
        logger.info("Fetching Upwork job listings")
        jobs = []
        page = 1
        max_pages = 5

        while page <= max_pages:
            url = f"{self.search_url}?page={page}&sort=recency&per_page=50"
            try:
                html = await self._fetch_page(url, use_playwright=True)
                soup = self._parse_html(html)
                job_cards = soup.select(
                    "article[data-test='JobTile'], section[data-test='JobTile'], div.up-card-section"
                )

                if not job_cards:
                    job_cards = soup.select(
                        "section.job-tile, div.job-tile, div[data-ev-job-oid]"
                    )

                if not job_cards:
                    scripts = soup.select("script#__NEXT_DATA__")
                    if scripts:
                        import json

                        data = json.loads(scripts[0].string)
                        try:
                            search_results = data["props"]["pageProps"][
                                "searchResults"
                            ]["jobs"]
                            for job in search_results:
                                jobs.append(
                                    {
                                        "id": job.get("id", ""),
                                        "title": job.get("title", ""),
                                        "description": job.get("description", ""),
                                        "url": urljoin(
                                            self.base_url, f"/jobs/{job.get('id')}"
                                        ),
                                        "budget": job.get("budget"),
                                        "currency": "USD",
                                        "posted_at": job.get("publishedOnDate"),
                                        "proposals": job.get("proposalsTier", {}).get(
                                            "total"
                                        ),
                                        "category": job.get("category", ""),
                                        "skills": job.get("skills", []),
                                        "country": job.get("client", {})
                                        .get("country", {})
                                        .get("name"),
                                        "rating": job.get("client", {})
                                        .get("feedback", {})
                                        .get("rating"),
                                        "payment_verified": job.get("client", {})
                                        .get("paymentVerificationStatus", {})
                                        .get("verified"),
                                    }
                                )
                        except (KeyError, TypeError):
                            pass

                for card in job_cards:
                    job_data = self._parse_job_card(card)
                    if job_data:
                        jobs.append(job_data)

                await self._throttle()
                page += 1

                next_btn = soup.select_one(
                    "a[data-test='pagination-next'], a.pagination-next, a.next"
                )
                if not next_btn:
                    break
            except Exception as e:
                logger.error("Error fetching Upwork page {}: {}", page, e)
                break

        return jobs

    def _parse_job_card(self, card: Any) -> Optional[dict[str, Any]]:
        try:
            title_el = card.select_one(
                "a[data-test*='job-title'], h2 a, h3 a, a[data-ev-label='job_title']"
            )
            if not title_el:
                return None

            title = title_el.get_text(strip=True)
            job_url = urljoin(self.base_url, title_el.get("href", ""))

            job_id = ""
            id_match = re.search(r"~([a-f0-9]{16,})", job_url)
            if id_match:
                job_id = id_match.group(1)

            desc_el = card.select_one(
                "div[data-test='description'], p.mb-0, span[data-test='description']"
            )
            description = desc_el.get_text(strip=True) if desc_el else None

            budget_str = ""
            budget_el = card.select_one(
                "span[data-test='budget'], strong[data-test='budget'], div.budget, span.budget"
            )
            if budget_el:
                budget_str = budget_el.get_text(strip=True)

            budget_min, budget_max = self._parse_budget(budget_str)

            posted_str = ""
            posted_el = card.select_one(
                "span[data-test='posted-on'], span.text-muted, span[data-qa='posted-on']"
            )
            if posted_el:
                posted_str = posted_el.get_text(strip=True)

            posted_at = self._parse_posted_date(posted_str)

            proposals_str = ""
            proposals_el = card.select_one(
                "span[data-test='proposals'], span[data-qa='proposals'], span.text-muted.mt-0"
            )
            if proposals_el:
                proposals_str = proposals_el.get_text(strip=True)

            proposals_count = self._parse_proposals(proposals_str)

            skills = []
            skills_els = card.select(
                "a[data-test*='skill-tag'], span.skill-tag, div[data-test='skills'] a"
            )
            for skill_el in skills_els:
                skills.append(skill_el.get_text(strip=True))

            country_el = card.select_one(
                "span[data-test='client-country'], span[data-qa='client-country'], strong[data-test='location']"
            )
            country = country_el.get_text(strip=True) if country_el else None

            rating_el = card.select_one(
                "span[data-test='rating'], span[data-qa='rating'], span.rating"
            )
            rating = None
            if rating_el:
                try:
                    rating = float(rating_el.get_text(strip=True))
                except ValueError:
                    pass

            payment_el = card.select_one(
                "span[data-test='payment-verified'], span[data-qa='payment-verified'], span.payment-verified"
            )
            payment_verified = payment_el is not None

            category_el = card.select_one(
                "a[data-test='category'], span[data-test='category'], span.category"
            )
            category = category_el.get_text(strip=True) if category_el else None

            return {
                "id": job_id,
                "title": title,
                "description": description,
                "url": job_url,
                "budget_min": budget_min,
                "budget_max": budget_max,
                "currency": "USD",
                "posted_at": posted_at,
                "proposals": proposals_count,
                "category": category,
                "skills": skills,
                "country": country,
                "rating": rating,
                "payment_verified": payment_verified,
            }
        except Exception as e:
            logger.debug("Error parsing Upwork job card: {}", e)
            return None

    def _parse_budget(self, budget_str: str) -> tuple[Optional[float], Optional[float]]:
        if not budget_str:
            return None, None

        budget_str = budget_str.replace("$", "").replace(",", "").strip()

        if "-" in budget_str or "–" in budget_str:
            parts = re.split(r"[-–]", budget_str)
            try:
                low = float(parts[0].strip())
                high = float(parts[1].strip()) if len(parts) > 1 else None
                return low, high
            except ValueError:
                pass

        hourly_match = re.search(
            r"(\d+\.?\d*)\s*[-–]\s*(\d+\.?\d*)\s*/hr", budget_str, re.IGNORECASE
        )
        if hourly_match:
            low = float(hourly_match.group(1))
            high = float(hourly_match.group(2))
            return low, high

        try:
            val = float(budget_str)
            return val, val
        except ValueError:
            pass

        return None, None

    def _parse_posted_date(self, date_str: str) -> Optional[datetime]:
        if not date_str:
            return None

        date_str = date_str.lower().strip()

        now = datetime.utcnow()

        if "minute" in date_str:
            minutes = (
                int(re.search(r"(\d+)", date_str).group(1))
                if re.search(r"(\d+)", date_str)
                else 1
            )
            return now.replace(second=0, microsecond=0)

        if "hour" in date_str:
            hours = (
                int(re.search(r"(\d+)", date_str).group(1))
                if re.search(r"(\d+)", date_str)
                else 1
            )
            from datetime import timedelta

            return now - timedelta(hours=hours)

        if "day" in date_str or "days" in date_str:
            days = (
                int(re.search(r"(\d+)", date_str).group(1))
                if re.search(r"(\d+)", date_str)
                else 1
            )
            from datetime import timedelta

            return now - timedelta(days=days)

        if "week" in date_str:
            weeks = (
                int(re.search(r"(\d+)", date_str).group(1))
                if re.search(r"(\d+)", date_str)
                else 1
            )
            from datetime import timedelta

            return now - timedelta(weeks=weeks)

        if "month" in date_str:
            months = (
                int(re.search(r"(\d+)", date_str).group(1))
                if re.search(r"(\d+)", date_str)
                else 1
            )
            from datetime import timedelta

            return now - timedelta(days=months * 30)

        formats = [
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%B %d, %Y",
            "%b %d, %Y",
            "%d/%m/%Y",
            "%m/%d/%Y",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        return now

    def _parse_proposals(self, proposals_str: str) -> Optional[int]:
        if not proposals_str:
            return None
        match = re.search(r"(\d+)", proposals_str)
        if match:
            return int(match.group(1))
        if "less" in proposals_str.lower() or "none" in proposals_str.lower():
            return 0
        return None

    async def parse_task(self, raw: dict[str, Any]) -> Optional[TaskData]:
        if not raw.get("title"):
            return None

        return TaskData(
            source=self.source_name,
            task_id=raw.get("id", "") or str(hash(raw.get("url", ""))),
            url=raw.get("url", ""),
            title=raw.get("title", "").strip(),
            description=raw.get("description"),
            budget_min=raw.get("budget_min") or raw.get("budget", {}).get("minimum"),
            budget_max=raw.get("budget_max") or raw.get("budget", {}).get("maximum"),
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
