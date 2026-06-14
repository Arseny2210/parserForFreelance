from abc import ABC, abstractmethod
from typing import Optional, Any
from datetime import datetime
from dataclasses import dataclass, field, asdict
import random
import asyncio
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
from httpx import AsyncClient, HTTPError, RequestError, TimeoutException
from loguru import logger
from core.settings import settings
from bs4 import BeautifulSoup


USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 OPR/111.0.0.0",
]


@dataclass
class TaskData:
    source: str = ""
    task_id: str = ""
    url: str = ""
    title: str = ""
    description: Optional[str] = None
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None
    currency: Optional[str] = None
    posted_at: Optional[datetime] = None
    proposals_count: Optional[int] = None
    category_raw: Optional[str] = None
    technologies: Optional[list[str]] = field(default_factory=list)
    country: Optional[str] = None
    client_rating: Optional[float] = None
    payment_verified: Optional[bool] = None
    normalized_category: Optional[str] = None
    scraped_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        result = {}
        for k, v in asdict(self).items():
            if isinstance(v, datetime):
                result[k] = v
            elif isinstance(v, list):
                result[k] = v
            else:
                result[k] = v
        return result


class BaseScraper(ABC):
    def __init__(self) -> None:
        self.source_name: str = ""
        self.base_url: str = ""
        self.tasks: list[TaskData] = []
        self._session: Optional[AsyncClient] = None

    async def _get_session(self) -> AsyncClient:
        if self._session is None or self._session.is_closed:
            headers = self._get_headers()
            proxy = settings.proxy_url if settings.proxy_enabled else None
            self._session = AsyncClient(
                headers=headers,
                timeout=settings.request_timeout,
                proxy=proxy,
                follow_redirects=True,
                http2=True,
            )
        return self._session

    def _get_headers(self) -> dict[str, str]:
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,ru;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        if settings.user_agent_rotation_enabled:
            headers["User-Agent"] = random.choice(USER_AGENTS)
        return headers

    async def _rotate_user_agent(self) -> None:
        if (
            settings.user_agent_rotation_enabled
            and self._session
            and not self._session.is_closed
        ):
            self._session.headers.update({"User-Agent": random.choice(USER_AGENTS)})

    async def _throttle(self) -> None:
        delay = settings.throttle_delay + random.uniform(0, 0.5)
        await asyncio.sleep(delay)

    @retry(
        stop=stop_after_attempt(settings.max_retries),
        wait=wait_exponential(
            multiplier=settings.exponential_backoff_base,
            max=settings.exponential_backoff_max,
        ),
        retry=retry_if_exception_type((RequestError, TimeoutException, HTTPError)),
        reraise=True,
    )
    async def _fetch_page(self, url: str, use_playwright: bool = False) -> str:
        if use_playwright:
            return await self._fetch_with_playwright(url)

        await self._rotate_user_agent()
        session = await self._get_session()
        response = await session.get(url)
        response.raise_for_status()
        return response.text

    async def _fetch_with_playwright(self, url: str) -> str:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=random.choice(USER_AGENTS),
                viewport={"width": 1920, "height": 1080},
            )
            page = await context.new_page()
            try:
                try:
                    await page.goto(
                        url,
                        wait_until="load",
                        timeout=settings.request_timeout * 1000,
                    )
                    await page.wait_for_timeout(2000)
                except Exception:
                    await page.goto(
                        url,
                        wait_until="domcontentloaded",
                        timeout=settings.request_timeout * 1000,
                    )
                    await page.wait_for_timeout(3000)
                content = await page.content()
            finally:
                await browser.close()
        return content

    def _parse_html(self, html: str) -> BeautifulSoup:
        return BeautifulSoup(html, "html.parser")

    async def collect(self) -> list[TaskData]:
        logger.info("Starting collection from {}", self.source_name)
        raw_data = await self._collect_raw()
        for item in raw_data:
            task = await self.parse_task(item)
            if task:
                await self.normalize(task)
                self.tasks.append(task)
        logger.info("Collected {} tasks from {}", len(self.tasks), self.source_name)
        return self.tasks

    @abstractmethod
    async def _collect_raw(self) -> list[Any]:
        pass

    @abstractmethod
    async def parse_task(self, raw: Any) -> Optional[TaskData]:
        pass

    @abstractmethod
    async def normalize(self, task: TaskData) -> None:
        pass

    async def close(self) -> None:
        if self._session and not self._session.is_closed:
            await self._session.aclose()
