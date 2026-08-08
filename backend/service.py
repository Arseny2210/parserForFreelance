"""
MarketService — singleton orchestrating scraping, analytics and persistence
for the FastAPI backend. Reuses the existing FreelanceMarketAnalyzer pipeline.
"""

import asyncio
import json
from pathlib import Path
from datetime import datetime
from typing import Any, Optional

from loguru import logger

from main import FreelanceMarketAnalyzer, SCRAPER_MAP
from export.excel_export import RUSSIAN_CATEGORIES, IT_CATEGORIES

CACHE_FILE = Path("exports/cache.json")

SOURCE_PRIORITY: dict[str, int] = {"kwork": 0, "fl": 1}
SOURCE_LABELS: dict[str, str] = {"kwork": "Kwork", "fl": "FL.ru"}

IT_CATEGORY_GROUPS: dict[str, list[str]] = {
    "Frontend / UI": ["Frontend", "React", "Next.js"],
    "Backend": ["Backend", "FastAPI", "Django", "Laravel", "C# / .NET"],
    "CMS": ["WordPress", "Tilda", "Shopify"],
    "Боты": ["Telegram Bots", "Discord Bots"],
    "AI / ML": [
        "AI Chatbots",
        "AI Agents",
        "RAG",
        "OpenAI Integration",
        "Claude Integration",
        "Machine Learning",
        "Computer Vision",
    ],
    "Парсинг / Автоматизация": [
        "Web Scraping",
        "Parsing",
        "Automation",
        "n8n",
        "Make",
        "Zapier",
    ],
    "Mobile": ["Mobile Apps", "Flutter", "React Native", "Android", "iOS"],
    "DevOps / QA": ["DevOps", "Docker", "Kubernetes", "QA"],
    "Data": ["Data Analytics", "Power BI", "SQL"],
    "Design / Marketing": ["Design", "Marketing"],
    "Fullstack": ["Fullstack"],
}

# Отдельные области для фильтра «Сфера»
IT_CORE: set[str] = set(IT_CATEGORIES) - {"Design", "Marketing"}
DESIGN_CATEGORIES: set[str] = {"Design"}


def _parse_dt(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
    return None


def _fetch_kwork_full_description(url: str) -> Optional[str]:
    """Загружает полный текст заказа Kwork со страницы заказа.

    В листинге Kwork отдаёт только обрезанное описание («… Показать полностью»).
    Полный текст лежит в JSON `window.stateData` на странице конкретного заказа
    (поле `wantData.description`).
    """
    if not url or "kwork.ru" not in url:
        return None
    try:
        import re
        import json
        import httpx

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
        }
        with httpx.Client(headers=headers, timeout=25, follow_redirects=True) as client:
            resp = client.get(url)
            resp.raise_for_status()
            html = resp.text

        match = re.search(
            r"window\.stateData=(\{.*?\});window\.firebaseConfig", html, re.S
        )
        if not match:
            return None
        data = json.loads(match.group(1))
        desc = (data.get("wantData") or {}).get("description")
        if not desc:
            return None
        text = desc.replace("\r\n", "\n").strip()
        return text or None
    except Exception:
        logger.exception("Failed to fetch full Kwork description for {}", url)
        return None


def _sort_key(task: dict) -> tuple:
    src = task.get("source", "")
    priority = SOURCE_PRIORITY.get(src, 2)
    posted = _parse_dt(task.get("posted_at"))
    ts = -posted.timestamp() if posted else 0.0
    return (priority, ts)


def _task_budget(task: dict) -> Optional[float]:
    b = task.get("budget_min") or task.get("budget_max")
    return b if b is not None and b > 0 else None


# ── Умный приоритет ────────────────────────────────────────────
# Площадка доминирует (Kwork > FL.ru > прочие), чтобы Kwork всегда был сверху.
# Внутри площадки score учитывает свежесть, бюджет и конкуренцию.
SOURCE_SCORE: dict[str, int] = {"kwork": 100000, "fl": 10000}

FRESHNESS_BONUS: list[tuple[int, int]] = [
    (24, 200),  # до 24 часов
    (72, 150),  # до 3 дней
    (168, 80),  # до 7 дней
]

COMPETITION_BONUS: list[tuple[int, int]] = [
    (5, 100),  # почти нет откликов
    (15, 60),  # мало откликов
    (30, 30),  # умеренно
]


def _priority_score(task: dict) -> int:
    src = task.get("source", "")
    score = SOURCE_SCORE.get(src, 1000)

    posted = _parse_dt(task.get("posted_at"))
    if posted:
        hours = (datetime.now() - posted).total_seconds() / 3600
        for limit, bonus in FRESHNESS_BONUS:
            if hours <= limit:
                score += bonus
                break

    if _task_budget(task):
        score += 50

    proposals = task.get("proposals_count")
    if proposals is not None:
        for limit, bonus in COMPETITION_BONUS:
            if proposals <= limit:
                score += bonus
                break

    return score


class MarketService:
    def __init__(self) -> None:
        self.tasks: list[dict] = []
        self.stats: dict = {}
        self.active_sources: list[str] = []
        self.last_run: Optional[datetime] = None
        self.collected_total: int = 0
        self._running = False
        self._status: dict = {"running": False, "progress": 0.0, "message": ""}
        self._collect_task: Optional[asyncio.Task] = None
        self._load_cache()

    # ── persistence ──────────────────────────────────────────────
    def _load_cache(self) -> None:
        if not CACHE_FILE.exists():
            return
        try:
            data = json.loads(CACHE_FILE.read_text())
            self.tasks = data.get("tasks", [])
            self.stats = data.get("stats", {})
            self.active_sources = data.get("sources", [])
            collected_at = data.get("collected_at")
            if collected_at:
                self.last_run = datetime.fromisoformat(collected_at)
            logger.info("Loaded {} tasks from cache", len(self.tasks))
        except Exception as e:
            logger.warning("Failed to load cache: {}", e)

    def _save_cache(self) -> None:
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "collected_at": self.last_run.isoformat() if self.last_run else None,
            "tasks": self.tasks,
            "stats": self.stats,
            "sources": self.active_sources,
        }
        CACHE_FILE.write_text(json.dumps(data, default=str, ensure_ascii=False))

    # ── collection ──────────────────────────────────────────────
    @property
    def running(self) -> bool:
        return self._running

    def status(self) -> dict:
        return {
            "running": self._running,
            "progress": self._status.get("progress", 0.0),
            "message": self._status.get("message", ""),
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "task_count": len(self.tasks),
            "collected_total": self.collected_total,
            "active_sources": [
                {"key": s, "label": SOURCE_LABELS.get(s, s)}
                for s in self.active_sources
            ],
        }

    def start_collect(self, sources: list[str]) -> dict:
        if self._running:
            return {"started": False, "reason": "already_running"}

        valid = [s for s in sources if s in SCRAPER_MAP]
        if not valid:
            return {"started": False, "reason": "no_valid_sources"}

        self._collect_task = asyncio.create_task(self._collect_impl(valid))
        return {"started": True, "sources": valid}

    async def _collect_impl(self, sources: list[str]) -> None:
        self._running = True
        self.collected_total = 0
        self._status = {"progress": 0.0, "message": "Запуск сбора данных..."}
        logger.info("Collection started for {}", sources)
        try:
            analyzer = FreelanceMarketAnalyzer(scrapers_to_run=sources)
            collected_all = []
            errors: list[str] = []

            for i, src in enumerate(sources):
                self._status = {
                    "progress": round(i / len(sources) * 0.55, 3),
                    "message": f"Сбор: {SOURCE_LABELS.get(src, src)}...",
                }
                try:
                    tasks = await analyzer.collect_source(src)
                    collected_all.extend(tasks)
                    logger.info("Collected {} from {}", len(tasks), src)
                except Exception as e:
                    logger.exception("Collect failed for {}: {}", src, e)
                    errors.append(SOURCE_LABELS.get(src, src))

            self.collected_total = len(collected_all)
            if not collected_all:
                self._status = {"progress": 1.0, "message": "Задач не найдено"}
                self._running = False
                return

            # Объединяем свежесобранные задачи с существующими из кеша,
            # чтобы частичный сбор не «съедал» ранее накопленную базу.
            merged = self._merge_tasks(self.tasks, collected_all)

            self._status = {"progress": 0.6, "message": "Классификация категорий..."}
            analyzer.tasks = merged
            await asyncio.to_thread(analyzer.normalize_categories)

            self._status = {"progress": 0.7, "message": "Извлечение технологий..."}
            await asyncio.to_thread(analyzer.extract_technologies)

            self._status = {"progress": 0.85, "message": "Анализ данных..."}
            await asyncio.to_thread(analyzer.run_analytics)

            self.tasks = analyzer.tasks
            self.stats = analyzer.analytics
            self.active_sources = sorted(
                set(self.active_sources) | set(analyzer.active_sources)
            )
            self.last_run = datetime.now()
            self._save_cache()

            new_count = len(collected_all) - self._overlap_count(collected_all)
            msg = f"Готово: собрано {new_count} новых, всего в базе {len(self.tasks)}"
            if errors:
                msg += f" (ошибки: {', '.join(errors)})"
            self._status = {"progress": 1.0, "message": msg}
            logger.info("Collection finished: {} tasks", len(self.tasks))
        except Exception as e:
            logger.exception("Collection failed: {}", e)
            self._status = {"progress": 0.0, "message": f"Ошибка: {e}"}
        finally:
            self._running = False

    @staticmethod
    def _merge_tasks(existing: list[dict], fresh: list[dict]) -> list[dict]:
        by_key: dict[tuple[str, str], dict] = {}
        for t in existing:
            by_key[(t.get("source", ""), str(t.get("task_id", "")))] = t
        for t in fresh:
            by_key[(t.get("source", ""), str(t.get("task_id", "")))] = t
        return list(by_key.values())

    def _overlap_count(self, fresh: list[dict]) -> int:
        existing_keys = {
            (t.get("source", ""), str(t.get("task_id", ""))) for t in self.tasks
        }
        return sum(
            1
            for t in fresh
            if (t.get("source", ""), str(t.get("task_id", ""))) in existing_keys
        )

    # ── full descriptions (on-demand) ────────────────────────────
    def get_full_description(self, source: str, task_id: str) -> Optional[str]:
        task = next(
            (
                t
                for t in self.tasks
                if t.get("source") == source
                and str(t.get("task_id", "")) == str(task_id)
            ),
            None,
        )
        if not task:
            return None
        if task.get("full_description"):
            return task["full_description"]

        full = _fetch_kwork_full_description(task.get("url") or "")
        if full:
            task["full_description"] = full
            self._save_cache()
            return full
        return None

    # ── querying ────────────────────────────────────────────────
    def filter_tasks(
        self,
        query: Optional[str] = None,
        sources: Optional[list[str]] = None,
        categories: Optional[list[str]] = None,
        budget_min: Optional[float] = None,
        budget_max: Optional[float] = None,
        scope: str = "all",
        freshness_hours: Optional[int] = None,
        has_budget: bool = False,
        min_proposals: Optional[int] = None,
        max_proposals: Optional[int] = None,
        search_desc: bool = False,
        sort: str = "priority",
    ) -> list[dict]:
        q = (query or "").strip().lower()
        cutoff = None
        if freshness_hours:
            cutoff = datetime.now().timestamp() - freshness_hours * 3600

        result: list[dict] = []
        for task in self.tasks:
            cat = task.get("normalized_category", "OTHER")
            src = task.get("source", "")

            if not self._scope_allows(scope, cat):
                continue
            if categories and cat not in categories:
                continue
            if sources and src not in sources:
                continue

            if q:
                haystack = task.get("title") or ""
                if search_desc:
                    haystack += " " + (task.get("description") or "")
                if q not in haystack.lower():
                    continue

            bmin = task.get("budget_min")
            bmax = task.get("budget_max")
            if has_budget and bmin is None and bmax is None:
                continue
            if budget_min is not None or budget_max is not None:
                if bmin is None and bmax is None:
                    continue
                t_lo = bmin if bmin is not None else bmax
                t_hi = bmax if bmax is not None else bmin
                if budget_min is not None and t_hi < budget_min:
                    continue
                if budget_max is not None and t_lo > budget_max:
                    continue

            if cutoff is not None:
                posted = _parse_dt(task.get("posted_at"))
                if posted is None or posted.timestamp() < cutoff:
                    continue

            proposals = task.get("proposals_count")
            if min_proposals is not None and (
                proposals is None or proposals < min_proposals
            ):
                continue
            if max_proposals is not None and (
                proposals is None or proposals > max_proposals
            ):
                continue

            result.append(task)

        self._sort(result, sort)
        return result

    @staticmethod
    def _scope_allows(scope: str, category: str) -> bool:
        if scope == "it":
            return category in IT_CORE
        if scope == "design":
            return category in DESIGN_CATEGORIES
        if scope == "it_design":
            return category in IT_CORE or category in DESIGN_CATEGORIES
        return True  # "all"

    @staticmethod
    def _sort(tasks: list[dict], sort: str) -> None:
        if sort == "date":
            tasks.sort(
                key=lambda t: _parse_dt(t.get("posted_at")).timestamp() or 0,
                reverse=True,
            )
        elif sort == "budget_desc":
            tasks.sort(key=lambda t: _task_budget(t) or 0, reverse=True)
        elif sort == "budget_asc":
            tasks.sort(key=lambda t: _task_budget(t) or 0)
        elif sort == "proposals_asc":
            tasks.sort(
                key=lambda t: (
                    t.get("proposals_count")
                    if t.get("proposals_count") is not None
                    else 10**9
                )
            )
        else:  # priority — умный приоритет
            tasks.sort(
                key=lambda t: (
                    _priority_score(t),
                    _parse_dt(t.get("posted_at")).timestamp() or 0,
                ),
                reverse=True,
            )

    def filters_meta(self) -> dict:
        present_sources = sorted(
            {t.get("source", "") for t in self.tasks if t.get("source")},
            key=lambda s: SOURCE_PRIORITY.get(s, 2),
        )
        present_categories = sorted(
            {
                t.get("normalized_category", "OTHER")
                for t in self.tasks
                if t.get("normalized_category") in IT_CATEGORIES
            }
        )
        budgets = [
            t.get("budget_min") or t.get("budget_max")
            for t in self.tasks
            if (t.get("budget_min") or t.get("budget_max"))
        ]
        return {
            "sources": [
                {"key": s, "label": SOURCE_LABELS.get(s, s)} for s in present_sources
            ],
            "all_sources": [
                {"key": k, "label": v}
                for k, v in SOURCE_LABELS.items()
                if k in SCRAPER_MAP
            ],
            "category_groups": [
                {
                    "name": group,
                    "categories": [
                        {
                            "key": c,
                            "label": RUSSIAN_CATEGORIES.get(c, c),
                            "present": c in present_categories,
                        }
                        for c in members
                    ],
                }
                for group, members in IT_CATEGORY_GROUPS.items()
            ],
            "budget_min": min(budgets) if budgets else 0,
            "budget_max": max(budgets) if budgets else 500_000,
        }

    def analytics(self) -> dict:
        return self.stats


service = MarketService()
