import sys
import json
import asyncio
import os
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter

import streamlit as st
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))

from main import FreelanceMarketAnalyzer
from export.excel_export import RUSSIAN_CATEGORIES, IT_CATEGORIES

st.set_page_config(page_title="Freelance Market Analyzer", layout="wide")

st.markdown(
    """
<style>
[data-testid="stSidebar"] { min-width: 320px; max-width: 320px; }
.stProgress > div > div > div > div { background-color: #00cc66; }
div[data-testid="stMetric"] { background: #f0f2f6; border-radius: 8px; padding: 8px; }
div[data-testid="stMetric"] > div:first-child { font-size: 14px; color: #555; }
div[data-testid="stMetric"] > div:nth-child(2) { font-size: 24px; font-weight: 700; }
.tasks-header { display: flex; justify-content: space-between; align-items: center; }
.cache-badge { font-size: 12px; color: #888; padding: 4px 10px; border-radius: 12px; background: #e8f0fe; }
</style>
""",
    unsafe_allow_html=True,
)

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
CACHE_FILE = Path("exports/cache.json")


def save_cache(tasks: list[dict], stats: dict):
    cache = {
        "collected_at": datetime.now().isoformat(),
        "tasks": tasks,
        "stats": stats,
    }
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(json.dumps(cache, default=str, ensure_ascii=False, indent=2))


def load_cache() -> dict | None:
    if not CACHE_FILE.exists():
        return None
    try:
        data = json.loads(CACHE_FILE.read_text())
        for t in data.get("tasks", []):
            if isinstance(t.get("posted_at"), str):
                t["posted_at"] = datetime.fromisoformat(t["posted_at"])
        return data
    except Exception:
        return None


for key in ("tasks", "stats", "last_run", "latest_excel", "debug_log"):
    if key not in st.session_state:
        st.session_state[key] = None
if "running" not in st.session_state:
    st.session_state.running = False


def reset_filters():
    st.session_state["filters"] = {
        "it_only": True,
        "selected_it_cats": set(IT_CATEGORIES),
        "sources": set(),
        "budget_min": None,
        "budget_max": None,
    }


if "filters" not in st.session_state:
    reset_filters()


def reset_state():
    for k in ("tasks", "stats", "last_run", "latest_excel", "debug_log"):
        st.session_state[k] = None
    st.session_state.running = False
    reset_filters()


def clamp(val, lo, hi):
    return max(lo, min(val, hi))


def run_async(coro_or_result):
    if not asyncio.iscoroutine(coro_or_result):
        return coro_or_result
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro_or_result)
    finally:
        loop.close()


def find_latest_excel():
    p = Path("exports")
    if not p.exists():
        return None
    files = sorted(p.glob("*.xlsx"), key=os.path.getmtime)
    return files[-1] if files else None


def apply_filters(tasks: list[dict], filters: dict) -> list[dict]:
    filtered = []
    f = filters
    for t in tasks:
        cat = t.get("normalized_category", "OTHER")
        src = t.get("source", "")

        if f["it_only"] and cat not in IT_CATEGORIES:
            continue
        if f["it_only"] and f["selected_it_cats"] and cat not in f["selected_it_cats"]:
            continue
        if f["sources"] and src not in f["sources"]:
            continue

        bmin = f.get("budget_min")
        bmax = f.get("budget_max")
        if bmin is not None or bmax is not None:
            t_min = t.get("budget_min")
            t_max = t.get("budget_max")
            if t_min is None and t_max is None:
                continue
            t_lo = t_min if t_min is not None else t_max
            t_hi = t_max if t_max is not None else t_min
            if bmin is not None and t_hi < bmin:
                continue
            if bmax is not None and t_lo > bmax:
                continue

        filtered.append(t)
    return filtered


# ── Auto-load cache ──────────────────────────────────────────────
if st.session_state.tasks is None and not st.session_state.running:
    cached = load_cache()
    if cached:
        st.session_state.tasks = cached["tasks"]
        st.session_state.stats = cached["stats"]
        st.session_state.last_run = datetime.fromisoformat(cached["collected_at"])


# ── Sidebar ──────────────────────────────────────────────────────
with st.sidebar:
    disabled = st.session_state.running
    has_data = st.session_state.tasks is not None

    st.header("📦 Сбор данных")

    selected = []
    for key, label in AVAILABLE_SOURCES.items():
        if st.checkbox(label, value=True, key=f"src_{key}", disabled=disabled):
            selected.append(key)

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        collect_btn = st.button(
            "🚀 Собрать", type="primary", use_container_width=True, disabled=disabled
        )
    with col2:
        if has_data and not disabled:
            if st.button("✕ Сбросить", use_container_width=True):
                reset_state()
                st.rerun()

    if collect_btn:
        if not selected:
            st.warning("Выберите хотя бы один источник")
        else:
            st.session_state.running = True
            st.session_state.tasks = None
            st.session_state.stats = None
            st.session_state.debug_log = []
            st.session_state.run_sources = selected
            reset_filters()
            st.rerun()

    if st.session_state.running:
        st.button("⏳ Идёт сбор...", disabled=True, use_container_width=True)

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

        all_budgets = [
            t.get("budget_min") or t.get("budget_max") or 0
            for t in st.session_state.tasks
        ]
        if not all_budgets:
            all_budgets = [0, 500_000]
        bmin, bmax = min(all_budgets), max(all_budgets)
        if bmin == bmax:
            bmax = bmin + 100_000
        default_min = f["budget_min"] if f["budget_min"] is not None else int(bmin)
        default_max = f["budget_max"] if f["budget_max"] is not None else int(bmax)
        b_range = st.slider(
            "Бюджет от — до (₽)",
            min_value=int(bmin),
            max_value=int(bmax),
            value=(
                int(clamp(default_min, bmin, bmax)),
                int(clamp(default_max, bmin, bmax)),
            ),
            key="f_budget",
        )
        f["budget_min"], f["budget_max"] = b_range

    if st.session_state.last_run:
        st.divider()
        dt = st.session_state.last_run
        n = len(st.session_state.tasks or [])
        age = datetime.now() - dt
        if age.total_seconds() < 60:
            age_str = "только что"
        elif age.total_seconds() < 3600:
            age_str = f"{int(age.total_seconds() // 60)} мин назад"
        else:
            age_str = f"{int(age.total_seconds() // 3600)} ч назад"
        st.caption(f"📅 {dt.strftime('%d.%m.%Y %H:%M')} · {age_str}")
        st.caption(f"📋 {n} задач")

    if has_data:
        st.divider()
        st.caption("✅ Данные загружены")


# ── Collection phase ──────────────────────────────────────────────
if st.session_state.running:
    sources = st.session_state.get("run_sources", [])
    debug = st.session_state.debug_log or []

    bar = st.progress(0, text="🚀 Подготовка...")
    status = st.status("Запуск сбора данных...", expanded=True)

    try:
        a = FreelanceMarketAnalyzer(scrapers_to_run=sources)

        total_steps = 0
        step = 0
        source_errors = []

        if sources:
            total_steps = len(sources) + 5

        for src in sources:
            step += 1
            pct = int(step / total_steps * 60)
            label_text = f"📥 {AVAILABLE_SOURCES.get(src, src)}..."
            bar.progress(pct, text=label_text)
            status.update(label=label_text, state="running")
            try:
                collected = run_async(a.collect_source(src))
                msg = f"✓ {len(collected)} задач с {AVAILABLE_SOURCES.get(src, src)}"
                status.write(msg)
                debug.append(f"[{src}] collected {len(collected)} tasks")
            except Exception as e:
                import traceback

                source_errors.append(src)
                tb = traceback.format_exc()
                status.write(f"❌ {AVAILABLE_SOURCES.get(src, src)}: {e}")
                debug.append(f"[{src}] ERROR: {e}")
                debug.append(tb)

        if source_errors:
            failed = ", ".join(AVAILABLE_SOURCES.get(s, s) for s in source_errors)
            status.write(f"⚠️ Ошибки сбора: {failed}")

        if not a.tasks:
            status.write("⚠️ Парсер не нашёл задач.")
            bar.progress(100, text="⚠️ Нет данных")
            status.update(label="⚠️ Сбор завершён, задач нет", state="error")
            st.session_state.debug_log = debug
            st.session_state.tasks = []
            st.session_state.stats = {}
            st.session_state.last_run = datetime.now()
            st.session_state.running = False
            save_cache([], {})
            st.rerun()

        step += 1
        pct = min(step / max(total_steps, 1) * 100, 95)
        bar.progress(int(pct), text="🏷️ Классификация...")
        status.update(label="Классификация категорий...", state="running")
        a.normalize_categories()
        debug.append(f"[analytics] normalized {len(a.tasks)} tasks")

        step += 1
        pct = min(step / max(total_steps, 1) * 100, 95)
        bar.progress(int(pct), text="🔧 Технологии...")
        status.update(label="Извлечение технологий...", state="running")
        a.extract_technologies()

        step += 1
        pct = min(step / max(total_steps, 1) * 100, 95)
        bar.progress(int(pct), text="📊 Анализ...")
        status.update(label="Анализ данных...", state="running")
        a.run_analytics()

        step += 1
        pct = min(step / max(total_steps, 1) * 100, 95)
        bar.progress(int(pct), text="📝 Экспорт...")
        status.update(label="Экспорт...", state="running")
        a.export_results()

        step += 1
        bar.progress(95, text="📈 Графики...")
        status.update(label="Генерация графиков...", state="running")
        a.generate_charts()

        bar.progress(100, text=f"✅ Готово — {len(a.tasks)} задач")
        status.update(
            label=f"✅ Собрано {len(a.tasks)} задач",
            state="complete",
            expanded=False,
        )

        st.session_state.debug_log = debug
        st.session_state.tasks = a.tasks
        st.session_state.stats = a.analytics
        st.session_state.last_run = datetime.now()
        st.session_state.latest_excel = find_latest_excel()
        st.session_state.running = False

        save_cache(a.tasks, a.analytics)
        st.rerun()

    except Exception as e:
        import traceback

        debug.append(f"[fatal] {e}")
        debug.append(traceback.format_exc())
        st.session_state.debug_log = debug
        bar.empty()
        status.update(label=f"❌ Ошибка: {e}", state="error")
        st.code(traceback.format_exc())

    st.stop()


# ── Main content ─────────────────────────────────────────────────
if st.session_state.tasks is None:
    cached = load_cache()
    if cached:
        st.session_state.tasks = cached["tasks"]
        st.session_state.stats = cached["stats"]
        st.session_state.last_run = datetime.fromisoformat(cached["collected_at"])
        st.rerun()
    else:
        st.info("👋 Нажмите **🚀 Собрать** в боковой панели, чтобы начать.")
        st.stop()

tasks = st.session_state.tasks
stats = st.session_state.stats
filters = st.session_state.filters
debug_log = st.session_state.debug_log or []

filtered_tasks = apply_filters(tasks, filters)
it_tasks = [t for t in tasks if t.get("normalized_category", "OTHER") in IT_CATEGORIES]

# ── Header ────────────────────────────────────────────────────────
col_title, col_cache = st.columns([3, 1])
with col_title:
    st.header("📊 Freelance Market Analyzer")
with col_cache:
    if st.session_state.last_run:
        dt = st.session_state.last_run
        cache_age = datetime.now() - dt
        if cache_age.total_seconds() < 60:
            age_str = "только что"
        elif cache_age.total_seconds() < 3600:
            age_str = f"{int(cache_age.total_seconds() // 60)} мин назад"
        else:
            age_str = f"{int(cache_age.total_seconds() // 3600)} ч назад"
        st.markdown(
            f"<div class='cache-badge'>📦 {dt.strftime('%d.%m.%Y %H:%M')} · {age_str}</div>",
            unsafe_allow_html=True,
        )
        if cache_age > timedelta(hours=1):
            st.warning("⚠️ Данные старше 1 часа. Нажмите «Собрать» для обновления.")

tab_overview, tab_tasks_tab, tab_charts, tab_excel, tab_logs = st.tabs(
    ["📈 Обзор", "📋 Задачи", "📊 Графики", "⬇️ Экспорт", "🔧 Логи"]
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
    cols[3].metric(
        "Категорий",
        len(stats.get("category_counts", {})) if stats else 0,
    )
    cols[4].metric(
        "Технологий",
        len(stats.get("technology_counts", {})) if stats else 0,
    )

    cat_counts = stats.get("category_counts", {}) if stats else {}
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

    ba = stats.get("budget_analysis", {}) if stats else {}
    if ba:
        st.subheader("💰 Бюджет")
        bc = st.columns(4)
        bc[0].metric("Средний", f"₽{(ba.get('average_budget_min') or 0):,.0f}")
        bc[1].metric("Медиана", f"₽{(ba.get('median_budget_min') or 0):,.0f}")
        bc[2].metric("Мин", f"₽{(ba.get('min_budget') or 0):,.0f}")
        bc[3].metric("Макс", f"₽{(ba.get('max_budget') or 0):,.0f}")

    ca = stats.get("competition_analysis", {}) if stats else {}
    if ca:
        st.subheader("🏆 Конкуренция")
        st.metric(
            "Среднее число откликов",
            f"{(ca.get('overall_average_proposals') or 0):.1f}",
        )

    st.caption(
        f"Показано: {len(filtered_tasks)} из {len(tasks)} задач"
        f" (после фильтров: {len(apply_filters(tasks, filters))})"
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
        else:
            st.info("📭 Графики будут сгенерированы после сбора данных.")

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
        st.info("Excel-файл не найден. Соберите данные для генерации.")

# ── Tab: Logs ─────────────────────────────────────────────────────
with tab_logs:
    st.subheader("📋 Логи сбора")
    if debug_log:
        for line in debug_log:
            st.code(line, language="", line_numbers=False)
    else:
        st.info("Логов нет")
