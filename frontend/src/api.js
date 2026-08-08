const BASE = '/api';

async function j(url, opts) {
  const res = await fetch(BASE + url, opts);
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(text || `${res.status} ${res.statusText}`);
  }
  return res.json();
}

export function fetchTasks(filters) {
  const p = new URLSearchParams();
  if (filters.q) p.set('q', filters.q);
  const sources = filters.sources ? [...filters.sources] : [];
  if (sources.length) p.set('sources', sources.join(','));
  const categories = filters.categories ? [...filters.categories] : [];
  if (categories.length) p.set('categories', categories.join(','));
  if (filters.budgetMin != null) p.set('budget_min', String(filters.budgetMin));
  if (filters.budgetMax != null) p.set('budget_max', String(filters.budgetMax));
  if (filters.freshness) p.set('freshness', filters.freshness);
  if (filters.hasBudget) p.set('has_budget', 'true');
  if (filters.maxProposals != null)
    p.set('max_proposals', String(filters.maxProposals));
  if (filters.searchDesc) p.set('search_desc', 'true');
  p.set('scope', filters.scope || 'all');
  p.set('sort', filters.sort || 'priority');
  p.set('limit', '2000');
  return j(`/tasks?${p}`);
}

export const fetchMeta = () => j('/filters');
export const fetchStatus = () => j('/status');
export const fetchAnalytics = () => j('/analytics');

export function startCollect(sources) {
  return j('/collect', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ sources }),
  });
}

export function fetchFullDescription(source, taskId) {
  return j(`/tasks/${encodeURIComponent(source)}/${encodeURIComponent(taskId)}/full-description`);
}
