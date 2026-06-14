#!/usr/bin/env python3
"""
Freelance Market Analyzer

Main entry point for the freelance market data collection and analysis system.
Collects tasks from multiple freelance platforms, normalizes them into
standard categories, performs analytics, generates charts, and exports
results to Excel.
"""

import sys
import asyncio
import json
import ssl
import urllib.request
from typing import Optional
from pathlib import Path
from datetime import datetime
from collections import Counter
import argparse

from loguru import logger

from core.settings import settings
from core.logger import setup_logger
from core.database import init_db, check_db_connection
from core.models import Base

from scrapers.base import TaskData
from scrapers.upwork import UpworkScraper
from scrapers.freelancer import FreelancerScraper
from scrapers.guru import GuruScraper
from scrapers.fl import FLScraper
from scrapers.kwork import KworkScraper
from scrapers.freelancehunt import FreelancehuntScraper

from analytics.categories import normalizer, classify_task
from analytics.technologies import extractor
from analytics.budgets import BudgetAnalyzer
from analytics.competition import CompetitionAnalyzer
from analytics.trends import TrendAnalyzer

from export.excel_export import ExcelExporter
from reports.charts import ChartGenerator


USD_TO_RUB_FALLBACK: float = 90.0


def get_usd_to_rub_rate() -> float:
    try:
        url = "https://open.er-api.com/v6/latest/USD"
        ctx = ssl._create_unverified_context()
        with urllib.request.urlopen(url, timeout=5, context=ctx) as resp:
            data = json.loads(resp.read().decode())
            rate = data["rates"]["RUB"]
            logger.info("USD/RUB rate fetched from open.er-api.com: {}", rate)
            return float(rate)
    except Exception as e:
        logger.warning(
            "Failed to fetch USD/RUB rate ({}), using fallback: {}",
            e,
            USD_TO_RUB_FALLBACK,
        )
        return USD_TO_RUB_FALLBACK


SCRAPER_MAP: dict[str, type] = {
    "upwork": UpworkScraper,
    "freelancer": FreelancerScraper,
    "guru": GuruScraper,
    "fl": FLScraper,
    "kwork": KworkScraper,
    "freelancehunt": FreelancehuntScraper,
}


class FreelanceMarketAnalyzer:
    def __init__(self, scrapers_to_run: Optional[list[str]] = None) -> None:
        self.scrapers_to_run = scrapers_to_run or settings.scrapers_enabled
        self.tasks: list[dict] = []
        self.analytics: dict = {}
        self.excel_exporter = ExcelExporter()
        self.chart_generator = ChartGenerator()
        self.budget_analyzer = BudgetAnalyzer()
        self.competition_analyzer = CompetitionAnalyzer()
        self.trend_analyzer = TrendAnalyzer()

        logger.info(
            "Initialized FreelanceMarketAnalyzer with scrapers: {}",
            self.scrapers_to_run,
        )

    async def collect_all(self) -> list[dict]:
        all_tasks: list[TaskData] = []
        self.active_sources: list[str] = []

        for scraper_name in self.scrapers_to_run:
            if scraper_name not in SCRAPER_MAP:
                logger.warning("Unknown scraper: {}, skipping", scraper_name)
                continue

            scraper_class = SCRAPER_MAP[scraper_name]
            scraper = scraper_class()
            try:
                tasks = await scraper.collect()
                all_tasks.extend(tasks)
                if tasks:
                    self.active_sources.append(scraper_name)
                logger.info("Collected {} tasks from {}", len(tasks), scraper_name)
            except Exception as e:
                logger.error("Failed to collect tasks from {}: {}", scraper_name, e)
            finally:
                await scraper.close()

        self.tasks = [t.to_dict() if isinstance(t, TaskData) else t for t in all_tasks]
        logger.info(
            "Total tasks collected: {} (from {})", len(self.tasks), self.active_sources
        )
        return self.tasks

    def normalize_categories(self) -> None:
        for task in self.tasks:
            if task.get("normalized_category"):
                continue
            title = task.get("title", "")
            description = task.get("description")
            category_raw = task.get("category_raw")
            task["normalized_category"] = normalizer.normalize(
                title, description, category_raw
            )

        category_counts = Counter(
            t.get("normalized_category", "OTHER") for t in self.tasks
        )
        logger.info(
            "Categories normalized. Distribution: {}",
            dict(category_counts.most_common(10)),
        )

    def extract_technologies(self) -> None:
        for task in self.tasks:
            title = task.get("title", "")
            description = task.get("description")
            existing = task.get("technologies", [])
            if not isinstance(existing, list):
                existing = []
            task["technologies"] = extractor.extract(title, description, existing)

        all_techs = []
        for task in self.tasks:
            techs = task.get("technologies", [])
            if isinstance(techs, list):
                all_techs.extend(techs)
        tech_counts = Counter(all_techs)
        logger.info(
            "Technologies extracted. Top: {}", dict(tech_counts.most_common(10))
        )

    def run_analytics(self) -> dict:
        category_counts = Counter(
            t.get("normalized_category", "OTHER") for t in self.tasks
        )
        all_techs = []
        for task in self.tasks:
            techs = task.get("technologies", [])
            if isinstance(techs, list):
                all_techs.extend(techs)
        tech_counts = Counter(all_techs)

        budget_analysis = self.budget_analyzer.analyze(self.tasks)
        competition_analysis = self.competition_analyzer.analyze(self.tasks)

        fastest_growing = self.trend_analyzer.fastest_growing_categories(self.tasks)
        highest_paying = self.trend_analyzer.highest_paying_categories(self.tasks)

        self.analytics = {
            "total_tasks": len(self.tasks),
            "category_counts": dict(category_counts.most_common()),
            "technology_counts": dict(tech_counts.most_common()),
            "budget_analysis": budget_analysis,
            "competition_analysis": competition_analysis,
            "fastest_growing_categories": fastest_growing,
            "highest_paying_categories": highest_paying,
            "sources": self.active_sources,
        }

        logger.info(
            "Analytics complete: {} categories, {} technologies, {} tasks",
            len(category_counts),
            len(tech_counts),
            len(self.tasks),
        )
        return self.analytics

    def print_summary(self) -> None:
        if not self.analytics:
            logger.warning("No analytics data to summarize")
            return

        print("\n" + "=" * 70)
        print("  FREELANCE MARKET ANALYSIS REPORT")
        print("=" * 70)
        print(f"  Total tasks analyzed: {self.analytics['total_tasks']}")
        print(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("-" * 70)

        print("\n  TOP 10 CATEGORIES:")
        print(f"  {'Category':<25} {'Count':<8} {'Share':<8}")
        print(f"  {'-' * 25} {'-' * 8} {'-' * 8}")
        total = self.analytics["total_tasks"] or 1
        for i, (cat, count) in enumerate(
            sorted(
                self.analytics["category_counts"].items(),
                key=lambda x: x[1],
                reverse=True,
            )[:10]
        ):
            share = count / total * 100
            print(f"  {cat:<25} {count:<8} {share:>5.1f}%")

        ba = self.analytics.get("budget_analysis", {})
        print(f"\n  BUDGET STATISTICS:")
        print(f"  Average budget: ₽{(ba.get('average_budget_min') or 0):,.2f}")
        print(f"  Median budget: ₽{(ba.get('median_budget_min') or 0):,.2f}")
        print(
            f"  Budget range: ₽{(ba.get('min_budget') or 0):,.2f} - ₽{(ba.get('max_budget') or 0):,.2f}"
        )

        ca = self.analytics.get("competition_analysis", {})
        print(f"\n  COMPETITION:")
        print(
            f"  Average proposals per task: {(ca.get('overall_average_proposals') or 0):.1f}"
        )
        print(
            f"  Most competitive: {list(ca.get('most_competitive_categories', {}).keys())[:5]}"
        )

        print(f"\n  FASTEST GROWING CATEGORIES:")
        for item in self.analytics.get("fastest_growing_categories", [])[:5]:
            print(f"  {item['category']:<25} +{item['growth_percent']:.1f}%")

        print(f"\n  HIGHEST PAYING CATEGORIES:")
        for item in self.analytics.get("highest_paying_categories", [])[:5]:
            print(f"  {item['category']:<25} ₽{item['avg_budget']:,.2f}")

        print("=" * 70 + "\n")

    def export_results(self) -> Path:
        excel_path = self.excel_exporter.export(self.tasks, self.analytics)
        logger.info("Excel report exported to {}", excel_path)
        return excel_path

    def generate_demo_data(self) -> None:
        from datetime import timedelta
        import random

        random.seed(42)
        from datetime import timezone

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        sources = ["upwork", "freelancer", "guru", "fl", "kwork", "freelancehunt"]

        TASKS_PER_GROUP = 40
        usd_to_rub = get_usd_to_rub_rate()

        category_templates = [
            {
                "prefix": "WP",
                "slug": "wp",
                "titles": [
                    "WordPress Developer for E-commerce Site",
                    "Создание сайта на WordPress",
                    "WordPress Plugin Development",
                    "Доработка WooCommerce магазина",
                    "WordPress Speed Optimization",
                    "Кастомизация темы WordPress",
                    "WordPress Bug Fixes and Security",
                    "Сайт-визитка на WordPress",
                    "Custom WordPress Theme from Scratch",
                    "Интернет-магазин на WordPress + WooCommerce",
                    "WordPress SEO Optimization and Meta Tags",
                    "Разработка сайта на WordPress с Elementor",
                    "WordPress Multisite Network Setup",
                    "WordPress REST API Development",
                    "Migrate website to WordPress CMS",
                ],
                "descriptions": [
                    "Need an experienced WordPress developer to build a WooCommerce store with custom theme",
                    "Разработка сайта на WordPress с кастомной темой и Elementor",
                    "Custom WordPress plugin with API integration and admin panel",
                    "Настройка WooCommerce, добавление плагинов доставки и оплаты",
                    "Optimize WordPress site loading speed, caching, CDN setup",
                    "Доработка существующей темы WordPress под дизайн-макет",
                    "Fix security vulnerabilities, update plugins, harden WordPress",
                    "Создание сайта-визитки на WordPress с формой обратной связи",
                    "Build a custom WordPress theme with ACF, custom post types, Gutenberg blocks",
                    "Полноценный интернет-магазин на WooCommerce с каталогом и корзиной",
                    "Complete SEO: meta tags, sitemap, schema markup, speed optimization for WordPress",
                    "Разработка сайта на WordPress с использованием Elementor и ACF Pro",
                    "Set up WordPress Multisite network with custom domain mapping",
                    "Build custom REST API endpoints for headless WordPress CMS",
                    "Перенос существующего сайта на WordPress с сохранением SEO и трафика",
                ],
                "budgets": [
                    ("USD", 1500, 3000),
                    ("RUB", 30000, 60000),
                    ("USD", 500, 2000),
                    ("RUB", 15000, 30000),
                    ("USD", 300, 800),
                    ("RUB", 10000, 20000),
                    ("USD", 200, 600),
                    ("RUB", 8000, 15000),
                    ("USD", 2000, 5000),
                    ("RUB", 25000, 50000),
                    ("USD", 500, 1500),
                    ("RUB", 12000, 25000),
                ],
                "proposals": (4, 35),
            },
            {
                "prefix": "FB",
                "slug": "frontend",
                "titles": [
                    "React Frontend Developer for SPA",
                    "Верстка лендинга по макету Figma",
                    "React Component Library with Storybook",
                    "Верстка интернет-магазина на Next.js",
                    "Vue.js Dashboard for Analytics",
                    "React Native Mobile App UI",
                    "Адаптация сайта под мобильные устройства",
                    "Angular Enterprise Application",
                    "Tailwind CSS to HTML Conversion",
                    "Сложная анимация на CSS/JS",
                    "TypeScript React Application Architecture",
                    "Next.js Full Stack Application",
                    "Svelte Frontend for SaaS Platform",
                    "Redesign and Refactor Legacy Frontend",
                    "Progressive Web App with React",
                ],
                "descriptions": [
                    "Build a SPA with React, TypeScript, Redux, and Material UI",
                    "Адаптивная верстка лендинга на HTML/CSS/JS по макету из Figma",
                    "Create a reusable React component library with Storybook and unit tests",
                    "Фронтенд для интернет-магазина на Next.js + TypeScript",
                    "Build an analytics dashboard with Vue 3, Chart.js, and Vuex",
                    "Implement pixel-perfect UI screens in React Native from design specs",
                    "Сделать существующий сайт адаптивным под все устройства",
                    "Build enterprise-grade Angular app with NgRx, lazy loading, i18n",
                    "Convert Figma designs to HTML with Tailwind CSS and animations",
                    "Реализация сложной анимации интерфейса на чистом CSS и JavaScript",
                    "Architect and build React TypeScript application with best practices",
                    "Full-stack Next.js application with SSR, API routes, and authentication",
                    "Build responsive Svelte frontend for B2B SaaS analytics platform",
                    "Refactor legacy jQuery codebase to modern React with TypeScript",
                    "Build progressive web app with offline support and push notifications",
                ],
                "budgets": [
                    ("USD", 2000, 5000),
                    ("RUB", 15000, 25000),
                    ("USD", 3000, 8000),
                    ("RUB", 25000, 45000),
                    ("USD", 2500, 6000),
                    ("USD", 3000, 7000),
                    ("RUB", 10000, 20000),
                    ("USD", 5000, 12000),
                    ("USD", 800, 2000),
                    ("RUB", 8000, 15000),
                    ("USD", 4000, 10000),
                    ("RUB", 20000, 40000),
                ],
                "proposals": (5, 40),
            },
            {
                "prefix": "BE",
                "slug": "backend",
                "titles": [
                    "Python Backend API Developer",
                    "Разработка API на Django Rest Framework",
                    "GraphQL API with Node.js",
                    "Микросервисная архитектура на FastAPI",
                    "Node.js WebSocket Server",
                    "Разработка CRM системы на Laravel",
                    "Go Microservice Development",
                    "REST API for Mobile App (Ruby on Rails)",
                    ".NET Core Web API Development",
                    "Backend for E-commerce Platform",
                    "Java Spring Boot Microservices",
                    "Express.js API with PostgreSQL",
                    "NestJS Backend for Real-time App",
                    "API Gateway with Kong and Kubernetes",
                    "Serverless Backend with AWS Lambda",
                ],
                "descriptions": [
                    "Develop REST API with FastAPI, PostgreSQL, and Redis caching",
                    "DRF бэкенд для мобильного приложения с JWT аутентификацией",
                    "Build GraphQL API with Apollo Server, TypeScript, and Prisma ORM",
                    "Разработка системы микросервисов на FastAPI с RabbitMQ",
                    "Build a real-time WebSocket server with Socket.io and Redis pub/sub",
                    "Создание CRM с модулями клиентов, сделок и отчетов",
                    "Build a high-performance microservice in Go with gRPC and Kafka",
                    "Create RESTful API for a mobile app using Ruby on Rails and PostgreSQL",
                    "Build .NET Core Web API with Entity Framework, Azure SQL, Swagger",
                    "Full backend for e-commerce: catalog, cart, checkout, payment integration",
                    "Develop Java Spring Boot microservices with Eureka and Hibernate",
                    "Build Express.js REST API with PostgreSQL, Redis caching, JWT auth",
                    "NestJS backend with WebSockets, GraphQL, and microservices",
                    "Set up API Gateway pattern with Kong, rate limiting, and service discovery",
                    "Build serverless backend with AWS Lambda, API Gateway, and DynamoDB",
                ],
                "budgets": [
                    ("USD", 3000, 8000),
                    ("RUB", 40000, 80000),
                    ("USD", 2500, 6000),
                    ("RUB", 50000, 100000),
                    ("USD", 1500, 4000),
                    ("RUB", 60000, 120000),
                    ("USD", 4000, 10000),
                    ("USD", 3000, 8000),
                    ("USD", 3500, 9000),
                    ("USD", 5000, 12000),
                    ("USD", 6000, 15000),
                    ("RUB", 30000, 70000),
                ],
                "proposals": (3, 28),
            },
            {
                "prefix": "TG",
                "slug": "bots",
                "titles": [
                    "Telegram Bot for Online Store",
                    "Написать Telegram бота на Python",
                    "Telegram Bot with AI Chat",
                    "Discord Bot for Server Management",
                    "Создание телеграм бота для магазина",
                    "Multi-functional Telegram Bot",
                    "Discord Bot with Economy System",
                    "Telegram Bot for Notification System",
                    "Чат-бот для Telegram с ИИ",
                    "Discord.js Bot with Dashboard",
                    "Telegram Bot with PostgreSQL Storage",
                    "Slack Bot for Workflow Automation",
                    "WhatsApp Business API Integration",
                    "Telegram Bot for Crypto Trading Signals",
                    "Multi-platform Bot (Telegram + Discord)",
                ],
                "descriptions": [
                    "Create a Telegram bot for order tracking using aiogram and PostgreSQL",
                    "Telegram бот для автоматизации заказов с интеграцией CRM",
                    "Telegram bot with GPT-4 integration for customer support automation",
                    "Discord bot with moderation, music, and leveling system using discord.py",
                    "Телеграм бот для интернет-магазина с корзиной и оплатой",
                    "Telegram bot with custom keyboard, inline modes, and admin panel",
                    "Discord bot with virtual economy, RPG game, and voice channel features",
                    "Bot that monitors services and sends alerts to Telegram channels",
                    "Telegram бот с искусственным интеллектом на базе GPT для консультаций",
                    "Discord bot with web dashboard for configuration and analytics",
                    "Telegram bot with PostgreSQL for storing user data and order history",
                    "Build Slack bot for automating team workflows and notifications",
                    "Integrate WhatsApp Business API for customer communication automation",
                    "Telegram bot for tracking cryptocurrency prices and trading signals",
                    "Develop multi-platform bot working on both Telegram and Discord",
                ],
                "budgets": [
                    ("USD", 500, 1500),
                    ("RUB", 10000, 20000),
                    ("USD", 800, 2500),
                    ("USD", 400, 1200),
                    ("RUB", 8000, 15000),
                    ("USD", 1000, 3000),
                    ("USD", 600, 1800),
                    ("USD", 400, 1000),
                    ("RUB", 15000, 30000),
                    ("USD", 1500, 4000),
                    ("USD", 700, 2000),
                    ("RUB", 12000, 25000),
                ],
                "proposals": (4, 30),
            },
            {
                "prefix": "AI",
                "slug": "ai",
                "titles": [
                    "AI Chatbot with GPT-4 Integration",
                    "RAG System for Document Q&A",
                    "Разработка AI-агента для автоматизации",
                    "OpenAI API Integration Project",
                    "Fine-tuning LLM Model",
                    "Claude API Integration",
                    "AI Image Generation Service",
                    "Внедрение ChatGPT в бизнес-процессы",
                    "AI Voice Assistant Development",
                    "Multi-Agent AI System",
                    "LLM Evaluation and Benchmarking",
                    "Prompt Engineering and Optimization",
                    "AI Content Moderation System",
                    "Text-to-Speech with AI Voices",
                    "Custom AI Training Pipeline",
                ],
                "descriptions": [
                    "Build an AI chatbot using OpenAI GPT-4 with custom knowledge base and memory",
                    "Implement RAG pipeline with LangChain, Pinecone vector DB, and LlamaIndex",
                    "AI-агент на базе LLM для автоматизации бизнес-процессов",
                    "Integrate OpenAI APIs (GPT-4, Whisper, DALL-E) into existing application",
                    "Fine-tune LLaMA/Mistral model on custom dataset with LoRA",
                    "Integrate Anthropic Claude API for content generation and analysis",
                    "Build image generation service using Stable Diffusion or DALL-E API",
                    "Интеграция ChatGPT в существующие бизнес-процессы компании",
                    "Voice assistant with speech recognition, NLP, and text-to-speech",
                    "Build multi-agent system with CrewAI for complex task automation",
                    "Evaluate LLM performance on custom metrics and benchmark datasets",
                    "Develop and optimize prompt templates for production AI applications",
                    "Build AI-powered content moderation with custom safety filters",
                    "Implement realistic text-to-speech using ElevenLabs or Azure TTS",
                    "Create custom ML training pipeline for domain-specific AI models",
                ],
                "budgets": [
                    ("USD", 3000, 8000),
                    ("USD", 5000, 12000),
                    ("RUB", 40000, 80000),
                    ("USD", 2000, 5000),
                    ("USD", 4000, 10000),
                    ("USD", 2500, 6000),
                    ("USD", 2000, 5000),
                    ("RUB", 20000, 50000),
                    ("USD", 5000, 12000),
                    ("USD", 8000, 20000),
                    ("USD", 3000, 7000),
                    ("RUB", 30000, 60000),
                ],
                "proposals": (2, 20),
            },
            {
                "prefix": "SC",
                "slug": "scraping",
                "titles": [
                    "Parse Data from Multiple Websites",
                    "Парсинг сайтов и сбор данных",
                    "Automated Data Pipeline",
                    "Настройка n8n для автоматизации",
                    "Web Scraping with Playwright",
                    "n8n Workflow Automation",
                    "Zapier Integration for CRM",
                    "Make.com Scenario Development",
                    "Автоматизация отчетов в Power BI",
                    "Real-time Data Pipeline with Kafka",
                    "ETL Pipeline for Data Warehouse",
                    "Scrape E-commerce Product Data",
                    "Automated Web Monitoring System",
                    "Data Extraction for Market Research",
                    "API Data Aggregation Service",
                ],
                "descriptions": [
                    "Web scraping project using Python, BeautifulSoup, and proxy rotation",
                    "Сбор данных с маркетплейсов на Python с поддержкой прокси",
                    "Build automated ETL pipeline with Airflow, Pandas, and PostgreSQL",
                    "Настройка n8n workflow automation для интеграции сервисов",
                    "Scrape JavaScript-rendered websites using Playwright and Python",
                    "Create complex n8n workflows for business process automation",
                    "Set up Zapier integrations between CRM, email, and project management",
                    "Develop Make.com (Integromat) scenarios for data synchronization",
                    "Автоматическая генерация отчетов в Power BI из данных 1С",
                    "Build real-time data processing pipeline with Kafka, Spark, and Cassandra",
                    "Design ETL pipeline for loading data into Snowflake data warehouse",
                    "Scrape product listings and pricing data from multiple e-commerce sites",
                    "Build automated monitoring system for website changes and alerts",
                    "Extract and structure data from multiple sources for market analysis",
                    "Aggregate data from multiple REST APIs into unified data service",
                ],
                "budgets": [
                    ("USD", 300, 800),
                    ("RUB", 8000, 15000),
                    ("USD", 2000, 5000),
                    ("RUB", 12000, 25000),
                    ("USD", 500, 1500),
                    ("USD", 1000, 3000),
                    ("USD", 400, 1200),
                    ("USD", 500, 1500),
                    ("RUB", 15000, 30000),
                    ("USD", 4000, 10000),
                    ("USD", 3000, 8000),
                    ("RUB", 10000, 20000),
                ],
                "proposals": (4, 50),
            },
            {
                "prefix": "ML",
                "slug": "data",
                "titles": [
                    "Machine Learning Model for Image Classification",
                    "Computer Vision: Object Detection System",
                    "Анализ данных и построение дашборда",
                    "Time Series Forecasting Model",
                    "SQL Database Optimization",
                    "Data Analytics Dashboard with Power BI",
                    "NLP Text Classification System",
                    "Рекомендательная система на ML",
                    "OCR System for Document Processing",
                    "Data Warehouse Architecture",
                    "Predictive Analytics Model",
                    "Sentiment Analysis Pipeline",
                    "Anomaly Detection System",
                    "Data Migration and ETL Process",
                    "Customer Segmentation Analysis",
                ],
                "descriptions": [
                    "Train a CNN model using TensorFlow for product image classification",
                    "Implement YOLO-based object detection for warehouse inventory tracking",
                    "Анализ данных компании, построение дашборда в Tableau/Metabase",
                    "Build time series forecasting model using Prophet or LSTM",
                    "Optimize complex SQL queries, add indexes, improve query performance",
                    "Create interactive Power BI dashboard with DAX measures and KPIs",
                    "Build NLP pipeline for text classification using transformers",
                    "Разработка рекомендательной системы на коллаборативной фильтрации",
                    "Build OCR system using Tesseract and OpenCV for invoice processing",
                    "Design and implement data warehouse with star schema and ETL processes",
                    "Build predictive model for customer churn using ensemble methods",
                    "Develop sentiment analysis pipeline for social media monitoring",
                    "Implement real-time anomaly detection for server metrics using ML",
                    "Migrate legacy data warehouse to cloud-based analytics solution",
                    "Perform customer segmentation using K-means clustering and PCA",
                ],
                "budgets": [
                    ("USD", 5000, 10000),
                    ("USD", 6000, 15000),
                    ("RUB", 20000, 40000),
                    ("USD", 3000, 8000),
                    ("USD", 1000, 3000),
                    ("USD", 2000, 5000),
                    ("USD", 4000, 10000),
                    ("RUB", 50000, 120000),
                    ("USD", 3000, 8000),
                    ("USD", 5000, 12000),
                    ("USD", 4000, 10000),
                    ("RUB", 25000, 50000),
                ],
                "proposals": (2, 25),
            },
            {
                "prefix": "MO",
                "slug": "mobile",
                "titles": [
                    "Flutter Mobile App Development",
                    "React Native App with Backend",
                    "Android App Development (Kotlin)",
                    "iOS App with SwiftUI",
                    "Создание мобильного приложения Flutter",
                    "Mobile App UI/UX Design + Development",
                    "Flutter App with BLoC Pattern",
                    "React Native E-commerce App",
                    "Android Auto and CarPlay App",
                    "Mobile AR Application",
                    "Ionic Cross-Platform Mobile App",
                    "Mobile App Testing and QA",
                    "App Store and Google Play Publishing",
                    "Mobile Chat Application",
                    "Health and Fitness Tracking App",
                ],
                "descriptions": [
                    "Build a cross-platform mobile app with Flutter and Dart",
                    "Full mobile app with React Native, Firebase, and push notifications",
                    "Native Android app with Kotlin, Jetpack Compose, and Material Design 3",
                    "Native iOS app with SwiftUI, Combine, and CoreData",
                    "Кроссплатформенное мобильное приложение на Flutter для доставки",
                    "Complete mobile app from design to App Store/Google Play release",
                    "Flutter app with BLoC state management, REST API, and local storage",
                    "Full e-commerce mobile app with React Native, payment gateway, admin panel",
                    "Develop Android Auto and Apple CarPlay app for music streaming service",
                    "Build augmented reality app with ARKit/ARCore for furniture visualization",
                    "Cross-platform mobile app using Ionic with Angular and Capacitor",
                    "Comprehensive testing strategy for mobile apps on real devices",
                    "Prepare and publish app to App Store and Google Play stores",
                    "Build real-time chat application with WebSockets and push notifications",
                    "Develop mobile health app with step tracking, nutrition logging, and charts",
                ],
                "budgets": [
                    ("USD", 3000, 7000),
                    ("USD", 5000, 12000),
                    ("USD", 3000, 8000),
                    ("USD", 4000, 10000),
                    ("RUB", 30000, 60000),
                    ("USD", 5000, 12000),
                    ("USD", 3500, 8000),
                    ("USD", 6000, 15000),
                    ("USD", 8000, 20000),
                    ("USD", 10000, 25000),
                    ("USD", 3000, 7000),
                    ("RUB", 20000, 40000),
                ],
                "proposals": (3, 20),
            },
            {
                "prefix": "DO",
                "slug": "devops",
                "titles": [
                    "Docker + Kubernetes Setup",
                    "DevOps настройка серверов",
                    "AWS Infrastructure as Code",
                    "CI/CD Pipeline with GitHub Actions",
                    "Kubernetes Cluster Migration",
                    "Prometheus + Grafana Monitoring",
                    "GitLab CI/CD + Kubernetes",
                    "Ansible Automation for Server Setup",
                    "Настройка мониторинга и алертинга",
                    "Terraform Multi-Cloud Setup",
                    "Cloud Migration to AWS/GCP/Azure",
                    "Database Administration and Optimization",
                    "SSL/TLS Certificate Management",
                    "Log Management with ELK Stack",
                    "Disaster Recovery Planning",
                ],
                "descriptions": [
                    "Set up Docker containers and Kubernetes cluster for microservices",
                    "Настройка CI/CD, Docker, мониторинг и логирование серверов",
                    "Set up AWS infrastructure using Terraform with EC2, RDS, S3, CloudFront",
                    "Build complete CI/CD pipeline with GitHub Actions, Docker, AWS ECR/ECS",
                    "Migrate existing Docker Compose setup to production Kubernetes cluster",
                    "Set up monitoring stack with Prometheus, Grafana, and alertmanager",
                    "Configure GitLab CI/CD with Kubernetes executor and Helm charts",
                    "Write Ansible playbooks for automated server provisioning and configuration",
                    "Настройка Zabbix/Prometheus + Grafana для мониторинга инфраструктуры",
                    "Terraform configuration for multi-cloud deployment (AWS + GCP + Azure)",
                    "Plan and execute cloud migration from on-premise to AWS",
                    "PostgreSQL DBA: backup, replication, performance tuning, migration",
                    "Set up automated SSL/TLS certificate renewal with Let's Encrypt",
                    "Deploy and configure ELK stack for centralized log management",
                    "Design disaster recovery strategy with automated failover and backups",
                ],
                "budgets": [
                    ("USD", 2000, 4000),
                    ("RUB", 15000, 30000),
                    ("USD", 3000, 8000),
                    ("USD", 1500, 4000),
                    ("USD", 5000, 12000),
                    ("USD", 2000, 5000),
                    ("USD", 2500, 6000),
                    ("USD", 1500, 3500),
                    ("RUB", 12000, 25000),
                    ("USD", 4000, 10000),
                    ("USD", 5000, 15000),
                    ("RUB", 25000, 50000),
                ],
                "proposals": (3, 20),
            },
            {
                "prefix": "QA",
                "slug": "qa",
                "titles": [
                    "Тестирование сайта и Telegram бота",
                    "QA Automation with Playwright",
                    "API Testing with Postman + Newman",
                    "Load Testing with k6",
                    "Mobile App Testing (iOS + Android)",
                    "Regression Test Suite Development",
                    "Security Audit and Penetration Testing",
                    "Тестирование производительности сайта",
                    "Cypress E2E Tests for SPA",
                    "Test Documentation and Test Cases",
                    "Automated UI Testing with Selenium",
                    "Integration Testing for Microservices",
                    "Performance Testing with JMeter",
                    "Database Testing and Data Validation",
                    "Accessibility Testing (WCAG Compliance)",
                ],
                "descriptions": [
                    "Функциональное тестирование веб-приложения и телеграм бота",
                    "Write automated E2E tests using Playwright and TypeScript",
                    "Create comprehensive API test suite with Postman and CI integration",
                    "Performance and load testing using Grafana k6 with custom scenarios",
                    "Manual and automated testing of mobile app on real devices",
                    "Build comprehensive regression test suite with pytest and Selenium",
                    "Security audit of web application: OWASP testing, vulnerability assessment",
                    "Нагрузочное тестирование веб-приложения с отчетом и рекомендациями",
                    "Write Cypress end-to-end tests for React SPA with CI integration",
                    "Create test plans, test cases, and QA documentation for web project",
                    "Build automated UI test suite with Selenium WebDriver and Python",
                    "Integration testing for distributed microservices architecture",
                    "Performance and stress testing with Apache JMeter and custom scripts",
                    "Data integrity testing: validate ETL pipelines and database migrations",
                    "WCAG 2.1 accessibility audit and remediation support for web app",
                ],
                "budgets": [
                    ("RUB", 8000, 15000),
                    ("USD", 2000, 5000),
                    ("USD", 800, 2000),
                    ("USD", 1500, 4000),
                    ("USD", 2000, 5000),
                    ("USD", 3000, 7000),
                    ("USD", 3000, 8000),
                    ("RUB", 10000, 20000),
                    ("USD", 2500, 6000),
                    ("USD", 500, 1500),
                    ("USD", 2000, 5000),
                    ("RUB", 12000, 25000),
                ],
                "proposals": (3, 35),
            },
            {
                "prefix": "SH",
                "slug": "fullstack",
                "titles": [
                    "Shopify Store Development",
                    "Создание интернет-магазина на Shopify",
                    "Shopify App Development",
                    "Tilda Website with Custom Blocks",
                    "Доработка сайта на Tilda",
                    "Shopify Migration from WooCommerce",
                    "Laravel + Vue.js Web Application",
                    "Автоматизация бизнес процессов",
                    "Fullstack: Next.js + Django + PostgreSQL",
                    "Сайт под ключ: Fullstack разработка",
                    "Full-stack SaaS Application",
                    "Django + React Web Platform",
                    "Custom CRM Development",
                    "API-first Web Application",
                    "MVP Development for Startup",
                ],
                "descriptions": [
                    "Full Shopify store setup with custom Liquid theme and apps",
                    "Разработка магазина на Shopify с кастомной темой и настройкой",
                    "Build a Shopify app with Node.js, Shopify Polaris, and REST API",
                    "Создание сайта на Tilda с кастомными Zero-блоками и анимацией",
                    "Добавить функционал на сайт Tilda: формы, CRM интеграция, анимация",
                    "Migrate existing WooCommerce store to Shopify with data transfer",
                    "Build full-stack web application with Laravel backend and Vue.js frontend",
                    "Автоматизация отчетов и уведомлений с интеграцией 1С и CRM",
                    "Complete full-stack application with Next.js frontend and Django backend",
                    "Полная разработка сайта от дизайна до деплоя на сервере",
                    "Build B2B SaaS platform with subscription management and analytics",
                    "Full-stack Django REST + React application with JWT authentication",
                    "Develop custom CRM with sales pipeline, contacts, and reporting",
                    "Design API-first web application with multiple client interfaces",
                    "Build MVP for startup: rapid development with iterative feedback",
                ],
                "budgets": [
                    ("USD", 2000, 6000),
                    ("RUB", 20000, 40000),
                    ("USD", 5000, 12000),
                    ("RUB", 8000, 15000),
                    ("RUB", 5000, 10000),
                    ("USD", 3000, 8000),
                    ("USD", 5000, 12000),
                    ("RUB", 15000, 30000),
                    ("USD", 8000, 20000),
                    ("RUB", 45000, 90000),
                    ("USD", 10000, 25000),
                    ("RUB", 60000, 120000),
                ],
                "proposals": (4, 22),
            },
        ]

        all_tasks = []
        for cat in category_templates:
            for i in range(TASKS_PER_GROUP):
                title = random.choice(cat["titles"])
                desc = random.choice(cat["descriptions"])
                currency, base_min, base_max = random.choice(cat["budgets"])
                if currency == "USD":
                    base_min = int(base_min * usd_to_rub)
                    base_max = int(base_max * usd_to_rub)
                    currency = "RUB"
                variance = random.uniform(0.85, 1.15)
                bmin = max(1, int(base_min * variance))
                bmax = max(bmin + 1, int(base_max * variance))
                bmin = round(bmin / 100) * 100
                bmax = round(bmax / 100) * 100

                source = random.choice(sources)
                task_id = f"{cat['prefix']}{i:03d}"

                search_queries = {
                    "WP": "wordpress+woocommerce",
                    "FB": "frontend+react+typescript",
                    "BE": "backend+api+python",
                    "TG": "telegram+bot",
                    "AI": "ai+chatbot+gpt+llm",
                    "SC": "web+scraping+automation",
                    "ML": "machine+learning+data+science",
                    "MO": "mobile+app+flutter+react+native",
                    "DO": "devops+docker+kubernetes",
                    "QA": "qa+testing+automation",
                    "SH": "fullstack+shopify+laravel",
                }
                search_q = search_queries.get(cat["prefix"], cat["slug"])

                platform_urls = {
                    "upwork": f"https://www.upwork.com/search/jobs/?q={search_q}",
                    "freelancer": f"https://www.freelancer.com/search/projects/?q={search_q}",
                    "guru": f"https://www.guru.com/search/?searchParams=%7B%22q%22%3A%22{search_q.replace('+', '%20')}%22%7D",
                    "fl": f"https://www.fl.ru/search/?q={search_q}",
                    "kwork": f"https://kwork.ru/search?query={search_q}",
                    "freelancehunt": f"https://freelancehunt.com/projects?q={search_q}",
                }

                task = {
                    "source": source,
                    "task_id": task_id,
                    "url": platform_urls.get(source),
                    "title": title,
                    "description": desc,
                    "budget_min": bmin,
                    "budget_max": bmax,
                    "currency": currency,
                    "posted_at": now - timedelta(hours=random.randint(1, 72)),
                    "proposals_count": random.randint(*cat["proposals"]),
                }
                all_tasks.append(task)

        self.tasks = all_tasks
        self.active_sources = sources
        logger.info(
            "Generated {} demo tasks across {} categories",
            len(self.tasks),
            len(category_templates),
        )

    async def run_with_demo(self) -> dict:
        logger.info("=" * 50)
        logger.info("Starting Freelance Market Analyzer (DEMO MODE)")
        logger.info("=" * 50)

        self.generate_demo_data()
        self.normalize_categories()
        self.extract_technologies()
        self.run_analytics()

        try:
            self.print_summary()
        except Exception as e:
            logger.error("Failed to print summary: {}", e)

        try:
            self.export_results()
        except Exception as e:
            logger.error("Failed to export results: {}", e)

        try:
            self.generate_charts()
        except Exception as e:
            logger.error("Failed to generate charts: {}", e)

        logger.info("=" * 50)
        logger.info("Demo analysis complete!")
        logger.info("=" * 50)

        return {"tasks": self.tasks, "analytics": self.analytics}

    def generate_charts(self) -> list[str]:
        charts = self.chart_generator.generate_all(self.tasks, self.analytics)
        logger.info("Generated {} charts", len(charts))
        return charts

    async def run(self) -> dict:
        logger.info("=" * 50)
        logger.info("Starting Freelance Market Analyzer")
        logger.info("=" * 50)

        try:
            db_ok = await check_db_connection()
            if db_ok:
                await init_db()
            else:
                logger.warning("Database not available, continuing without persistence")
        except Exception as e:
            logger.warning(
                "Database unavailable ({}), continuing without persistence", e
            )

        await self.collect_all()

        if not self.tasks:
            logger.warning("No tasks collected, nothing to analyze")
            return {"tasks": [], "analytics": {}}

        self.normalize_categories()
        self.extract_technologies()
        self.run_analytics()

        try:
            self.print_summary()
        except Exception as e:
            logger.error("Failed to print summary: {}", e)

        try:
            self.export_results()
        except Exception as e:
            logger.error("Failed to export results: {}", e)

        try:
            self.generate_charts()
        except Exception as e:
            logger.error("Failed to generate charts: {}", e)

        logger.info("=" * 50)
        logger.info("Analysis complete!")
        logger.info("=" * 50)

        return {
            "tasks": self.tasks,
            "analytics": self.analytics,
        }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Freelance Market Analyzer - Collect and analyze IT freelance orders"
    )
    parser.add_argument(
        "--scrapers",
        "-s",
        nargs="+",
        default=None,
        help="Scrapers to run (default: all). Options: upwork, freelancer, guru, fl, kwork, freelancehunt",
    )
    parser.add_argument(
        "--demo",
        "-d",
        action="store_true",
        help="Use demo data instead of live scraping from freelance platforms",
    )
    parser.add_argument(
        "--analyze-only",
        "-a",
        action="store_true",
        help="Skip scraping, only analyze existing data (not yet supported)",
    )
    parser.add_argument(
        "--export-only",
        "-e",
        action="store_true",
        help="Skip scraping and analysis, only generate export from existing data (not yet supported)",
    )

    args = parser.parse_args()

    analyzer = FreelanceMarketAnalyzer(scrapers_to_run=args.scrapers)

    try:
        if args.demo:
            asyncio.run(analyzer.run_with_demo())
        else:
            asyncio.run(analyzer.run())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.exception("Fatal error: {}", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
