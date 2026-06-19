# Freelance Market Analyzer

Сбор и анализ IT-заказов с фриланс-бирж. Веб-интерфейс (Streamlit), Excel-отчёты, графики, NLP-классификация по 35+ категориям.

## Быстрый старт

```bash
pip install -r requirements.txt
playwright install chromium
streamlit run streamlit_app.py
```

Откройте `http://localhost:8501` в браузере.

## Режимы работы

### Веб-интерфейс (Streamlit) — основной

```bash
streamlit run streamlit_app.py
```

- Выбор источников: Kwork, FL.ru (чекбоксы в сайдбаре)
- Прогресс-бар с детальными шагами и статусами
- Фильтры: IT-категории (групповые чекбоксы), источник, диапазон бюджета
- Поиск по названию задачи во вкладке «📋 Задачи»
- Вкладки: «📈 Обзор» (метрики + графики), «📋 Задачи» (таблица), «📊 Графики» (PNG), «⬇️ Экспорт» (Excel)
- Кнопка «✕ Сбросить» для очистки данных

### CLI (живой сбор)

```bash
python3 main.py --scrapers fl kwork
```

### CLI (демо-данные)

```bash
python3 main.py --demo
```

Генерирует 440+ реалистичных IT-задач в 35 категориях без парсинга.

## Фильтры

### В сайдбаре

| Фильтр | Описание |
|--------|----------|
| **Только IT / Design** | Показывать только IT-задачи |
| **IT-категории** | 11 групп: Frontend/UI, Backend, CMS, Боты, AI/ML, Парсинг/Автоматизация, Mobile, DevOps/QA, Data, Design/Marketing, Fullstack |
| **Выбрать все / Снять все** | Быстрое управление IT-категориями |
| **Источник** | Multiselect: Kwork, FL.ru |
| **Бюджет от — до** | Слайдер диапазона |

### Во вкладке «📋 Задачи»

| Фильтр | Описание |
|--------|----------|
| **🔍 Поиск по названию** | Фильтрация по тексту в названии задачи |

## Архитектура

```
project/
├── streamlit_app.py          # Веб-интерфейс (Streamlit)
├── main.py                   # Оркестратор FreelanceMarketAnalyzer
├── scrapers/                 # Парсеры бирж
│   ├── base.py               # BaseScraper (ABC)
│   ├── kwork.py              # Kwork (Playwright, stealth)
│   └── fl.py                 # FL.ru (Playwright, headless=new)
├── analytics/                # Аналитика
│   ├── categories.py         # NLP-классификация (35+ категорий, regex)
│   ├── technologies.py       # Извлечение 70+ технологий
│   ├── budgets.py            # Анализ бюджетов
│   ├── competition.py        # Анализ конкуренции
│   └── trends.py             # Анализ трендов
├── export/
│   └── excel_export.py       # Excel-отчёт (10 листов, русские названия)
├── reports/
│   └── charts.py             # 8 matplotlib графиков
├── core/
│   ├── settings.py           # Pydantic-конфигурация
│   └── logger.py             # Loguru
├── requirements.txt
├── AGENTS.md                 # Шпаргалка команд
└── tests/                    # Pytest тесты
```

## Результаты

### Excel-отчёт (`exports/freelance_market_analysis_*.xlsx`)

| Лист | Содержимое |
|------|-----------|
| Общая аналитика рынка | Сводка: статистика, бюджеты, конкуренция, выводы |
| IT-задачи | Все IT-задачи, сгруппированные по категориям |
| Топ категорий | Распределение по категориям |
| Топ технологий | Топ технологий |
| Средний бюджет | Средние бюджеты по категориям |
| Медианный бюджет | Медианные бюджеты |
| Конкуренция | Среднее число откликов |
| Быстрорастущие категории | Самые быстрорастущие категории |
| Самые дорогие категории | Самые дорогие категории |
| Примеры задач | Примеры задач по категориям |

### Графики (`reports/charts/*.png`)

| Файл | Описание |
|------|----------|
| `category_distribution.png` | Распределение категорий |
| `budgets_by_category.png` | Бюджеты по категориям |
| `tasks_by_source.png` | Задачи по площадкам |
| `publication_timeline.png` | Динамика публикаций |
| `technology_distribution.png` | Распределение технологий |
| `budget_histogram.png` | Гистограмма бюджетов |
| `competition_heatmap.png` | Конкуренция vs бюджет |
| `category_vs_budget.png` | Категории vs бюджет |

## Категории (NLP-классификация)

Система автоматически классифицирует задачи в 35+ категорий на основе названия и описания (регулярные выражения, русские и английские ключевые слова):

**Frontend:** Frontend, React, Next.js
**Backend:** Backend, FastAPI, Django, Laravel, C# / .NET
**CMS:** WordPress, Tilda, Shopify
**Боты:** Telegram Bots, Discord Bots
**AI/ML:** AI Chatbots, AI Agents, RAG, OpenAI Integration, Claude Integration, Machine Learning, Computer Vision
**Парсинг/Автоматизация:** Web Scraping, Parsing, Automation, n8n, Make, Zapier
**Mobile:** Mobile Apps, Flutter, React Native, Android, iOS
**DevOps/QA:** DevOps, Docker, Kubernetes, QA
**Data:** Data Analytics, Power BI, SQL
**Design/Marketing:** Design, Marketing
**Прочее:** Fullstack, OTHER (не IT)

## Установка

```bash
# Зависимости
pip install -r requirements.txt

# Браузер для Playwright
playwright install chromium
```

## Тесты

```bash
python3 -m pytest tests/ -v
```

## Переменные окружения (`.env`)

| Переменная | По умолчанию | Описание |
|-----------|-------------|----------|
| `LOG_LEVEL` | `DEBUG` | Уровень логирования |
| `PROXY_ENABLED` | `false` | Включить прокси |
| `PROXY_URL` | — | URL прокси |
| `REQUEST_TIMEOUT` | `30` | Таймаут запроса (сек) |
| `MAX_RETRIES` | `5` | Максимум повторов |
| `THROTTLE_DELAY` | `1.0` | Задержка между запросами |

## Технологии

- **Streamlit** — веб-интерфейс
- **Playwright** — headless Chrome для парсинга
- **Pandas** — обработка данных
- **OpenPyXL** — Excel-отчёты
- **Matplotlib + Seaborn** — графики
- **Pydantic** — конфигурация
- **Loguru** — логирование
- **Pytest** — тесты
