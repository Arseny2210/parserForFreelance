from typing import Optional
from collections import defaultdict
import pandas as pd
from loguru import logger


class CompetitionAnalyzer:
    def analyze(self, tasks: list[dict]) -> dict:
        category_proposals: dict[str, list[int]] = defaultdict(list)

        for task in tasks:
            proposals = task.get("proposals_count")
            category = task.get("normalized_category", "OTHER")
            if proposals is not None:
                category_proposals[category].append(proposals)

        result: dict = {
            "most_competitive_categories": {},
            "least_competitive_categories": {},
            "average_proposals_per_category": {},
            "overall_average_proposals": None,
            "overall_median_proposals": None,
        }

        avg_proposals_list = []
        all_proposals = []

        for category, proposals_list in category_proposals.items():
            avg_bids = sum(proposals_list) / len(proposals_list)
            result["average_proposals_per_category"][category] = round(avg_bids, 2)
            avg_proposals_list.append((category, avg_bids))
            all_proposals.extend(proposals_list)

        avg_proposals_list.sort(key=lambda x: x[1], reverse=True)

        result["most_competitive_categories"] = dict(avg_proposals_list[:10])
        result["least_competitive_categories"] = dict(
            sorted(avg_proposals_list, key=lambda x: x[1])[:10]
        )

        if all_proposals:
            result["overall_average_proposals"] = round(
                sum(all_proposals) / len(all_proposals), 2
            )
            sorted_proposals = sorted(all_proposals)
            n = len(sorted_proposals)
            if n % 2 == 0:
                result["overall_median_proposals"] = (
                    sorted_proposals[n // 2 - 1] + sorted_proposals[n // 2]
                ) / 2
            else:
                result["overall_median_proposals"] = sorted_proposals[n // 2]

        logger.info("Competition analysis complete")
        return result

    def find_undervalued_categories(self, tasks: list[dict]) -> pd.DataFrame:
        category_stats: dict[str, dict] = defaultdict(
            lambda: {
                "total_budget": 0,
                "total_proposals": 0,
                "count": 0,
                "budgets": [],
                "proposals": [],
            }
        )

        for task in tasks:
            category = task.get("normalized_category", "OTHER")
            budget = task.get("budget_min") or task.get("budget_max")
            proposals = task.get("proposals_count")

            if budget and proposals is not None:
                category_stats[category]["total_budget"] += budget
                category_stats[category]["total_proposals"] += proposals
                category_stats[category]["count"] += 1
                category_stats[category]["budgets"].append(budget)
                category_stats[category]["proposals"].append(proposals)

        records = []
        for category, stats in category_stats.items():
            if stats["count"] < 3:
                continue
            avg_budget = stats["total_budget"] / stats["count"]
            avg_proposals = stats["total_proposals"] / stats["count"]
            value_ratio = avg_budget / (avg_proposals + 1)

            records.append(
                {
                    "category": category,
                    "avg_budget": avg_budget,
                    "avg_proposals": avg_proposals,
                    "value_ratio": value_ratio,
                    "task_count": stats["count"],
                }
            )

        if not records:
            return pd.DataFrame()

        df = pd.DataFrame(records)
        df = df.sort_values("value_ratio", ascending=False)
        df["undervalued_score"] = (df["value_ratio"] - df["value_ratio"].min()) / (
            df["value_ratio"].max() - df["value_ratio"].min() + 0.001
        )

        logger.info("Undervalued categories analysis complete")
        return df

    def category_competition_summary(self, tasks: list[dict]) -> pd.DataFrame:
        records = []
        for task in tasks:
            proposals = task.get("proposals_count")
            if proposals is not None:
                records.append(
                    {
                        "category": task.get("normalized_category", "OTHER"),
                        "proposals": proposals,
                        "title": task.get("title"),
                        "source": task.get("source"),
                    }
                )

        if not records:
            return pd.DataFrame()

        df = pd.DataFrame(records)
        summary = (
            df.groupby("category")
            .agg(
                avg_proposals=("proposals", "mean"),
                median_proposals=("proposals", "median"),
                max_proposals=("proposals", "max"),
                min_proposals=("proposals", "min"),
                task_count=("proposals", "count"),
            )
            .reset_index()
        )

        summary = summary.sort_values("avg_proposals", ascending=False)
        summary.columns = [
            "Category",
            "Avg Proposals",
            "Median Proposals",
            "Max Proposals",
            "Min Proposals",
            "Task Count",
        ]
        return summary
