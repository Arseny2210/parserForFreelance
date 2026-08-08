# Freelance Market Analyzer

Сбор и анализ IT-заказов с фриланс-бирж (Kwork, FL.ru). Современный веб-интерфейс
на **React + FastAPI**, карточки заказов с приоритетом Kwork, премиальный тёмный дизайн,
гибкие фильтры, Excel-отчёты и графики.

---

## 🚀 Быстрый старт (React + FastAPI)

### Вариант 1 — одним скриптом (production)

```bash
./start.sh            # собирает frontend и поднимает сервер
# → http://localhost:8000
```

### Вариант 2 — разработка с hot-reload

```bash
./dev.sh              # backend :8000 + vite :5173
# → фронт http://localhost:5173, API http://localhost:8000/api
```

### Вручную

```bash
# Python
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt fastapi

# Frontend
cd frontend && npm install && npm run build && cd ..

# Сервер (отдаёт и API, и собранный фронт)
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

---

## ✨ Что умеет веб-интерфейс

- **Карточки заказов** — заголовок, описание, бюджет, категория, технологии, отклики, дата
- **Приоритет Kwork** — заказы с Kwork всегда сверху, помечены бейджем «★ Приоритет»
- **Все возможные заказы** — по умолчанию показываются все площадки сразу
- **Фильтры:**
  - Источники (чекбоксы с приоритетом Kwork)
  - Только IT / Design
  - IT-категории (группированные: Frontend, Backend, AI/ML, Боты и т.д.)
  - Бюджет «от — до» (двойной слайдер)
  - Поиск по названию (с debounce)
- **Метрики** — всего заказов, IT/Design, категории, технологии, средний бюджет
- **Сбор данных** — кнопка «Собрать заказы» запускает парсинг с прогресс-баром и статусом
- **Тёмная премиальная тема** — glassmorphism-карточки, градиенты, анимации, адаптив

---

## 🐍 API (FastAPI)

| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| `GET` | `/api/health` | Проверка сервиса |
| `GET` | `/api/status` | Статус сбора, кол-во задач, время обновления |
| `GET` | `/api/tasks` | Заказы с фильтрами и приоритетом Kwork |
| `GET` | `/api/filters` | Доступные источники, категории, диапазон бюджета |
| `GET` | `/api/analytics` | Аналитика (категории, технологии, бюджеты, конкуренция) |
| `POST` | `/api/collect` | Запустить сбор данных `{"sources": ["kwork","fl"]}` |

Пример фильтрации задач:

```
GET /api/tasks?sources=kwork,fl&categories=Frontend,React&budget_min=10000&budget_max=200000&q=сайт&it_only=true
```

---

## ⚙️ CLI (без интерфейса)

```bash
python3 main.py --demo            # демо-данные (440+ задач)
python3 main.py --scrapers fl kwork   # живой сбор
```

---

## 📦 Архитектура

```
project/
├── backend/                  # FastAPI API
│   ├── main.py               # эндпоинты + раздача фронта
│   └── service.py            # оркестрация сбора, Kwork-приоритет, кеш
├── frontend/                 # React + Vite
│   └── src/
│       ├── App.jsx           # состояние, метрики, сетка
│       ├── api.js            # клиент API
│       └── components/
│           ├── Sidebar.jsx   # источники, сбор, фильтры, поиск
│           └── TaskCard.jsx  # карточка заказа с Kwork-бейджем
├── scrapers/                 # парсеры (Kwork, FL.ru и др.)
├── analytics/                # NLP-классификация (35+ категорий)
├── export/                   # Excel-отчёты
├── reports/charts.py         # 8 matplotlib-графиков
├── streamlit_app.py          # (legacy) старый интерфейс
└── main.py                   # CLI-оркестратор
```

---

## 🧪 Тесты

```bash
python3 -m pytest tests/ -v
```

---

## 🚢 Деплой (Render / Docker)

`Dockerfile` и `docker-compose.yml` уже настроены. В контейнере запускается
`start.sh` → собирает frontend → поднимает FastAPI, который отдаёт и API, и SPA
на одном порту. Никакого отдельного веб-сервера не нужно.
