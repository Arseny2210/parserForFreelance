# Freelance Market Analyzer

Production-ready система сбора и анализа IT-заказов с фриланс-бирж с полной аналитикой, Excel-отчётом и графиками.

По умолчанию работает в **демо-режиме** — генерирует 440+ реалистичных IT-задач, сгруппированных по 11 категориям, для демонстрации полной цепочки аналитики.

## Быстрый старт

```bash
# 1. Установить зависимости
pip install -r requirements.txt

# 2. Запустить в демо-режиме (по умолчанию)
python3 main.py

# Или с явным указанием демо-режима:
python3 main.py

# Живой сбор с фриланс-бирж (требуются Playwright браузеры):
python3 main.py --live
```

## Режимы работы

| Режим | Команда | Описание |
|-------|---------|----------|
| **Демо (по умолчанию)** | `python3 main.py` | Генерирует 440+ IT-задач в 11 категориях. Не требует БД, браузеров, интернета |
| Живой сбор | `python3 main.py --live` | Парсит Upwork, Freelancer, Guru, FL.ru, Kwork, Freelancehunt |

## Архитектура

```
project/
├── scrapers/           # Парсеры площадок (для --live режима)
│   ├── base.py         # BaseScraper (ABC)
│   ├── upwork.py
│   ├── freelancer.py
│   ├── guru.py
│   ├── fl.py
│   ├── kwork.py
│   └── freelancehunt.py
├── core/               # Ядро
│   ├── models.py       # SQLAlchemy models
│   ├── database.py     # Подключение к БД
│   ├── settings.py     # Pydantic settings
│   └── logger.py       # Loguru конфигурация
├── analytics/          # Аналитика
│   ├── categories.py   # NLP классификация (36 категорий)
│   ├── technologies.py # Извлечение 70+ технологий
│   ├── budgets.py      # Анализ бюджетов
│   ├── competition.py  # Анализ конкуренции
│   └── trends.py       # Анализ трендов
├── export/             # Экспорт
│   └── excel_export.py # Excel-отчёт (10 листов, русские названия)
├── reports/            # Визуализация
│   └── charts.py       # 8 matplotlib графиков
├── main.py             # Оркестратор
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

## Результаты

### Excel-отчёт (`exports/freelance_market_analysis_*.xlsx`)

| Лист | Содержимое |
|------|-----------|
| Общая аналитика рынка | Сводка: статистика, распределение категорий, бюджеты, конкуренция, выводы |
| IT-задачи | Все задачи, отфильтрованные по IT, сгруппированные по категориям |
| Топ категорий | Распределение по категориям |
| Топ технологий | Топ технологий |
| Средний бюджет | Средние бюджеты по категориям |
| Медианный бюджет | Медианные бюджеты |
| Конкуренция | Конкуренция (среднее число откликов) |
| Быстрорастущие категории | Самые быстрорастущие категории |
| Самые дорогие категории | Самые дорогие категории |
| Примеры задач | Примеры задач по категориям |

### Графики (`reports/charts/*.png`)

- `category_distribution.png` — распределение категорий
- `budgets_by_category.png` — бюджеты по категориям
- `tasks_by_source.png` — количество задач по площадкам
- `publication_timeline.png` — динамика публикаций
- `technology_distribution.png` — распределение технологий
- `budget_histogram.png` — гистограмма бюджетов
- `competition_heatmap.png` — конкуренция vs бюджет
- `category_vs_budget.png` — категории vs бюджет

## Категории (NLP-классификация)

Система автоматически классифицирует задачи в 36 категорий на основе названия и описания с использованием регулярных выражений и ключевых слов (включая русские):

WordPress, Tilda, Shopify, Frontend, React, Next.js, Backend, FastAPI, Django, Laravel, Fullstack, Telegram Bots, Discord Bots, AI Chatbots, AI Agents, RAG, OpenAI Integration, Claude Integration, Web Scraping, Parsing, Automation, n8n, Make, Zapier, Mobile Apps, Flutter, React Native, Android, iOS, DevOps, Docker, Kubernetes, QA, Data Analytics, Power BI, SQL, Machine Learning, Computer Vision, OTHER.

## Разработка

```bash
# Установка зависимостей для разработки
pip install -r requirements-dev.txt

# Линтинг
ruff check .

# Type checking
mypy .

# Тесты
pytest -v --tb=short

# Полная проверка
ruff check . && mypy . && pytest -v --tb=short
```

## Дополнительно

- **Демо-данные** используют seed 42 для воспроизводимости
- **Excel-отчёт** содержит фильтрацию только IT-задач, русские названия листов и колонок, цветовое кодирование
- **8 графиков** сохраняются в `reports/charts/`
- **Graceful degradation** — система работает без БД (используется только для `--live` режима с PostgreSQL)

## Переменные окружения

| Переменная | Значение по умолчанию | Описание |
|-----------|----------------------|----------|
| DATABASE_URL | postgresql+asyncpg://postgres:postgres@localhost:5432/freelance_market | Async connection |
| DATABASE_URL_SYNC | postgresql://postgres:postgres@localhost:5432/freelance_market | Sync connection |
| LOG_LEVEL | DEBUG | Уровень логирования |
| PROXY_ENABLED | false | Включить прокси |
| PROXY_URL | - | URL прокси |
| REQUEST_TIMEOUT | 30 | Таймаут запроса (сек) |
| MAX_RETRIES | 5 | Максимум повторов |
| THROTTLE_DELAY | 1.0 | Задержка между запросами |
