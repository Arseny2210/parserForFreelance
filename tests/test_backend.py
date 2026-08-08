"""
Tests for the FastAPI backend filter logic (Kwork priority, sorting, filters).
"""

import pytest
from datetime import datetime, timedelta

from backend.service import MarketService


@pytest.fixture()
def service() -> MarketService:
    now = datetime.now()
    svc = MarketService()
    svc.tasks = [
        {
            "task_id": "k1",
            "source": "kwork",
            "title": "Django сайт",
            "normalized_category": "Backend",
            "budget_min": 30000,
            "budget_max": 50000,
            "proposals_count": 20,
            "posted_at": now - timedelta(hours=2),
            "technologies": ["Django"],
        },
        {
            "task_id": "k2",
            "source": "kwork",
            "title": "Верстка лендинга",
            "normalized_category": "Frontend",
            "budget_min": 10000,
            "budget_max": 20000,
            "proposals_count": 40,
            "posted_at": now - timedelta(hours=26),
            "technologies": ["HTML"],
        },
        {
            "task_id": "f1",
            "source": "fl",
            "title": "React приложение",
            "normalized_category": "Frontend",
            "budget_min": 80000,
            "budget_max": 120000,
            "proposals_count": 5,
            "posted_at": now - timedelta(hours=5),
            "technologies": ["React"],
        },
        {
            "task_id": "x1",
            "source": "upwork",
            "title": "Excel отчёт",
            "normalized_category": "Data Analytics",
            "budget_min": None,
            "budget_max": None,
            "proposals_count": None,
            "posted_at": now - timedelta(hours=1),
            "technologies": [],
        },
    ]
    return svc


class TestKworkPriority:
    def test_kwork_comes_first(self, service: MarketService) -> None:
        result = service.filter_tasks(sort="priority")
        sources = [t["source"] for t in result]
        assert sources[0] == "kwork"
        assert sources[1] == "kwork"
        assert sources[2] == "fl"

    def test_newest_first_within_source(self, service: MarketService) -> None:
        result = service.filter_tasks(sort="priority")
        kwork = [t for t in result if t["source"] == "kwork"]
        assert kwork[0]["task_id"] == "k2" or kwork[0]["task_id"] == "k1"

    def test_priority_score_prefers_good_opportunity(
        self, service: MarketService
    ) -> None:
        # свежая задача с высокой конкуренцией vs старая с почти нулевой
        now = datetime.now()
        service.tasks.append(
            {
                "task_id": "f2",
                "source": "fl",
                "title": "Свежий сайт",
                "normalized_category": "Frontend",
                "budget_min": 50000,
                "budget_max": 60000,
                "proposals_count": 40,
                "posted_at": now - timedelta(hours=1),
                "technologies": [],
            }
        )
        result = service.filter_tasks(sort="priority")
        fl = [t for t in result if t["source"] == "fl"]
        # f1: 5 откликов + бюджет → выше свежего f2 с 40 откликами
        assert fl[0]["task_id"] == "f1"

    def test_kwork_always_beats_fl(self, service: MarketService) -> None:
        # даже старый kwork-заказ остаётся выше любого fl
        now = datetime.now()
        service.tasks.append(
            {
                "task_id": "k3",
                "source": "kwork",
                "title": "Старый kwork",
                "normalized_category": "Backend",
                "budget_min": None,
                "budget_max": None,
                "proposals_count": 50,
                "posted_at": now - timedelta(days=30),
                "technologies": [],
            }
        )
        result = service.filter_tasks(sort="priority")
        kwork_pos = next(i for i, t in enumerate(result) if t["task_id"] == "k3")
        fl_pos = next(i for i, t in enumerate(result) if t["source"] == "fl")
        assert kwork_pos < fl_pos


class TestFilters:
    def test_source_filter(self, service: MarketService) -> None:
        result = service.filter_tasks(sources=["fl"])
        assert len(result) == 1
        assert result[0]["source"] == "fl"

    def test_category_filter(self, service: MarketService) -> None:
        result = service.filter_tasks(categories=["Frontend"])
        assert {t["title"] for t in result} == {"Верстка лендинга", "React приложение"}

    def test_it_only_excludes_non_it(self, service: MarketService) -> None:
        result = service.filter_tasks(scope="it")
        assert all(
            t["normalized_category"] in {"Backend", "Frontend", "Data Analytics"}
            for t in result
        )

    def test_scope_it_excludes_design(self, service: MarketService) -> None:
        service.tasks.append(
            {
                "task_id": "d1",
                "source": "kwork",
                "title": "Логотип",
                "normalized_category": "Design",
                "budget_min": 5000,
                "budget_max": 10000,
                "proposals_count": 3,
                "posted_at": datetime.now(),
                "technologies": [],
            }
        )
        result = service.filter_tasks(scope="it")
        assert all(t["task_id"] != "d1" for t in result)

    def test_scope_design_only(self, service: MarketService) -> None:
        service.tasks.append(
            {
                "task_id": "d1",
                "source": "kwork",
                "title": "Логотип",
                "normalized_category": "Design",
                "budget_min": 5000,
                "budget_max": 10000,
                "proposals_count": 3,
                "posted_at": datetime.now(),
                "technologies": [],
            }
        )
        result = service.filter_tasks(scope="design")
        assert len(result) == 1
        assert result[0]["task_id"] == "d1"

    def test_scope_it_design_union(self, service: MarketService) -> None:
        service.tasks.append(
            {
                "task_id": "d1",
                "source": "kwork",
                "title": "Логотип",
                "normalized_category": "Design",
                "budget_min": 5000,
                "budget_max": 10000,
                "proposals_count": 3,
                "posted_at": datetime.now(),
                "technologies": [],
            }
        )
        result = service.filter_tasks(scope="it_design")
        assert any(t["task_id"] == "d1" for t in result)
        assert any(t["task_id"] == "k1" for t in result)

    def test_scope_all_includes_everything(self, service: MarketService) -> None:
        result = service.filter_tasks(scope="all")
        assert len(result) == 4

    def test_search_title(self, service: MarketService) -> None:
        result = service.filter_tasks(query="Django")
        assert len(result) == 1
        assert result[0]["task_id"] == "k1"

    def test_search_description(self, service: MarketService) -> None:
        svc = service
        svc.tasks[0]["description"] = "специальное слово-магнит"
        result = svc.filter_tasks(query="магнит", search_desc=False)
        assert result == []
        result = svc.filter_tasks(query="магнит", search_desc=True)
        assert len(result) == 1

    def test_budget_range(self, service: MarketService) -> None:
        result = service.filter_tasks(budget_min=50000)
        assert all(t["task_id"] in {"k1", "f1"} for t in result)

    def test_has_budget(self, service: MarketService) -> None:
        result = service.filter_tasks(has_budget=True)
        assert all(
            t["budget_min"] is not None or t["budget_max"] is not None for t in result
        )
        assert all(t["task_id"] != "x1" for t in result)

    def test_freshness(self, service: MarketService) -> None:
        result = service.filter_tasks(freshness_hours=24)
        assert all(t["task_id"] != "k2" for t in result)

    def test_proposals_range(self, service: MarketService) -> None:
        result = service.filter_tasks(max_proposals=10)
        assert all(t["task_id"] != "k1" for t in result)
        assert all(t["task_id"] != "k2" for t in result)


class TestSorting:
    def test_sort_by_date(self, service: MarketService) -> None:
        result = service.filter_tasks(sort="date")
        assert result[0]["task_id"] == "x1"

    def test_sort_by_budget_desc(self, service: MarketService) -> None:
        result = service.filter_tasks(sort="budget_desc", has_budget=True)
        assert result[0]["task_id"] == "f1"

    def test_sort_by_proposals_asc(self, service: MarketService) -> None:
        result = service.filter_tasks(sort="proposals_asc")
        # x1 has no proposals → treated as highest, so f1 (5) first
        assert result[0]["task_id"] == "f1"


class TestServiceState:
    def test_filters_meta(self, service: MarketService) -> None:
        meta = service.filters_meta()
        assert "kwork" in [s["key"] for s in meta["all_sources"]]
        assert meta["budget_min"] == 10000
        assert meta["budget_max"] == 80000


class TestCollectionMerge:
    def test_merge_keeps_existing_tasks(self, service: MarketService) -> None:
        fresh = [
            {
                "task_id": "k1",
                "source": "kwork",
                "title": "Django сайт (обновлён)",
                "normalized_category": "Backend",
            },
            {
                "task_id": "k9",
                "source": "kwork",
                "title": "Новый бот",
                "normalized_category": "Backend",
            },
        ]
        merged = service._merge_tasks(service.tasks, fresh)
        ids = {(t["source"], t["task_id"]) for t in merged}
        assert ("kwork", "k1") in ids  # обновлён, не дублирован
        assert ("kwork", "k9") in ids  # добавлен новый
        assert ("fl", "f1") in ids  # старые сохранены
        assert len(merged) == len(service.tasks) + 1
        updated = next(t for t in merged if t["task_id"] == "k1")
        assert updated["title"] == "Django сайт (обновлён)"

    def test_overlap_count(self, service: MarketService) -> None:
        fresh = [
            {"source": "kwork", "task_id": "k1"},
            {"source": "kwork", "task_id": "brand_new"},
        ]
        assert service._overlap_count(fresh) == 1
