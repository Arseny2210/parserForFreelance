"""
Unit tests for the base scraper module.
"""

import pytest
from datetime import datetime
from scrapers.base import BaseScraper, TaskData


class TestTaskData:
    def test_task_data_creation(self) -> None:
        task = TaskData(
            source="test",
            task_id="123",
            url="https://example.com/job/123",
            title="Test Job",
            description="Test description",
            budget_min=100.0,
            budget_max=500.0,
            currency="USD",
            posted_at=datetime(2024, 1, 1),
            proposals_count=5,
            category_raw="Web Development",
            technologies=["Python", "Django"],
            country="US",
            client_rating=4.5,
            payment_verified=True,
        )
        assert task.source == "test"
        assert task.title == "Test Job"
        assert task.budget_min == 100.0
        assert task.technologies == ["Python", "Django"]

    def test_task_data_defaults(self) -> None:
        task = TaskData(
            source="test",
            task_id="456",
            url="https://example.com/job/456",
            title="Another Job",
        )
        assert task.description is None
        assert task.budget_min is None
        assert task.technologies == []
        assert task.payment_verified is None
        assert task.scraped_at is not None

    def test_task_data_to_dict(self) -> None:
        task = TaskData(
            source="test",
            task_id="789",
            url="https://example.com/job/789",
            title="Dict Job",
            technologies=["Python"],
        )
        d = task.to_dict()
        assert d["source"] == "test"
        assert d["technologies"] == ["Python"]
        assert isinstance(d["scraped_at"], datetime)


class MockScraper(BaseScraper):
    def __init__(self) -> None:
        super().__init__()
        self.source_name = "mock"
        self.base_url = "https://mock.example.com"

    async def _collect_raw(self) -> list[dict]:
        return [
            {
                "id": "1",
                "title": "Mock Job 1",
                "description": "A mock job for testing",
                "url": "https://mock.example.com/job/1",
                "budget_min": 100,
                "budget_max": 200,
                "currency": "USD",
                "posted_at": datetime(2024, 6, 1),
                "proposals": 5,
                "category": "Web",
                "skills": ["Python"],
                "country": "US",
                "rating": 4.0,
                "payment_verified": True,
            }
        ]

    async def parse_task(self, raw: dict) -> TaskData:
        return TaskData(
            source=self.source_name,
            task_id=raw.get("id", ""),
            url=raw.get("url", ""),
            title=raw.get("title", ""),
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
        task.normalized_category = "Backend"


@pytest.mark.asyncio
async def test_mock_scraper_collect() -> None:
    scraper = MockScraper()
    tasks = await scraper.collect()
    assert len(tasks) == 1
    assert tasks[0].title == "Mock Job 1"
    assert tasks[0].normalized_category == "Backend"
    await scraper.close()


@pytest.mark.asyncio
async def test_mock_scraper_collect_empty() -> None:
    class EmptyMockScraper(MockScraper):
        async def _collect_raw(self) -> list[dict]:
            return []

    scraper = EmptyMockScraper()
    tasks = await scraper.collect()
    assert len(tasks) == 0
    await scraper.close()
