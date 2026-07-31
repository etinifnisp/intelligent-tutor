import { useState, useEffect } from 'react';
import { authFetch, masteryColor, subjectColor } from '../utils.jsx';
import MasteryRing from './MasteryRing.jsx';
import LoadingState from './LoadingState.jsx';
import ErrorState from './ErrorState.jsx';

function formatMs(ms) {
  if (!ms) return '—';
  const sec = Math.round(ms / 1000);
  if (sec < 60) return `${sec}s`;
  return `${Math.floor(sec / 60)}m ${sec % 60}s`;
}

export default function ProgressPage({ user }) {
  const [progress, setProgress] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  function load() {
    setLoading(true);
    setError(null);
    authFetch('/learning/progress/me')
      .then(r => {
        if (!r.ok) throw new Error('Failed to load progress');
        return r.json();
      })
      .then(setProgress)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    load();
    const t = setInterval(load, 30000);
    return () => clearInterval(t);
  }, [user?.id]);

  if (loading) return <LoadingState message="Loading your progress…" />;
  if (error) return <ErrorState message={error} onRetry={load} />;

  const misconceptions = Object.entries(progress?.misconceptions || {});
  const conceptCount = (progress?.concepts || []).length;

  return (
    <div id="page-progress" className="page active student-page">
      <header className="page-header">
        <div>
          <h1>Progress</h1>
          <p className="page-subtitle">Evidence-based mastery from your practice attempts</p>
        </div>
        <button className="btn btn-secondary" onClick={load}>Refresh</button>
      </header>

      <div className="progress-stats-row">
        <div className="stat-card card">
          <div className="stat-val">{progress?.total_attempts || 0}</div>
          <div className="stat-lbl">Total attempts</div>
        </div>
        <div className="stat-card card">
          <div className="stat-val">{Math.round((progress?.accuracy || 0) * 100)}%</div>
          <div className="stat-lbl">Overall accuracy</div>
        </div>
        <div className="stat-card card">
          <div className="stat-val">{Math.round((progress?.accuracy_without_hints || 0) * 100)}%</div>
          <div className="stat-lbl">No-hint accuracy</div>
        </div>
        <div className="stat-card card">
          <div className="stat-val">{formatMs(progress?.avg_response_time_ms)}</div>
          <div className="stat-lbl">Avg solving time</div>
        </div>
        <div className="stat-card card">
          <div className="stat-val">{progress?.revision_due || 0}</div>
          <div className="stat-lbl">Due for revision</div>
        </div>
        {progress?.improvement_delta != null && (
          <div className="stat-card card">
            <div className={`stat-val ${progress.improvement_delta >= 0 ? 'positive' : 'negative'}`}>
              {progress.improvement_delta >= 0 ? '+' : ''}{Math.round(progress.improvement_delta * 100)}%
            </div>
            <div className="stat-lbl">Recent improvement</div>
          </div>
        )}
      </div>

      <div className="progress-columns">
        <section className="card">
          <h2>Strongest topics</h2>
          {(progress?.strongest || []).length === 0 ? (
            <p className="empty-hint">Complete more attempts to see strengths.</p>
          ) : (
            <ul className="concept-progress-list">
              {progress.strongest.map(c => (
                <li key={c.concept_id} className="concept-progress-row">
                  <span className="concept-name">{c.concept_id}</span>
                  <span style={{ color: masteryColor(c.p_known), fontWeight: 600 }}>
                    {Math.round(c.p_known * 100)}%
                  </span>
                  <div className="concept-bar-bg">
                    <div
                      className="concept-bar-fill"
                      style={{ width: `${c.p_known * 100}%`, background: masteryColor(c.p_known) }}
                    />
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="card">
          <h2>Weakest topics</h2>
          {(progress?.weakest || []).length === 0 ? (
            <p className="empty-hint">No weak areas identified yet.</p>
          ) : (
            <ul className="concept-progress-list">
              {progress.weakest.map(c => (
                <li key={c.concept_id} className="concept-progress-row">
                  <span className="concept-name">{c.concept_id}</span>
                  <span style={{ color: masteryColor(c.p_known), fontWeight: 600 }}>
                    {Math.round(c.p_known * 100)}%
                  </span>
                  <div className="concept-bar-bg">
                    <div
                      className="concept-bar-fill"
                      style={{ width: `${c.p_known * 100}%`, background: masteryColor(c.p_known) }}
                    />
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      <section className="card">
        <h2>Mastery by concept · {conceptCount} tracked</h2>
        {(progress?.concepts || []).length === 0 ? (
          <p className="empty-hint">Start practicing to build your mastery profile.</p>
        ) : (
          <div className="mastery-grid">
            {progress.concepts.map(c => (
              <div key={c.concept_id} className="mastery-concept-card">
                <MasteryRing
                  pct={c.p_known}
                  color={subjectColor(c.subject) || masteryColor(c.p_known)}
                  size={72}
                />
                <div className="mastery-concept-info">
                  <div className="concept-name">{c.concept_id}</div>
                  <div className="mastery-meta">
                    {c.attempt_count} attempts · {Math.round(c.accuracy_without_hints * 100)}% no-hint
                    {c.mastered && <span className="badge badge-easy"> Mastered</span>}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {misconceptions.length > 0 && (
        <section className="card misconceptions-list">
          <h2>Detected misconceptions</h2>
          {misconceptions.map(([chapter, desc]) => (
            <div key={chapter} className="misconception-row">
              <div className="misconception-chapter">{chapter}</div>
              <div className="misconception-text">{desc}</div>
            </div>
          ))}
        </section>
      )}
    </div>
  );
}
