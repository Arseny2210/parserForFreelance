import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  fetchTasks,
  fetchMeta,
  fetchStatus,
  fetchAnalytics,
  startCollect,
} from './api.js';
import Sidebar from './components/Sidebar.jsx';
import TaskCard from './components/TaskCard.jsx';
import { IconBox, IconCode, IconTag, IconLayers, IconWallet, IconInbox } from './icons.jsx';

const DEFAULT_FILTERS = {
  q: '',
  sources: new Set(),
  categories: new Set(),
  scope: 'all',
  budgetMin: null,
  budgetMax: null,
  freshness: null,
  hasBudget: false,
  maxProposals: null,
  searchDesc: false,
  sort: 'priority',
};

function Metric({ label, value, sub, icon, tone }) {
  return (
    <div className="metric">
      <div className={`metric-icon ${tone || ''}`}>{icon}</div>
      <div className="label">{label}</div>
      <div className="value">{value}</div>
      {sub && <div className="sub">{sub}</div>}
    </div>
  );
}

export default function App() {
  const [meta, setMeta] = useState(null);
  const [status, setStatus] = useState(null);
  const [analytics, setAnalytics] = useState(null);
  const [filters, setFilters] = useState(DEFAULT_FILTERS);
  const [tasks, setTasks] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const statusTimer = useRef(null);

  const loadTasks = useCallback(async (f) => {
    setLoading(true);
    try {
      const data = await fetchTasks(f);
      setTasks(data.tasks);
      setTotal(data.total);
      setError(null);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial load
  useEffect(() => {
    (async () => {
      try {
        const [m, s, a] = await Promise.all([fetchMeta(), fetchStatus(), fetchAnalytics()]);
        setMeta(m);
        setStatus(s);
        setAnalytics(a);
        const initial = {
          ...DEFAULT_FILTERS,
          sources: new Set((m.all_sources || []).map((x) => x.key)),
        };
        setFilters(initial);
        loadTasks(initial);
      } catch (e) {
        setError('Не удалось подключиться к серверу: ' + e.message);
        setLoading(false);
      }
    })();
  }, [loadTasks]);

  // Refetch tasks whenever filters change
  useEffect(() => {
    if (!filters) return;
    const t = setTimeout(() => loadTasks(filters), 120);
    return () => clearTimeout(t);
  }, [filters, loadTasks]);

  // Poll status while collecting
  const pollStatus = useCallback(async () => {
    const tick = async () => {
      try {
        const s = await fetchStatus();
        setStatus(s);
        if (s.running) {
          statusTimer.current = setTimeout(tick, 1500);
        } else if (statusTimer.current) {
          clearTimeout(statusTimer.current);
          statusTimer.current = null;
          // refresh data after collection finished
          const [m, a] = await Promise.all([fetchMeta(), fetchAnalytics()]);
          setMeta(m);
          setAnalytics(a);
          loadTasks(filters);
        }
      } catch {
        statusTimer.current = setTimeout(tick, 3000);
      }
    };
    tick();
  }, [filters, loadTasks]);

  useEffect(() => {
    if (status?.running) {
      pollStatus();
    }
    return () => {
      if (statusTimer.current) clearTimeout(statusTimer.current);
    };
  }, [status?.running, pollStatus]);

  const onFilterChange = useCallback((patch) => {
    setFilters((prev) => {
      const next = { ...prev, ...patch };
      return { ...next, sources: patch.sources || prev.sources, categories: patch.categories || prev.categories };
    });
  }, []);

  const handleCollect = async (sources) => {
    try {
      await startCollect(sources);
      setStatus((prev) => ({ ...prev, running: true, message: 'Запуск...' }));
    } catch (e) {
      setError(e.message);
    }
  };

  const handleReset = () => {
    const reset = {
      ...DEFAULT_FILTERS,
      sources: new Set((meta?.all_sources || []).map((x) => x.key)),
    };
    setFilters(reset);
  };

  // number of active filters (for the "active filters" badge)
  const activeFilterCount = useMemo(() => {
    let n = 0;
    if (filters.q) n++;
    if (filters.sources.size !== (meta?.all_sources || []).length) n++;
    if (filters.categories.size > 0) n++;
    if (filters.budgetMin != null && filters.budgetMin !== meta?.budget_min) n++;
    if (filters.budgetMax != null && filters.budgetMax !== meta?.budget_max) n++;
    if (filters.freshness) n++;
    if (filters.hasBudget) n++;
    if (filters.maxProposals != null) n++;
    if (filters.scope !== 'all') n++;
    if (filters.sort !== 'priority') n++;
    return n;
  }, [filters, meta]);

  const stats = analytics || {};
  const catCount = Object.keys(stats.category_counts || {}).length;
  const techCount = Object.keys(stats.technology_counts || {}).length;
  const avgBudget = stats.budget_analysis?.average_budget_min;

  return (
    <div className="app">
      <Sidebar
        meta={meta}
        status={status}
        filters={filters}
        onFilterChange={onFilterChange}
        onCollect={handleCollect}
        onReset={handleReset}
      />

      <main className="main">
        <header className="header">
          <div>
            <h1>Рынок фриланса · IT-заказы</h1>
            <p>
              Свежие заказы с бирж. Умный приоритет: Kwork сверху · свежесть ·
              низкая конкуренция
            </p>
          </div>
          {status?.running && (
            <div className="last-run">
              <span className="spinner" /> Сбор заказов...
            </div>
          )}
          {status?.last_run && !status?.running && (
            <div className="last-run">
              <span className="live-dot" />
              Обновлено {new Date(status.last_run).toLocaleTimeString('ru-RU')}
            </div>
          )}
        </header>

        <div className="metrics">
          <Metric label="Всего заказов" value={total} icon={<IconBox />} />
          <Metric
            label="IT / Design"
            value={Object.values(stats.category_counts || {})
              .reduce((a, b) => a + b, 0) || 0}
            sub="IT-заказы"
            icon={<IconCode />}
            tone="green"
          />
          <Metric label="Категорий" value={catCount} icon={<IconTag />} />
          <Metric label="Технологий" value={techCount} icon={<IconLayers />} />
          {avgBudget != null && (
            <Metric
              label="Средний бюджет"
              value={`₽${Math.round(avgBudget).toLocaleString('ru-RU')}`}
              icon={<IconWallet />}
            />
          )}
        </div>

        <div className="tasks-head">
          <h2>
            {filters.q ? (
              <>Результаты по «{filters.q}»</>
            ) : (
              <>Все заказы</>
            )}
            {activeFilterCount > 0 && (
              <span className="count" style={{ marginLeft: 10 }}>
                · фильтров: {activeFilterCount}
              </span>
            )}
          </h2>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <span className="count">Kwork в приоритете · {total} найдено</span>
            {activeFilterCount > 0 && (
              <button className="btn btn-ghost" style={{ width: 'auto', padding: '6px 14px' }} onClick={handleReset}>
                Сбросить
              </button>
            )}
          </div>
        </div>

        {error && (
          <div className="empty">
            <div className="big">
              <IconInbox size={26} />
            </div>
            {error}
          </div>
        )}

        {loading && !error && (
          <div className="grid">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="skeleton" />
            ))}
          </div>
        )}

        {!loading && !error && tasks.length === 0 && (
          <div className="empty">
            <div className="big">
              <IconInbox size={26} />
            </div>
            Ничего не найдено. Попробуйте изменить фильтры или собрать новые заказы.
          </div>
        )}

        {!loading && !error && tasks.length > 0 && (
          <div className="grid">
            {tasks.map((t) => (
              <TaskCard key={`${t.source}-${t.task_id}-${t.url}`} task={t} />
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
