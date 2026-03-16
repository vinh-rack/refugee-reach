import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { API_BASE } from '../config';

interface NewsArticle {
  id: string;
  title: string | null;
  url: string;
  source_name: string | null;
  published_at: string | null;
  summary_hint: string | null;
}

interface NewsEvent {
  id: string;
  canonical_title: string;
  topic: string | null;
  region: string | null;
  status: string | null;
  severity_score: number | null;
  confidence_score: number | null;
  summary: string | null;
  article_count: number;
  first_seen_at: string | null;
  last_seen_at: string | null;
  articles: NewsArticle[];
}

interface NewsResponse {
  success: boolean;
  count: number;
  events: NewsEvent[];
  error?: string;
}

function formatDate(iso: string | null): string {
  if (!iso) return 'n/a';
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

function severityColor(score: number | null): string {
  if (score === null) return '#888';
  if (score >= 0.8) return '#ef4444';
  if (score >= 0.5) return '#fb923c';
  return '#22c55e';
}

function NewsPage() {
  const [events, setEvents] = useState<NewsEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  // Filters
  const [limit, setLimit] = useState(20);
  const [topic, setTopic] = useState('');
  const [region, setRegion] = useState('');
  const [minSeverity, setMinSeverity] = useState(0);

  // Dynamic filter options from DB
  const [topics, setTopics] = useState<string[]>([]);
  const [regions, setRegions] = useState<string[]>([]);

  const fetchFilters = async () => {
    try {
      const res = await fetch(`${API_BASE}/news/filters`);
      const data = await res.json();
      if (data.success) {
        setTopics(data.topics || []);
        setRegions(data.regions || []);
      }
    } catch (err) {
      console.error('Failed to fetch filter options:', err);
    }
  };

  const fetchNews = async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      params.set('limit', String(limit));
      if (topic) params.set('topic', topic);
      if (region) params.set('region', region);
      if (minSeverity > 0) params.set('min_severity', String(minSeverity));

      const res = await fetch(`${API_BASE}/news?${params}`);
      const data: NewsResponse = await res.json();
      if (data.success) {
        setEvents(data.events);
      } else {
        setError(data.error || 'Failed to fetch news');
      }
    } catch (err: any) {
      setError(err.message || 'Network error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFilters();
    fetchNews();
  }, []);

  const handleApplyFilters = () => {
    fetchNews();
  };

  return (
    <div className="news-page">
      <div className="news-header">
        <div className="news-header-left">
          <Link to="/" className="news-back-link" aria-label="Back to main page">← Back</Link>
          <h1 className="news-title">News Events</h1>
          <p className="news-subtitle">Latest geopolitical events from the pipeline</p>
        </div>
      </div>

      <div className="news-filters">
        <label className="news-filter-group">
          <span>Topic</span>
          <select value={topic} onChange={e => setTopic(e.target.value)}>
            <option value="">All</option>
            {topics.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
        </label>
        <label className="news-filter-group">
          <span>Region</span>
          <select value={region} onChange={e => setRegion(e.target.value)}>
            <option value="">All</option>
            {regions.map(r => <option key={r} value={r}>{r}</option>)}
          </select>
        </label>
        <label className="news-filter-group">
          <span>Min Severity</span>
          <input
            type="range"
            min="0"
            max="1"
            step="0.1"
            value={minSeverity}
            onChange={e => setMinSeverity(parseFloat(e.target.value))}
          />
          <span className="news-severity-value">{minSeverity.toFixed(1)}</span>
        </label>
        <label className="news-filter-group">
          <span>Limit</span>
          <input
            type="number"
            min="1"
            max="100"
            value={limit}
            onChange={e => setLimit(parseInt(e.target.value) || 20)}
            className="news-limit-input"
          />
        </label>
        <button className="news-apply-btn" onClick={handleApplyFilters}>Apply</button>
      </div>

      {loading && <div className="news-loading">Loading events...</div>}
      {error && <div className="news-error">{error}</div>}

      {!loading && !error && events.length === 0 && (
        <div className="news-empty">No events found. Try adjusting filters.</div>
      )}

      <div className="news-grid">
        {events.map(event => {
          const expanded = expandedId === event.id;
          return (
            <article
              key={event.id}
              className={`news-card ${expanded ? 'expanded' : ''}`}
              onClick={() => setExpandedId(expanded ? null : event.id)}
              role="button"
              tabIndex={0}
              aria-expanded={expanded}
              onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setExpandedId(expanded ? null : event.id); }}}
            >
              <h3 className="news-card-title">{event.canonical_title || 'Untitled event'}</h3>
              <div className="news-card-meta">
                {event.article_count} articles · Last seen: {formatDate(event.last_seen_at)}
              </div>
              <div className="news-card-chips">
                <span
                  className="news-chip"
                  style={{ color: severityColor(event.severity_score), borderColor: severityColor(event.severity_score) }}
                >
                  Severity {event.severity_score !== null ? event.severity_score.toFixed(2) : 'n/a'}
                </span>
                <span className="news-chip">
                  Confidence {event.confidence_score !== null ? event.confidence_score.toFixed(2) : 'n/a'}
                </span>
                <span className="news-chip">
                  {event.topic || 'unknown'} / {event.region || 'unknown'}
                </span>
              </div>
              <p className="news-card-summary">{event.summary || 'No summary available.'}</p>

              {expanded && event.articles.length > 0 && (
                <div className="news-articles-list" onClick={e => e.stopPropagation()}>
                  <h4>Source Articles ({event.articles.length})</h4>
                  <ul>
                    {event.articles.map(article => (
                      <li key={article.id}>
                        <a href={article.url} target="_blank" rel="noopener noreferrer">
                          {article.title || 'Untitled'}
                        </a>
                        <span className="news-article-meta">
                          {article.source_name || 'Unknown source'} · {formatDate(article.published_at)}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </article>
          );
        })}
      </div>
    </div>
  );
}

export default NewsPage;
