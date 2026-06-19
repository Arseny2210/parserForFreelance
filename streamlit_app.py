import sys
import asyncio
import os
from pathlib import Path
from datetime import datetime
from collections import Counter

import streamlit as st
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))

from main import FreelanceMarketAnalyzer
from export.excel_export import RUSSIAN_CATEGORIES, IT_CATEGORIES

st.set_page_config(page_title="Freelance Market Analyzer", layout="wide")

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

AVAILABLE_SOURCES = {"kwork": "Kwork", "fl": "FL.ru"}

for key in ("tasks", "stats", "last_run", "latest_excel"):
    if key not in st.session_state:
        st.session_state[key] = None
if "running" not in st.session_state:
    st.session_state.running = False
if "filters" not in st.session_state:
    st.session_state.filters = {
        "it_only": True,
        "selected_it_cats": set(IT_CATEGORIES),
        "sources": set(),
        "budget_min": 0,
        "budget_max": 5_000_000,
    }


def find_latest_excel():
    p = Path("exports")
    if not p.exists():
        return None
    files = sorted(p.glob("*.xlsx"), key=os.path.getmtime)
    return files[-1] if files else None


def reset_state():
    for k in ("tasks", "stats", "last_run", "latest_excel"):
        st.session_state[k] = None
    st.session_state.running = False


def run_async(coro_or_result):
    if not asyncio.iscoroutine(coro_or_result):
        return coro_or_result
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro_or_result)
    finally:
        loop.close()


def apply_filters(tasks: list[dict], filters: dict) -> list[dict]:
    filtered = []
    f = filters
    for t in tasks:
        cat = t.get("normalized_category", "OTHER")
        src = t.get("source", "")
        budget = t.get("budget_min") or 0

        if f["it_only"] and cat not in IT_CATEGORIES:
            continue
        if f["it_only"] and f["selected_it_cats"] and cat not in f["selected_it_cats"]:
            continue
        if f["sources"] and src not in f["sources"]:
            continue
        if budget < f["budget_min"] or budget > f["budget_max"]:
            continue

        filtered.append(t)
    return filtered


# ── Sidebar ──────────────────────────────────────────────────────
with st.sidebar:
    disabled = st.session_state.running
    has_data = st.session_state.tasks is not None

    st.header("📦 Сбор данных")

    selected = []
    for key, label in AVAILABLE_SOURCES.items():
        if st.checkbox(label, value=True, key=f"src_{key}", disabled=disabled):
            selected.append(key)

    if st.button(
        "🚀 Собрать данные", type="primary", use_container_width=True, disabled=disabled
    ):
        if not selected:
            st.warning("Выберите хотя бы один источник")
        else:
            st.session_state.running = True
            st.session_state.tasks = None
            st.session_state.stats = None
            st.session_state.run_sources = selected
            st.rerun()

    if st.session_state.running:
        st.button("⏳ Идёт сбор...", disabled=True, use_container_width=True)
    elif has_data:
        if st.button("✕ Сбросить", use_container_width=True):
            reset_state()
            st.rerun()

    if has_data:
        st.divider()
        st.header("🔍 Фильтры")
        f = st.session_state.filters

        it_only = st.checkbox("Только IT / Design", value=f["it_only"], key="f_it_only")
        f["it_only"] = it_only

        if it_only:
            st.caption("IT-категории")
            all_selected = True
            cats_in_data = {
                t.get("normalized_category")
                for t in st.session_state.tasks
                if t.get("normalized_category") in IT_CATEGORIES
            }
            for group, members in IT_CATEGORY_GROUPS.items():
                present = [c for c in members if c in cats_in_data]
                if not present:
                    continue
                sel = all(c in f["selected_it_cats"] for c in present)
                group_val = st.checkbox(
                    f"{group} ({', '.join(RUSSIAN_CATEGORIES[c] for c in present)})",
                    value=sel,
                    key=f"fg_{group}",
                )
                if group_val:
                    for c in present:
                        f["selected_it_cats"].add(c)
                else:
                    all_selected = False
                    for c in present:
                        f["selected_it_cats"].discard(c)

            select_all = st.checkbox(
                "Выбрать все / Снять все", value=all_selected, key="f_cat_all"
            )
            if select_all and not all_selected:
                f["selected_it_cats"] = set(IT_CATEGORIES)
            elif not select_all and all_selected:
                f["selected_it_cats"] = set()

        sources_in_data = sorted({t.get("source", "") for t in st.session_state.tasks})
        sel_sources = [
            s for s in sources_in_data if s in f["sources"]
        ] or sources_in_data
        src_filter = st.multiselect(
            "Источник",
            sources_in_data,
            default=sel_sources,
            key="f_sources",
        )
        f["sources"] = set(src_filter)

        all_budgets = [t.get("budget_min") or 0 for t in st.session_state.tasks]
        if not all_budgets:
            all_budgets = [0, 500_000]
        bmin, bmax = min(all_budgets), max(all_budgets)
        if bmin == bmax:
            bmax = bmin + 100_000
        b_range = st.slider(
            "Бюджет от — до (₽)",
            min_value=int(bmin),
            max_value=int(bmax),
            value=(int(f["budget_min"]), int(f["budget_max"])),
            key="f_budget",
        )
        f["budget_min"], f["budget_max"] = b_range

    if st.session_state.last_run:
        st.divider()
        dt = st.session_state.last_run
        st.caption(f"Последний сбор: {dt.strftime('%d.%m.%Y %H:%M')}")
        n = len(st.session_state.tasks or [])
        st.caption(f"Всего задач: {n}")

    if has_data:
        st.divider()
        st.caption("✅ Данные загружены")


# ── Collection phase ──────────────────────────────────────────────
if st.session_state.running:
    sources = st.session_state.get("run_sources", [])

    bar = st.progress(0, text="🚀 Подготовка...")
    status = st.status("Запуск сбора данных...", expanded=True)

    try:
        a = FreelanceMarketAnalyzer(scrapers_to_run=sources)

        total_steps = len(sources) + 5
        step = 0

        for src in sources:
            step += 1
            pct = int(step / total_steps * 60)
            label_text = f"📥 {AVAILABLE_SOURCES.get(src, src)}..."
            bar.progress(pct, text=label_text)
            status.update(label=label_text, state="running")
            collected = run_async(a.collect_source(src))
            status.write(
                f"✓ {len(collected)} задач с {AVAILABLE_SOURCES.get(src, src)}"
            )

            step += 1
            bar.progress(62, text="🏷️ Классификация...")
            status.update(label="Классификация категорий...", state="running")
            a.normalize_categories()

            step += 1
            bar.progress(70, text="🔧 Технологии...")
            status.update(label="Извлечение технологий...", state="running")
            a.extract_technologies()

            step += 1
            bar.progress(78, text="📊 Анализ...")
            status.update(label="Анализ данных...", state="running")
            a.run_analytics()

            step += 1
            bar.progress(86, text="📝 Экспорт в Excel...")
            status.update(label="Экспорт...", state="running")
            a.export_results()

            step += 1
            bar.progress(94, text="📈 Графики...")
            status.update(label="Генерация графиков...", state="running")
            a.generate_charts()

        bar.progress(100, text=f"✅ Готово — {len(a.tasks)} задач")
        status.update(
            label=f"✅ Собрано {len(a.tasks)} задач",
            state="complete",
            expanded=False,
        )

        st.session_state.tasks = a.tasks
        st.session_state.stats = a.analytics
        st.session_state.last_run = datetime.now()
        st.session_state.latest_excel = find_latest_excel()

        st.session_state.running = False
        st.rerun()

    except Exception as e:
        import traceback

        bar.empty()
        status.update(label=f"❌ Ошибка: {e}", state="error")
        st.code(traceback.format_exc())

    st.stop()


# ── Main content ─────────────────────────────────────────────────
if st.session_state.tasks is None:
    st.info("Нажмите **🚀 Собрать данные** в боковой панели.")
    st.stop()

tasks = st.session_state.tasks
stats = st.session_state.stats
filters = st.session_state.filters

filtered_tasks = apply_filters(tasks, filters)
it_tasks = [t for t in tasks if t.get("normalized_category", "OTHER") in IT_CATEGORIES]

tab_overview, tab_tasks_tab, tab_charts, tab_excel = st.tabs(
    ["📈 Обзор", "📋 Задачи", "📊 Графики", "⬇️ Экспорт"]
)

# ── Tab: Overview ─────────────────────────────────────────────────
with tab_overview:
    cols = st.columns(5)
    cols[0].metric("Всего задач", len(tasks))
    cols[1].metric(
        "IT / Design",
        len(it_tasks),
        f"{len(it_tasks) / max(len(tasks), 1) * 100:.0f}%",
    )
    cols[2].metric("Не IT", len(tasks) - len(it_tasks))
    cols[3].metric("Категорий", len(stats.get("category_counts", {})))
    cols[4].metric("Технологий", len(stats.get("technology_counts", {})))

    cat_counts = stats.get("category_counts", {})
    it_counts = {k: v for k, v in cat_counts.items() if k in IT_CATEGORIES}

    col_left, col_right = st.columns(2)
    with col_left:
        if it_counts:
            st.subheader("Распределение IT-категорий")
            df = pd.DataFrame(
                {
                    "Категория": [
                        RUSSIAN_CATEGORIES.get(k, k) for k in it_counts.keys()
                    ],
                    "Задач": list(it_counts.values()),
                }
            ).sort_values("Задач", ascending=False)
            st.bar_chart(df.set_index("Категория"))

    with col_right:
        source_counts = Counter(t.get("source", "?") for t in tasks)
        if source_counts:
            st.subheader("По источникам")
            df_src = pd.DataFrame(
                {
                    "Источник": list(source_counts.keys()),
                    "Задач": list(source_counts.values()),
                }
            ).sort_values("Задач", ascending=False)
            st.bar_chart(df_src.set_index("Источник"))

    ba = stats.get("budget_analysis", {})
    if ba:
        st.subheader("Бюджет")
        bc = st.columns(4)
        bc[0].metric("Средний", f"₽{(ba.get('average_budget_min') or 0):,.0f}")
        bc[1].metric("Медиана", f"₽{(ba.get('median_budget_min') or 0):,.0f}")
        bc[2].metric("Мин", f"₽{(ba.get('min_budget') or 0):,.0f}")
        bc[3].metric("Макс", f"₽{(ba.get('max_budget') or 0):,.0f}")

    ca = stats.get("competition_analysis", {})
    if ca:
        st.subheader("Конкуренция")
        st.metric(
            "Среднее число откликов", f"{ca.get('overall_average_proposals', 0):.1f}"
        )

    st.caption(
        f"Показано: {len(filtered_tasks)} задач из {len(tasks)} (после фильтров: {len(apply_filters(tasks, filters))})"
    )

# ── Tab: Tasks ────────────────────────────────────────────────────
with tab_tasks_tab:
    search = st.text_input(
        "🔍 Поиск по названию",
        value="",
        placeholder="Введите часть названия задачи...",
    )
    if search:
        filtered_tasks = [
            t for t in filtered_tasks if search.lower() in t.get("title", "").lower()
        ]

    rows = []
    for t in filtered_tasks:
        bmin = t.get("budget_min")
        bmax = t.get("budget_max")
        if bmin and bmax and bmin != bmax:
            budget_str = f"{bmin:,.0f} — {bmax:,.0f} ₽"
        elif bmin:
            budget_str = f"от {bmin:,.0f} ₽"
        elif bmax:
            budget_str = f"до {bmax:,.0f} ₽"
        else:
            budget_str = "дог."

        posted = t.get("posted_at")
        if isinstance(posted, datetime):
            posted_str = posted.strftime("%d.%m.%Y")
        else:
            posted_str = ""
        rows.append(
            {
                "Название": t.get("title", ""),
                "Категория": RUSSIAN_CATEGORIES.get(
                    t.get("normalized_category", "OTHER"), "OTHER"
                ),
                "Бюджет": budget_str,
                "Источник": t.get("source", ""),
                "Дата": posted_str,
                "Технологии": ", ".join(t.get("technologies", []) or [])[:80],
                "Ссылка": t.get("url", ""),
            }
        )

    st.caption(f"Показано: {len(rows)} из {len(tasks)} задач")
    if rows:
        st.dataframe(
            pd.DataFrame(rows),
            column_config={
                "Ссылка": st.column_config.LinkColumn(display_text="Открыть"),
            },
            use_container_width=True,
            hide_index=True,
            height=600,
        )

# ── Tab: Charts ───────────────────────────────────────────────────
with tab_charts:
    d = Path("reports/charts")
    if d.exists():
        titles = {
            "category_distribution": "Категории",
            "budgets_by_category": "Бюджеты",
            "tasks_by_source": "Источники",
            "publication_timeline": "Публикации",
            "technology_distribution": "Технологии",
            "budget_histogram": "Бюджеты",
            "competition_heatmap": "Конкуренция",
            "category_vs_budget": "Категория vs Бюджет",
        }
        files = sorted(d.glob("*.png"), key=os.path.getmtime)
        if files:
            cols = st.columns(2)
            for i, f in enumerate(files):
                with cols[i % 2]:
                    st.image(
                        str(f),
                        caption=titles.get(f.stem, f.stem),
                        use_container_width=True,
                    )

# ── Tab: Export ───────────────────────────────────────────────────
with tab_excel:
    p = st.session_state.latest_excel or find_latest_excel()
    if p and Path(p).exists():
        with open(p, "rb") as f:
            st.download_button(
                "📥 Скачать Excel",
                f,
                file_name=os.path.basename(p),
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
                use_container_width=True,
            )
        st.caption(f"Файл: {os.path.basename(p)}")
    else:
        st.info("Excel-файл не найден")
