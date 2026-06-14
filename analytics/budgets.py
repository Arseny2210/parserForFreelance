from typing import Optional
import statistics
from collections import defaultdict
from datetime import datetime, timedelta
import pandas as pd
from loguru import logger


class BudgetAnalyzer:
    def analyze(self, tasks: list[dict]) -> dict:
        budgets_min = []
        budgets_max = []
        category_budgets: dict[str, list[float]] = defaultdict(list)

        for task in tasks:
            budget_min = task.get("budget_min")
            budget_max = task.get("budget_max")
            category = task.get("normalized_category", "OTHER")

            if budget_min is not None and budget_min > 0:
                budgets_min.append(budget_min)
                category_budgets[category].append(budget_min)

            if budget_max is not None and budget_max > 0:
                budgets_max.append(budget_max)

        result: dict = {
            "average_budget_min": self._safe_mean(budgets_min),
            "average_budget_max": self._safe_mean(budgets_max),
            "median_budget_min": self._safe_median(budgets_min),
            "median_budget_max": self._safe_median(budgets_max),
            "min_budget": min(budgets_min) if budgets_min else None,
            "max_budget": max(budgets_max) if budgets_max else None,
            "std_dev_budget_min": self._safe_stdev(budgets_min),
            "std_dev_budget_max": self._safe_stdev(budgets_max),
            "budget_range_25_75_min": self._safe_percentile(budgets_min, 25),
            "budget_range_25_75_max": self._safe_percentile(budgets_max, 75),
            "total_tasks_with_budget": len(budgets_min),
            "total_tasks_without_budget": len(tasks) - len(budgets_min),
            "category_average_budgets": {
                cat: self._safe_mean(buds)
                for cat, buds in category_budgets.items()
                if len(buds) >= 3
            },
            "category_median_budgets": {
                cat: self._safe_median(buds)
                for cat, buds in category_budgets.items()
                if len(buds) >= 3
            },
        }

        logger.info(
            "Budget analysis complete: avg=₽{:.2f}, median=₽{:.2f}",
            result["average_budget_min"] or 0,
            result["median_budget_min"] or 0,
        )
        return result

    def analyze_category_budgets(self, tasks: list[dict]) -> pd.DataFrame:
        records = []
        for task in tasks:
            budget_min = task.get("budget_min")
            budget_max = task.get("budget_max")
            if budget_min is not None or budget_max is not None:
                records.append(
                    {
                        "category": task.get("normalized_category", "OTHER"),
                        "budget_min": budget_min,
                        "budget_max": budget_max,
                        "source": task.get("source"),
                        "currency": task.get("currency", "USD"),
                    }
                )

        if not records:
            return pd.DataFrame()

        df = pd.DataFrame(records)
        summary = (
            df.groupby("category")
            .agg(
                avg_budget_min=("budget_min", "mean"),
                avg_budget_max=("budget_max", "mean"),
                median_budget_min=("budget_min", "median"),
                median_budget_max=("budget_max", "median"),
                count=("budget_min", "count"),
                std_budget_min=("budget_min", "std"),
            )
            .reset_index()
        )

        summary = summary.sort_values("avg_budget_min", ascending=False)
        summary.columns = [
            "Category",
            "Avg Budget Min",
            "Avg Budget Max",
            "Median Budget Min",
            "Median Budget Max",
            "Task Count",
            "Std Dev Budget Min",
        ]
        return summary

    def budget_distribution(self, tasks: list[dict], bins: int = 10) -> dict:
        budgets = []
        for task in tasks:
            b = task.get("budget_min") or task.get("budget_max")
            if b is not None and b > 0:
                budgets.append(b)

        if not budgets:
            return {"bins": [], "counts": [], "labels": []}

        min_b = min(budgets)
        max_b = max(budgets)
        bin_size = (max_b - min_b) / bins if max_b > min_b else 1

        distribution: dict = {"bins": [], "counts": [], "labels": []}
        for i in range(bins):
            low = min_b + i * bin_size
            high = low + bin_size
            if i == bins - 1:
                count = sum(1 for b in budgets if low <= b <= high)
            else:
                count = sum(1 for b in budgets if low <= b < high)
            distribution["bins"].append((low, high))
            distribution["counts"].append(count)
            distribution["labels"].append(f"${low:.0f}-${high:.0f}")

        return distribution

    def _safe_mean(self, values: list[float]) -> Optional[float]:
        return statistics.mean(values) if values else None

    def _safe_median(self, values: list[float]) -> Optional[float]:
        return statistics.median(values) if values else None

    def _safe_stdev(self, values: list[float]) -> Optional[float]:
        return statistics.stdev(values) if len(values) > 1 else None

    def _safe_percentile(self, values: list[float], percentile: int) -> Optional[float]:
        if not values:
            return None
        sorted_vals = sorted(values)
        k = (len(sorted_vals) - 1) * percentile / 100
        f = int(k)
        c = f + 1
        if c >= len(sorted_vals):
            return sorted_vals[-1]
        return sorted_vals[f] + (k - f) * (sorted_vals[c] - sorted_vals[f])
