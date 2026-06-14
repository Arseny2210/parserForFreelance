from typing import Optional
from pathlib import Path
from collections import Counter
from datetime import datetime
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from loguru import logger
from core.settings import settings

plt.style.use("seaborn-v0_8-darkgrid")
plt.rcParams["figure.figsize"] = (14, 8)
plt.rcParams["figure.dpi"] = 150
plt.rcParams["font.size"] = 12
plt.rcParams["axes.titlesize"] = 16
plt.rcParams["axes.labelsize"] = 13
plt.rcParams["font.family"] = "DejaVu Sans"


class ChartGenerator:
    def __init__(self) -> None:
        self.charts_dir = Path(settings.charts_dir)
        self.charts_dir.mkdir(parents=True, exist_ok=True)
        self.generated_charts: list[str] = []

    def generate_all(self, tasks: list[dict], analytics: dict) -> list[str]:
        self.generated_charts = []

        self.plot_category_distribution(tasks)
        self.plot_budgets_by_category(tasks)
        self.plot_tasks_by_source(tasks)
        self.plot_publication_timeline(tasks)
        self.plot_technology_distribution(tasks)
        self.plot_budget_histogram(tasks)
        self.plot_competition_heatmap(tasks)
        self.plot_category_vs_budget(tasks)

        logger.info(
            "Generated {} charts in {}", len(self.generated_charts), self.charts_dir
        )
        return self.generated_charts

    def plot_category_distribution(self, tasks: list[dict]) -> str:
        counter = Counter()
        for task in tasks:
            counter[task.get("normalized_category", "OTHER")] += 1

        if not counter:
            return ""

        sorted_items = counter.most_common(15)
        categories, counts = zip(*sorted_items)

        fig, ax = plt.subplots()
        colors = plt.cm.viridis([i / len(categories) for i in range(len(categories))])
        bars = ax.barh(range(len(categories)), counts, color=colors)
        ax.set_yticks(range(len(categories)))
        ax.set_yticklabels(categories)
        ax.set_xlabel("Number of Tasks")
        ax.set_title("Top 15 Categories by Task Count")
        ax.invert_yaxis()

        for bar, count in zip(bars, counts):
            ax.text(
                bar.get_width() + 0.3,
                bar.get_y() + bar.get_height() / 2,
                str(count),
                va="center",
            )

        plt.tight_layout()
        filepath = self.charts_dir / "category_distribution.png"
        plt.savefig(filepath, bbox_inches="tight")
        plt.close()
        self.generated_charts.append(str(filepath))
        return str(filepath)

    def plot_budgets_by_category(self, tasks: list[dict]) -> str:
        records = []
        for task in tasks:
            budget = task.get("budget_min") or task.get("budget_max")
            if budget and budget > 0:
                records.append(
                    {
                        "category": task.get("normalized_category", "OTHER"),
                        "budget": budget,
                    }
                )

        if not records:
            return ""

        df = pd.DataFrame(records)
        cat_order = (
            df.groupby("category")["budget"]
            .mean()
            .sort_values(ascending=False)
            .head(15)
            .index
        )

        fig, ax = plt.subplots(figsize=(16, 8))
        data_to_plot = [df[df["category"] == cat]["budget"].values for cat in cat_order]

        bp = ax.boxplot(data_to_plot, patch_artist=True, showmeans=True)
        for patch, color in zip(
            bp["boxes"],
            plt.cm.plasma([i / len(cat_order) for i in range(len(cat_order))]),
        ):
            patch.set_facecolor(color)

        ax.set_xticklabels(cat_order, rotation=45, ha="right")
        ax.set_ylabel("Budget (₽)")
        ax.set_title("Budget Distribution by Category")
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        filepath = self.charts_dir / "budgets_by_category.png"
        plt.savefig(filepath, bbox_inches="tight")
        plt.close()
        self.generated_charts.append(str(filepath))
        return str(filepath)

    def plot_tasks_by_source(self, tasks: list[dict]) -> str:
        counter = Counter()
        for task in tasks:
            counter[task.get("source", "unknown")] += 1

        if not counter:
            return ""

        sources, counts = zip(*counter.most_common())
        colors = plt.cm.Set3([i / len(sources) for i in range(len(sources))])

        fig, ax = plt.subplots()
        wedges, texts, autotexts = ax.pie(
            counts,
            labels=sources,
            autopct="%1.1f%%",
            colors=colors,
            startangle=90,
            wedgeprops={"linewidth": 1, "edgecolor": "white"},
        )
        for autotext in autotexts:
            autotext.set_color("white")
            autotext.set_fontweight("bold")

        ax.set_title(f"Tasks by Source (Total: {sum(counts)})")
        ax.axis("equal")

        plt.tight_layout()
        filepath = self.charts_dir / "tasks_by_source.png"
        plt.savefig(filepath, bbox_inches="tight")
        plt.close()
        self.generated_charts.append(str(filepath))
        return str(filepath)

    def plot_publication_timeline(self, tasks: list[dict]) -> str:
        records = []
        for task in tasks:
            posted_at = task.get("posted_at")
            if posted_at and isinstance(posted_at, datetime):
                records.append(posted_at.date())

        if not records:
            return ""

        date_counts = Counter(records)
        dates = sorted(date_counts.keys())
        counts = [date_counts[d] for d in dates]

        fig, ax = plt.subplots(figsize=(16, 6))
        ax.fill_between(range(len(dates)), counts, alpha=0.3, color="steelblue")
        ax.plot(
            range(len(dates)),
            counts,
            marker="o",
            linestyle="-",
            color="steelblue",
            markersize=4,
        )

        ax.set_xticks(range(len(dates)))
        ax.set_xticklabels(
            [d.strftime("%m/%d") for d in dates], rotation=45, ha="right"
        )
        ax.set_xlabel("Date")
        ax.set_ylabel("Number of Tasks")
        ax.set_title("Publication Timeline")
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        filepath = self.charts_dir / "publication_timeline.png"
        plt.savefig(filepath, bbox_inches="tight")
        plt.close()
        self.generated_charts.append(str(filepath))
        return str(filepath)

    def plot_technology_distribution(self, tasks: list[dict]) -> str:
        tech_counter = Counter()
        for task in tasks:
            techs = task.get("technologies", [])
            if isinstance(techs, list):
                for tech in techs:
                    if isinstance(tech, str):
                        tech_counter[tech] += 1

        if not tech_counter:
            return ""

        sorted_techs = tech_counter.most_common(15)
        techs, counts = zip(*sorted_techs)

        fig, ax = plt.subplots(figsize=(12, 8))
        colors = plt.cm.magma([i / len(techs) for i in range(len(techs))])
        bars = ax.barh(range(len(techs)), counts, color=colors)
        ax.set_yticks(range(len(techs)))
        ax.set_yticklabels(techs)
        ax.set_xlabel("Number of Mentions")
        ax.set_title("Top 15 Technologies Mentioned")
        ax.invert_yaxis()

        for bar, count in zip(bars, counts):
            ax.text(
                bar.get_width() + 0.5,
                bar.get_y() + bar.get_height() / 2,
                str(count),
                va="center",
            )

        plt.tight_layout()
        filepath = self.charts_dir / "technology_distribution.png"
        plt.savefig(filepath, bbox_inches="tight")
        plt.close()
        self.generated_charts.append(str(filepath))
        return str(filepath)

    def plot_budget_histogram(self, tasks: list[dict]) -> str:
        budgets = []
        for task in tasks:
            b = task.get("budget_min") or task.get("budget_max")
            if b and 0 < b < 100000:
                budgets.append(b)

        if not budgets:
            return ""

        fig, ax = plt.subplots(figsize=(14, 6))
        n, bins, patches = ax.hist(
            budgets, bins=30, color="steelblue", edgecolor="white", alpha=0.8
        )

        mean_val = sum(budgets) / len(budgets)
        median_val = sorted(budgets)[len(budgets) // 2]

        ax.axvline(
            mean_val,
            color="red",
            linestyle="--",
            linewidth=2,
            label=f"Mean: ₽{mean_val:,.0f}",
        )
        ax.axvline(
            median_val,
            color="green",
            linestyle="--",
            linewidth=2,
            label=f"Median: ₽{median_val:,.0f}",
        )

        ax.set_xlabel("Budget (₽)")
        ax.set_ylabel("Frequency")
        ax.set_title("Budget Distribution (Tasks)")
        ax.legend()
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        filepath = self.charts_dir / "budget_histogram.png"
        plt.savefig(filepath, bbox_inches="tight")
        plt.close()
        self.generated_charts.append(str(filepath))
        return str(filepath)

    def plot_competition_heatmap(self, tasks: list[dict]) -> str:
        records = []
        for task in tasks:
            proposals = task.get("proposals_count")
            budget = task.get("budget_min") or task.get("budget_max")
            if proposals is not None and budget and budget > 0:
                records.append(
                    {
                        "category": task.get("normalized_category", "OTHER"),
                        "proposals": proposals,
                        "budget": budget,
                    }
                )

        if not records:
            return ""

        df = pd.DataFrame(records)
        pivot = df.pivot_table(
            index="category",
            values=["proposals", "budget"],
            aggfunc={"proposals": "mean", "budget": "mean"},
        ).dropna()

        if pivot.empty or len(pivot) < 3:
            return ""

        fig, ax = plt.subplots(figsize=(12, 8))
        scatter = ax.scatter(
            pivot["proposals"],
            pivot["budget"],
            c=range(len(pivot)),
            cmap="viridis",
            s=100,
            alpha=0.8,
            edgecolors="black",
            linewidth=0.5,
        )

        for idx, row in pivot.iterrows():
            ax.annotate(
                idx,
                (row["proposals"], row["budget"]),
                fontsize=9,
                alpha=0.8,
                xytext=(5, 5),
                textcoords="offset points",
            )

        ax.set_xlabel("Average Proposals")
        ax.set_ylabel("Average Budget (₽)")
        ax.set_title("Competition vs Budget by Category")
        ax.grid(True, alpha=0.3)

        median_proposals = pivot["proposals"].median()
        median_budget = pivot["budget"].median()
        ax.axvline(median_proposals, color="gray", linestyle=":", alpha=0.5)
        ax.axhline(median_budget, color="gray", linestyle=":", alpha=0.5)

        plt.tight_layout()
        filepath = self.charts_dir / "competition_heatmap.png"
        plt.savefig(filepath, bbox_inches="tight")
        plt.close()
        self.generated_charts.append(str(filepath))
        return str(filepath)

    def plot_category_vs_budget(self, tasks: list[dict]) -> str:
        records = []
        for task in tasks:
            budget = task.get("budget_min") or task.get("budget_max")
            if budget and budget > 0:
                records.append(
                    {
                        "category": task.get("normalized_category", "OTHER"),
                        "budget": budget,
                    }
                )

        if not records:
            return ""

        df = pd.DataFrame(records)
        stats = (
            df.groupby("category")["budget"]
            .agg(["mean", "count"])
            .sort_values("mean", ascending=False)
            .head(15)
        )

        fig, ax1 = plt.subplots(figsize=(14, 7))

        x = range(len(stats))
        bars = ax1.bar(
            x, stats["mean"], color="steelblue", alpha=0.8, label="Avg Budget"
        )

        ax2 = ax1.twinx()
        ax2.plot(
            x, stats["count"], "ro-", markersize=8, linewidth=2, label="Task Count"
        )

        ax1.set_xticks(x)
        ax1.set_xticklabels(stats.index, rotation=45, ha="right")
        ax1.set_ylabel("Average Budget (₽)")
        ax2.set_ylabel("Number of Tasks")
        ax1.set_title("Average Budget and Task Count by Category")

        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper right")

        plt.tight_layout()
        filepath = self.charts_dir / "category_vs_budget.png"
        plt.savefig(filepath, bbox_inches="tight")
        plt.close()
        self.generated_charts.append(str(filepath))
        return str(filepath)
