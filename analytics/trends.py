from typing import Optional
from collections import defaultdict, Counter
from datetime import datetime, timedelta, timezone
import pandas as pd
from loguru import logger
from analytics.categories import CATEGORY_KEYWORDS


class TrendAnalyzer:
    def analyze_growth(self, tasks: list[dict]) -> pd.DataFrame:
        if not tasks:
            return pd.DataFrame()

        category_counts: dict[str, int] = Counter()
        recent_category_counts: dict[str, int] = Counter()

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        recent_cutoff = now - timedelta(days=7)

        for task in tasks:
            category = task.get("normalized_category", "OTHER")
            category_counts[category] += 1

            posted_at = task.get("posted_at")
            if posted_at and isinstance(posted_at, datetime):
                if posted_at >= recent_cutoff:
                    recent_category_counts[category] += 1

        total = sum(category_counts.values()) or 1
        recent_total = sum(recent_category_counts.values()) or 1

        records = []
        all_categories = set(category_counts.keys()) | set(
            recent_category_counts.keys()
        )

        for category in all_categories:
            freq = category_counts.get(category, 0)
            recent_freq = recent_category_counts.get(category, 0)
            share = freq / total * 100
            recent_share = recent_freq / recent_total * 100 if recent_total > 0 else 0

            if freq > 0:
                growth_rate = ((recent_freq / freq) - 1) if freq > 0 else 0
            else:
                growth_rate = 0

            records.append(
                {
                    "category": category,
                    "total_count": freq,
                    "recent_count": recent_freq,
                    "share_percent": round(share, 2),
                    "recent_share_percent": round(recent_share, 2),
                    "growth_rate": round(growth_rate, 4),
                }
            )

        df = pd.DataFrame(records)

        if not df.empty:
            df["growth_percent"] = df["growth_rate"] * 100
            df = df.sort_values("growth_rate", ascending=False)

        logger.info("Trend analysis complete: {} categories analyzed", len(df))
        return df

    def fastest_growing_categories(
        self, tasks: list[dict], top_n: int = 10
    ) -> list[dict]:
        df = self.analyze_growth(tasks)
        if df.empty:
            return []

        top_growing = df.head(top_n)
        result = []
        for _, row in top_growing.iterrows():
            result.append(
                {
                    "category": row["category"],
                    "total_count": int(row["total_count"]),
                    "growth_rate": float(row["growth_rate"]),
                    "growth_percent": float(row["growth_percent"]),
                }
            )

        logger.info("Top {} fastest growing categories identified", len(result))
        return result

    def highest_paying_categories(
        self, tasks: list[dict], top_n: int = 10
    ) -> list[dict]:
        category_budgets: dict[str, list[float]] = defaultdict(list)

        for task in tasks:
            category = task.get("normalized_category", "OTHER")
            budget = task.get("budget_min") or task.get("budget_max")
            if budget is not None and budget > 0:
                category_budgets[category].append(budget)

        avg_budgets = []
        for category, budgets in category_budgets.items():
            if len(budgets) >= 2:
                avg_budgets.append(
                    {
                        "category": category,
                        "avg_budget": sum(budgets) / len(budgets),
                        "median_budget": sorted(budgets)[len(budgets) // 2],
                        "max_budget": max(budgets),
                        "min_budget": min(budgets),
                        "task_count": len(budgets),
                    }
                )

        avg_budgets.sort(key=lambda x: x["avg_budget"], reverse=True)
        result = avg_budgets[:top_n]

        logger.info("Top {} highest paying categories identified", len(result))
        return result

    def publication_trend(self, tasks: list[dict]) -> pd.DataFrame:
        records = []
        for task in tasks:
            posted_at = task.get("posted_at")
            if posted_at and isinstance(posted_at, datetime):
                records.append(
                    {
                        "date": posted_at.date(),
                        "source": task.get("source"),
                        "category": task.get("normalized_category", "OTHER"),
                    }
                )

        if not records:
            return pd.DataFrame()

        df = pd.DataFrame(records)
        daily_counts = df.groupby(["date", "source"]).size().reset_index(name="count")
        daily_counts = daily_counts.sort_values("date")

        return daily_counts

    def category_distribution_trend(
        self, tasks: list[dict], days: int = 30
    ) -> pd.DataFrame:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        cutoff = now - timedelta(days=days)

        records = []
        for task in tasks:
            posted_at = task.get("posted_at")
            if posted_at and isinstance(posted_at, datetime) and posted_at >= cutoff:
                records.append(
                    {
                        "date": posted_at.date(),
                        "category": task.get("normalized_category", "OTHER"),
                    }
                )

        if not records:
            return pd.DataFrame()

        df = pd.DataFrame(records)
        pivot = df.groupby(["date", "category"]).size().unstack(fill_value=0)
        return pivot
