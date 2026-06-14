"""
Unit tests for the analytics modules (categories, technologies, budgets, competition, trends).
"""

import pytest
from datetime import datetime, timedelta, timezone
from analytics.categories import CategoryNormalizer, classify_task, CATEGORY_KEYWORDS
from analytics.technologies import TechnologyExtractor
from analytics.budgets import BudgetAnalyzer
from analytics.competition import CompetitionAnalyzer
from analytics.trends import TrendAnalyzer


class TestCategoryNormalizer:
    def setup_method(self) -> None:
        self.normalizer = CategoryNormalizer()

    def test_wordpress_classification(self) -> None:
        category = self.normalizer.normalize(
            "Need WordPress developer for custom theme",
            "Looking for an experienced WordPress developer to create a custom theme with Elementor",
        )
        assert category == "WordPress"

    def test_react_classification(self) -> None:
        category = self.normalizer.normalize(
            "React Frontend Developer",
            "Need a React developer with Redux experience for SPA",
        )
        assert category == "React"

    def test_backend_classification(self) -> None:
        category = self.normalizer.normalize(
            "Backend API Developer",
            "Build REST API with authentication and database integration",
        )
        assert category == "Backend"

    def test_ai_chatbot_classification(self) -> None:
        category = self.normalizer.normalize(
            "AI Chatbot with GPT-4",
            "Build a conversational AI chatbot using OpenAI API with custom knowledge base",
        )
        assert category == "AI Chatbots"

    def test_other_classification(self) -> None:
        category = self.normalizer.normalize(
            "Need help with Excel spreadsheet",
            "Need to create formulas and macros in Excel",
        )
        assert category == "OTHER"

    def test_classify_task_function(self) -> None:
        cat, score = classify_task("Build Django web application with PostgreSQL")
        assert cat == "Django"
        assert score > 0

    def test_category_keywords_not_empty(self) -> None:
        assert len(CATEGORY_KEYWORDS) >= 36

    def test_docker_classification(self) -> None:
        category = self.normalizer.normalize(
            "Docker container setup",
            "Need to containerize a Flask application with Docker compose",
        )
        assert category == "Docker"

    def test_fullstack_classification(self) -> None:
        category = self.normalizer.normalize(
            "Full Stack Developer MERN Stack",
            "Need a full stack developer for a MERN application",
        )
        assert category == "Fullstack"

    def test_rag_classification(self) -> None:
        category = self.normalizer.normalize(
            "RAG System with Vector Database",
            "Build a retrieval augmented generation system using LlamaIndex with Pinecone",
        )
        assert category == "RAG"


class TestTechnologyExtractor:
    def setup_method(self) -> None:
        self.extractor = TechnologyExtractor()

    def test_python_extraction(self) -> None:
        techs = self.extractor.extract("Python developer needed", "Write Python code")
        assert "Python" in techs

    def test_multiple_technologies(self) -> None:
        techs = self.extractor.extract(
            "Full Stack Developer",
            "React frontend with Django backend and PostgreSQL database",
        )
        assert "React" in techs
        assert "Django" in techs
        assert "PostgreSQL" in techs

    def test_docker_kubernetes(self) -> None:
        techs = self.extractor.extract(
            "DevOps Engineer", "Kubernetes cluster management with Docker containers"
        )
        assert "Docker" in techs
        assert "Kubernetes" in techs

    def test_react_native(self) -> None:
        techs = self.extractor.extract(
            "Mobile App Developer",
            "Build cross-platform app with React Native and Expo",
        )
        assert "React Native" in techs

    def test_empty_input(self) -> None:
        techs = self.extractor.extract("")
        assert techs == []

    def test_technology_frequencies(self) -> None:
        tasks = [
            {"technologies": ["Python", "Django"]},
            {"technologies": ["Python", "Flask"]},
            {"technologies": ["JavaScript", "React"]},
        ]
        freqs = self.extractor.get_technology_frequencies(tasks)
        assert freqs["Python"] == 2
        assert freqs["JavaScript"] == 1


class TestBudgetAnalyzer:
    def setup_method(self) -> None:
        self.analyzer = BudgetAnalyzer()

    def test_basic_analysis(self) -> None:
        tasks = [
            {"budget_min": 100, "budget_max": 200, "normalized_category": "Frontend"},
            {"budget_min": 500, "budget_max": 1000, "normalized_category": "Backend"},
            {"budget_min": 1000, "budget_max": 2000, "normalized_category": "Backend"},
        ]
        result = self.analyzer.analyze(tasks)
        assert result["average_budget_min"] == pytest.approx(533.33, rel=0.01)
        assert result["median_budget_min"] == 500
        assert result["total_tasks_with_budget"] == 3

    def test_empty_tasks(self) -> None:
        result = self.analyzer.analyze([])
        assert result["average_budget_min"] is None
        assert result["total_tasks_with_budget"] == 0

    def test_budget_distribution(self) -> None:
        tasks = [
            {"budget_min": 100, "budget_max": 200, "normalized_category": "Test"},
            {"budget_min": 200, "budget_max": 300, "normalized_category": "Test"},
            {"budget_min": 300, "budget_max": 400, "normalized_category": "Test"},
        ]
        dist = self.analyzer.budget_distribution(tasks, bins=3)
        assert len(dist["bins"]) == 3
        assert sum(dist["counts"]) == 3

    def test_category_budgets(self) -> None:
        tasks = [
            {"budget_min": 100, "normalized_category": "Frontend"},
            {"budget_min": 200, "normalized_category": "Frontend"},
            {"budget_min": 150, "normalized_category": "Frontend"},
            {"budget_min": 500, "normalized_category": "Backend"},
            {"budget_min": 600, "normalized_category": "Backend"},
            {"budget_min": 700, "normalized_category": "Backend"},
        ]
        result = self.analyzer.analyze(tasks)
        assert result["category_average_budgets"]["Frontend"] == pytest.approx(
            150, rel=0.01
        )
        assert result["category_average_budgets"]["Backend"] == pytest.approx(
            600, rel=0.01
        )


class TestCompetitionAnalyzer:
    def setup_method(self) -> None:
        self.analyzer = CompetitionAnalyzer()

    def test_competition_analysis(self) -> None:
        tasks = [
            {"proposals_count": 10, "normalized_category": "Frontend"},
            {"proposals_count": 20, "normalized_category": "Frontend"},
            {"proposals_count": 5, "normalized_category": "Backend"},
        ]
        result = self.analyzer.analyze(tasks)
        assert result["overall_average_proposals"] == pytest.approx(11.67, rel=0.01)
        assert result["average_proposals_per_category"]["Frontend"] == 15
        assert result["average_proposals_per_category"]["Backend"] == 5

    def test_empty_tasks(self) -> None:
        result = self.analyzer.analyze([])
        assert result["overall_average_proposals"] is None

    def test_undervalued_categories(self) -> None:
        tasks = [
            {
                "proposals_count": 2,
                "budget_min": 1000,
                "normalized_category": "Frontend",
            },
            {
                "proposals_count": 3,
                "budget_min": 1200,
                "normalized_category": "Frontend",
            },
            {
                "proposals_count": 3,
                "budget_min": 1100,
                "normalized_category": "Frontend",
            },
            {
                "proposals_count": 20,
                "budget_min": 500,
                "normalized_category": "Backend",
            },
            {
                "proposals_count": 25,
                "budget_min": 600,
                "normalized_category": "Backend",
            },
            {
                "proposals_count": 22,
                "budget_min": 550,
                "normalized_category": "Backend",
            },
        ]
        df = self.analyzer.find_undervalued_categories(tasks)
        assert not df.empty
        assert (
            "frontend" in df["category"].str.lower().values
            or "Frontend" in df["category"].values
        )


class TestTrendAnalyzer:
    def setup_method(self) -> None:
        self.analyzer = TrendAnalyzer()

    def test_fastest_growing(self) -> None:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        tasks = [
            {"normalized_category": "Frontend", "posted_at": now - timedelta(days=10)},
            {"normalized_category": "Frontend", "posted_at": now - timedelta(hours=6)},
            {"normalized_category": "Backend", "posted_at": now - timedelta(days=20)},
            {
                "normalized_category": "AI Chatbots",
                "posted_at": now - timedelta(hours=3),
            },
        ]
        growing = self.analyzer.fastest_growing_categories(tasks)
        assert len(growing) > 0

    def test_highest_paying(self) -> None:
        tasks = [
            {"normalized_category": "DevOps", "budget_min": 5000, "budget_max": 10000},
            {"normalized_category": "DevOps", "budget_min": 3000, "budget_max": 6000},
            {"normalized_category": "Frontend", "budget_min": 500, "budget_max": 1000},
            {"normalized_category": "Frontend", "budget_min": 300, "budget_max": 800},
        ]
        paying = self.analyzer.highest_paying_categories(tasks)
        assert paying[0]["category"] == "DevOps"
        assert paying[0]["avg_budget"] > paying[1]["avg_budget"]

    def test_empty_tasks(self) -> None:
        growing = self.analyzer.fastest_growing_categories([])
        assert growing == []
