import { useEffect, useState } from 'react';
import {
  IconSearch,
  IconBox,
  IconBolt,
  IconSliders,
  IconTrend,
  IconRefresh,
} from '../icons.jsx';

const SORT_OPTIONS = [
  { key: 'priority', label: 'Умный приоритет' },
  { key: 'date', label: 'Новые сверху' },
  { key: 'budget_desc', label: 'Бюджет: сначала большие' },
  { key: 'budget_asc', label: 'Бюджет: сначала малые' },
  { key: 'proposals_asc', label: 'Низкая конкуренция' },
];

const FRESHNESS_OPTIONS = [
  { key: null, label: 'Все время' },
  { key: '24h', label: '24ч' },
  { key: '3d', label: '3д' },
  { key: '7d', label: '7д' },
  { key: '30d', label: '30д' },
];

const SCOPE_OPTIONS = [
  { key: 'all', label: 'Все' },
  { key: 'it', label: 'IT' },
  { key: 'design', label: 'Дизайн' },
  { key: 'it_design', label: 'IT + Дизайн' },
];

const COMPETITION_OPTIONS = [
  { key: null, label: 'Любая' },
  { key: '10', label: 'Низкая (<10)' },
  { key: '30', label: 'До 30' },
];

const BUDGET_PRESETS = [
  { label: 'до 50к', min: null, max: 50000 },
  { label: '50–200к', min: 50000, max: 200000 },
  { label: '200к–1М', min: 200000, max: 1000000 },
  { label: '1М+', min: 1000000, max: null },
];

function SourceCheck({ source, checked, onChange }) {
  const cls = ['kwork', 'fl'].includes(source.key) ? source.key : 'default';
  return (
    <label className={`source-item ${checked ? 'selected' : ''}`}>
      <input type="checkbox" checked={checked} onChange={onChange} />
      <span className={`source-dot ${cls}`} />
      <span className="source-name">{source.label}</span>
    </label>
  );
}

function CategoryGroup({ group, selected, onToggle, onToggleAll }) {
  const all = group.categories.every((c) => selected.has(c.key));
  const some = group.categories.some((c) => selected.has(c.key));

  return (
    <div className="filter-group">
      <label className="filter-label">
        <input
          type="checkbox"
          checked={all}
          ref={(el) => el && (el.indeterminate = !all && some)}
          onChange={() => onToggleAll(group.categories.map((c) => c.key), !all)}
        />
        {group.name}
      </label>
      {group.categories.map((cat) => (
        <label
          key={cat.key}
          className={`filter-check ${cat.present ? '' : 'disabled'}`}
          style={{ paddingLeft: 22 }}
        >
          <input
            type="checkbox"
            checked={selected.has(cat.key)}
            disabled={!cat.present}
            onChange={() => onToggle(cat.key)}
          />
          {cat.label}
        </label>
      ))}
    </div>
  );
}

function Toggle({ label, checked, onChange }) {
  return (
    <label className="toggle-row">
      <input
        type="checkbox"
        checked={checked}
        onChange={onChange}
        className="filter-check-input"
      />
      {label}
    </label>
  );
}

export default function Sidebar({
  meta,
  status,
  filters,
  onFilterChange,
  onCollect,
  onReset,
}) {
  const [q, setQ] = useState(filters.q || '');
  const [presetKey, setPresetKey] = useState(null);

  const sources = meta?.sources || [];
  const budget = {
    min: meta?.budget_min ?? 0,
    max: meta?.budget_max ?? 500000,
  };

  const budgetMin = filters.budgetMin != null ? filters.budgetMin : budget.min;
  const budgetMax = filters.budgetMax != null ? filters.budgetMax : budget.max;

  const posFor = (v) =>
    budget.max > budget.min
      ? ((v - budget.min) / (budget.max - budget.min)) * 100
      : 50;

  const step = Math.max(1, Math.round((budget.max - budget.min) / 200));

  // debounce search input
  useEffect(() => {
    const t = setTimeout(() => {
      if (q !== (filters.q || '')) onFilterChange({ q });
    }, 350);
    return () => clearTimeout(t);
  }, [q]);

  const toggleSource = (key) => {
    const set = new Set(filters.sources);
    if (set.has(key)) set.delete(key);
    else set.add(key);
    onFilterChange({ sources: set });
  };

  const toggleCategory = (key) => {
    const set = new Set(filters.categories);
    if (set.has(key)) set.delete(key);
    else set.add(key);
    onFilterChange({ categories: set });
  };

  const toggleAllCategories = (keys, select) => {
    const set = new Set(filters.categories);
    keys.forEach((k) => (select ? set.add(k) : set.delete(k)));
    onFilterChange({ categories: set });
  };

  const applyPreset = (preset) => {
    setPresetKey(preset.label);
    onFilterChange({ budgetMin: preset.min, budgetMax: preset.max });
  };

  const fmt = (v) => v.toLocaleString('ru-RU');

  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-logo">
          <IconTrend size={18} />
        </div>
        <div>
          <div className="brand-title">Freelance Market</div>
          <div className="brand-sub">Анализ IT-заказов · Kwork приоритет</div>
        </div>
      </div>

      {/* Collection */}
      <div className="side-section">
        <div className="side-head">
          <IconBox size={13} /> Данные
        </div>
        <div className="source-list">
          {(meta?.all_sources || []).map((s) => (
            <SourceCheck
              key={s.key}
              source={s}
              checked={filters.sources.has(s.key)}
              onChange={() => toggleSource(s.key)}
            />
          ))}
        </div>
        <button
          className="btn btn-primary"
          disabled={status?.running || filters.sources.size === 0}
          onClick={() => onCollect([...filters.sources])}
        >
          {status?.running ? (
            <>
              <span className="spinner" /> Сбор в процессе...
            </>
          ) : (
            <>Собрать заказы</>
          )}
        </button>
      </div>

      {/* Status */}
      {status && (
        <div className="side-section">
          <div className="side-head">
            <IconBolt size={13} /> Статус
          </div>
          <div className="status-bar">
            {(status.running || status.message) && (
              <div className="status-row">
                {status.running ? <span className="spinner" /> : <span className="ok-dot" />}
                {status.message || 'Ожидание...'}
              </div>
            )}
            {status.running && (
              <div className="progress-track">
                <div
                  className="progress-fill"
                  style={{ width: `${Math.round(status.progress * 100)}%` }}
                />
              </div>
            )}
            {!status.running && status.last_run && (
              <div className="status-row">
                Обновлено: {new Date(status.last_run).toLocaleString('ru-RU')}
              </div>
            )}
            {!status.running && status.task_count > 0 && (
              <div className="status-row">{status.task_count} задач в базе</div>
            )}
          </div>
        </div>
      )}

      {/* Active filters */}
      <div className="side-section">
        <div className="side-head">
          <IconSliders size={13} /> Фильтры
        </div>

        {/* Sort */}
        <div className="group-name">Сортировка</div>
        <div className="select-wrap" style={{ marginBottom: 12 }}>
          <select
            value={filters.sort}
            onChange={(e) => onFilterChange({ sort: e.target.value })}
          >
            {SORT_OPTIONS.map((o) => (
              <option key={o.key} value={o.key}>
                {o.label}
              </option>
            ))}
          </select>
        </div>

        {/* Search */}
        <div className="group-name">Поиск</div>
        <div className="search-wrap">
          <IconSearch size={15} />
          <input
            className="search-input"
            placeholder="Поиск по заказам..."
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
        </div>
        <Toggle
          label="Искать и в описании"
          checked={filters.searchDesc}
          onChange={() => onFilterChange({ searchDesc: !filters.searchDesc })}
        />

        {/* Period */}
        <div className="group-name">Период публикации</div>
        <div className="seg" style={{ marginBottom: 12 }}>
          {FRESHNESS_OPTIONS.map((o) => (
            <span
              key={o.key || 'all'}
              className={`pill ${filters.freshness === o.key ? 'active' : ''}`}
              onClick={() => onFilterChange({ freshness: o.key })}
            >
              {o.label}
            </span>
          ))}
        </div>

        {/* Scope: IT / Дизайн */}
        <div className="group-name">Сфера</div>
        <div className="seg" style={{ marginBottom: 12 }}>
          {SCOPE_OPTIONS.map((o) => (
            <span
              key={o.key}
              className={`pill ${filters.scope === o.key ? 'active' : ''}`}
              onClick={() => onFilterChange({ scope: o.key })}
            >
              {o.label}
            </span>
          ))}
        </div>

        {/* IT categories */}
        {filters.scope !== 'design' && (
          <>
            <div className="group-name">IT-категории</div>
            <div style={{ marginBottom: 6 }}>
              {(meta?.category_groups || []).map((g) => (
                <CategoryGroup
                  key={g.name}
                  group={g}
                  selected={filters.categories}
                  onToggle={toggleCategory}
                  onToggleAll={toggleAllCategories}
                />
              ))}
            </div>
          </>
        )}

        {/* Budget */}
        <div className="group-name">Бюджет, ₽</div>
        <div className="budget-presets" style={{ marginBottom: 10 }}>
          {BUDGET_PRESETS.map((p) => (
            <span
              key={p.label}
              className={`preset-chip ${presetKey === p.label ? 'active' : ''}`}
              onClick={() => applyPreset(p)}
            >
              {p.label}
            </span>
          ))}
        </div>
        <div className="range-wrap">
          <div className="range-values">
            <span>от {fmt(budgetMin)}</span>
            <span>до {fmt(budgetMax)}</span>
          </div>
          <input
            type="range"
            min={budget.min}
            max={budgetMax}
            step={step}
            value={budgetMin}
            style={{ '--range-pos': `${posFor(budgetMin)}%` }}
            onChange={(e) => {
              setPresetKey(null);
              onFilterChange({ budgetMin: Number(e.target.value) });
            }}
          />
          <div style={{ height: 8 }} />
          <input
            type="range"
            min={budgetMin}
            max={budget.max}
            step={step}
            value={budgetMax}
            style={{ '--range-pos': `${posFor(budgetMax)}%` }}
            onChange={(e) => {
              setPresetKey(null);
              onFilterChange({ budgetMax: Number(e.target.value) });
            }}
          />
        </div>
        <Toggle
          label="Только с указанным бюджетом"
          checked={filters.hasBudget}
          onChange={() => onFilterChange({ hasBudget: !filters.hasBudget })}
        />

        {/* Competition */}
        <div className="group-name">Конкуренция (отклики)</div>
        <div className="seg">
          {COMPETITION_OPTIONS.map((o) => (
            <span
              key={o.key || 'any'}
              className={`pill ${filters.maxProposals === o.key ? 'active' : ''}`}
              onClick={() => onFilterChange({ maxProposals: o.key })}
            >
              {o.label}
            </span>
          ))}
        </div>

        <div style={{ height: 14 }} />
        <button className="btn btn-ghost" onClick={onReset}>
          <IconRefresh size={13} /> Сбросить всё
        </button>
      </div>
    </aside>
  );
}
