import { useMemo, useState } from 'react';
import { fetchFullDescription } from '../api.js';
import {
  IconArrowUpRight,
  IconCalendar,
  IconChevronDown,
  IconChevronUp,
  IconFlame,
  IconGlobe,
  IconMessage,
  IconShield,
  IconStar,
} from '../icons.jsx';

const SOURCE_LABELS = { kwork: 'Kwork', fl: 'FL.ru' };
const SOURCE_BADGE = { kwork: 'kwork', fl: 'fl' };

function formatBudget(task) {
  const bmin = task.budget_min;
  const bmax = task.budget_max;
  if (bmin && bmax && bmin !== bmax)
    return (
      <>
        ₽{bmin.toLocaleString('ru-RU')} — ₽{bmax.toLocaleString('ru-RU')}
      </>
    );
  if (bmin) return <>от ₽{bmin.toLocaleString('ru-RU')}</>;
  if (bmax) return <>до ₽{bmax.toLocaleString('ru-RU')}</>;
  return <span className="budget-na">договорная</span>;
}

function formatDate(value) {
  if (!value) return '';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return '';
  return d.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit' });
}

function formatAge(value) {
  if (!value) return '';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return '';
  const h = (Date.now() - d.getTime()) / 36e5;
  if (h < 1) return `${Math.max(1, Math.round(h * 60))} мин назад`;
  if (h < 24) return `${Math.round(h)} ч назад`;
  const days = Math.round(h / 24);
  return days === 1 ? 'вчера' : `${days} дн назад`;
}

function prettySource(key) {
  if (SOURCE_LABELS[key]) return SOURCE_LABELS[key];
  return key.charAt(0).toUpperCase() + key.slice(1);
}

function stripTruncation(text) {
  return text.replace(/\s*Показать полностью\s*$/i, '').trim();
}

export default function TaskCard({ task }) {
  const [expanded, setExpanded] = useState(false);
  const [fullDesc, setFullDesc] = useState(task.full_description || null);
  const [loadingDesc, setLoadingDesc] = useState(false);
  const [descError, setDescError] = useState(false);
  const isKwork = task.source === 'kwork';
  const techs = useMemo(
    () => (Array.isArray(task.technologies) ? task.technologies.slice(0, 6) : []),
    [task.technologies]
  );
  const title = task.title || 'Без названия';
  const url = task.url;

  const ageHours = useMemo(() => {
    if (!task.posted_at) return null;
    const d = new Date(task.posted_at);
    if (Number.isNaN(d.getTime())) return null;
    return (Date.now() - d.getTime()) / 36e5;
  }, [task.posted_at]);

  const isFresh = ageHours != null && ageHours <= 24;
  const isVeryFresh = ageHours != null && ageHours <= 3;
  const lowCompetition =
    task.proposals_count != null && task.proposals_count <= 5;

  const titleEl = url ? (
    <a href={url} target="_blank" rel="noopener noreferrer">
      {title}
    </a>
  ) : (
    title
  );

  const handleExpand = async (e) => {
    e.preventDefault();
    if (expanded) {
      setExpanded(false);
      return;
    }
    setExpanded(true);
    if (fullDesc || !isKwork || !url) return;
    setLoadingDesc(true);
    setDescError(false);
    try {
      const res = await fetchFullDescription(task.source, task.task_id);
      if (res.description) setFullDesc(res.description);
      else setDescError(true);
    } catch {
      setDescError(true);
    } finally {
      setLoadingDesc(false);
    }
  };

  const showDesc = fullDesc || stripTruncation(task.description || '');
  const canExpand = isKwork && !!url;

  const showExtra =
    task.country ||
    task.client_rating != null ||
    task.payment_verified;

  return (
    <article className={`card ${isKwork ? 'top-priority' : ''}`}>
      <div className="card-top">
        <span
          className={`source-badge ${SOURCE_BADGE[task.source] || 'other'}`}
        >
          <span className={`source-dot ${task.source}`} style={{ width: 7, height: 7 }} />
          {prettySource(task.source)}
        </span>
        {isVeryFresh && (
          <span className="prio-badge hot">
            <IconFlame size={12} /> Хот
          </span>
        )}
        {isFresh && !isVeryFresh && (
          <span className="prio-badge fresh">Новое</span>
        )}
        {lowCompetition && (
          <span className="prio-badge easy">
            <IconMessage size={12} /> Мало откликов
          </span>
        )}
        {isKwork && (
          <span className="priority-tag">
            <IconStar size={12} /> Приоритет
          </span>
        )}
      </div>

      <h3 className="card-title">{titleEl}</h3>

      {showDesc && (
        <div className={`desc-wrap ${expanded ? 'expanded' : ''}`}>
          <p className="card-desc" style={expanded ? { WebkitLineClamp: 'none' } : undefined}>
            {showDesc}
          </p>
          {canExpand && (
            <button className="desc-toggle" onClick={handleExpand}>
              {loadingDesc
                ? 'Загрузка...'
                : expanded
                  ? (
                      <>
                        Свернуть <IconChevronUp size={12} />
                      </>
                    )
                  : (
                      <>
                        Читать полностью <IconChevronDown size={12} />
                      </>
                    )}
            </button>
          )}
          {descError && (
            <div className="desc-error">Не удалось загрузить описание</div>
          )}
        </div>
      )}

      <div className="card-meta">
        {task.normalized_category && (
          <span className="chip category">{task.normalized_category}</span>
        )}
        {techs.map((t) => (
          <span key={t} className="chip tech">
            {t}
          </span>
        ))}
        {techs.length < (task.technologies || []).length && (
          <span className="chip">+{task.technologies.length - techs.length}</span>
        )}
      </div>

      {showExtra && (
        <div className="card-extra">
          {task.country && (
            <span title="Страна">
              <IconGlobe size={13} /> {task.country}
            </span>
          )}
          {task.client_rating != null && (
            <span className="rating" title="Рейтинг заказчика">
              <IconStar size={13} /> {Number(task.client_rating).toFixed(1)}
            </span>
          )}
          {task.payment_verified && (
            <span className="verified" title="Платёж подтверждён">
              <IconShield size={13} /> Платёж подтверждён
            </span>
          )}
        </div>
      )}

      <div className="card-footer">
        <div className="budget">
          {formatBudget(task)}{' '}
          <small>{task.currency || ''}</small>
        </div>
        <div className="card-foot-info">
          {task.proposals_count != null && (
            <span title="Отклики">
              <IconMessage size={13} /> {task.proposals_count}
            </span>
          )}
          <span className="date-cell" title="Дата публикации">
            <IconCalendar size={13} />
            <span className="date-num">{formatDate(task.posted_at)}</span>
            {formatAge(task.posted_at) && (
              <span className="date-age">· {formatAge(task.posted_at)}</span>
            )}
          </span>
          {url && (
            <a className="open-link" href={url} target="_blank" rel="noopener noreferrer">
              Открыть <IconArrowUpRight size={13} />
            </a>
          )}
        </div>
      </div>
    </article>
  );
}
