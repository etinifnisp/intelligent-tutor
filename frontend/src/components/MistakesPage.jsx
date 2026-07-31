import { useState, useEffect } from 'react';
import { authFetch, renderMarkdown } from '../utils.jsx';
import QuestionDisplay from './QuestionDisplay.jsx';
import LoadingState from './LoadingState.jsx';
import ErrorState from './ErrorState.jsx';

const MISCONCEPTION_LABELS = {
  unit_error: 'Unit or dimensional mistake',
  careless_mistake: 'Fast incorrect response with high confidence',
  hint_dependency: 'Repeated incorrect attempts after hints',
  conceptual_gap: 'Conceptual misunderstanding',
};

export default function MistakesPage({ user, setPage }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expanded, setExpanded] = useState(null);

  function load() {
    setLoading(true);
    setError(null);
    authFetch('/learning/mistakes/me')
      .then(r => {
        if (!r.ok) throw new Error('Failed to load mistakes');
        return r.json();
      })
      .then(setData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }

  useEffect(() => { load(); }, [user?.id]);

  if (loading) return <LoadingState message="Loading your mistakes…" />;
  if (error) return <ErrorState message={error} onRetry={load} />;

  const mistakes = data?.mistakes || [];

  return (
    <div id="page-mistakes" className="page active student-page">
      <header className="page-header">
        <div>
          <h1>Review Mistakes</h1>
          <p className="page-subtitle">Learn from incorrect attempts and retry weak concepts</p>
        </div>
        <button className="btn btn-secondary" onClick={load}>Refresh</button>
      </header>

      {mistakes.length === 0 ? (
        <div className="card empty-card">
          <p>No incorrect attempts recorded yet. Complete a practice session to build your mistake log.</p>
          <button className="btn btn-primary" onClick={() => setPage('practice')}>Start practicing</button>
        </div>
      ) : (
        <div className="mistakes-list">
          {mistakes.map(m => (
            <article key={m.id} className="card mistake-card">
              <div className="mistake-header">
                <span className="mistake-date">
                  {new Date(m.created_at).toLocaleDateString()}
                </span>
                {m.misconception_type && (
                  <span className="badge badge-hard">
                    {MISCONCEPTION_LABELS[m.misconception_type] || m.misconception_type}
                  </span>
                )}
                {m.subject && <span className="mistake-subject">{m.subject} · {m.chapter}</span>}
              </div>

              <button
                className="mistake-toggle"
                onClick={() => setExpanded(expanded === m.id ? null : m.id)}
              >
                {expanded === m.id ? 'Hide details' : 'Show question & your answer'}
              </button>

              {expanded === m.id && (
                <div className="mistake-detail">
                  {m.question_text && (
                    <div
                      className="mistake-question"
                      dangerouslySetInnerHTML={renderMarkdown(m.question_text)}
                    />
                  )}
                  <div className="mistake-answer-block">
                    <strong>Your answer:</strong>
                    <span>{m.answer || '—'}</span>
                  </div>
                  {m.confidence != null && (
                    <div className="mistake-meta">
                      Confidence: {Math.round(m.confidence * 100)}%
                      {m.hints_used > 0 && ` · ${m.hints_used} hint(s) used`}
                    </div>
                  )}
                  {m.concept_ids?.length > 0 && (
                    <div className="concept-chip-list">
                      {m.concept_ids.map(c => (
                        <span key={c} className="concept-chip">{c}</span>
                      ))}
                    </div>
                  )}
                </div>
              )}

              <div className="mistake-actions">
                <button className="btn btn-primary" onClick={() => setPage('practice')}>
                  Retry similar question
                </button>
                <button className="btn btn-ghost" onClick={() => setPage('tutor')}>
                  Ask tutor about this
                </button>
              </div>
            </article>
          ))}
        </div>
      )}

      {data?.retry_recommendations?.length > 0 && (
        <section className="card">
          <h2>Suggested retry questions</h2>
          <ul className="rec-list">
            {data.retry_recommendations.map(r => (
              <li key={r.question_id} className="rec-row">
                <span>{r.chapter || r.question_id}</span>
                <span className="rec-reasons">{(r.reasons || []).join(' · ')}</span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
