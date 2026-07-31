import { useState, useEffect } from 'react';
import { authFetch, subjectColor, subjectIcon } from '../utils.jsx';
import LoadingState from './LoadingState.jsx';
import ErrorState from './ErrorState.jsx';

const SESSION_KEY = 'jee_last_session';

export function saveLastSession(data) {
  localStorage.setItem(SESSION_KEY, JSON.stringify({ ...data, savedAt: Date.now() }));
}

export function getLastSession() {
  try {
    const raw = localStorage.getItem(SESSION_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export default function TodayPage({ user, setPage }) {
  const [plan, setPlan] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const lastSession = getLastSession();

  function load() {
    setLoading(true);
    setError(null);
    authFetch('/learning/today/me')
      .then(r => {
        if (!r.ok) throw new Error('Failed to load today plan');
        return r.json();
      })
      .then(setPlan)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }

  useEffect(() => { load(); }, [user?.id]);

  if (loading) return <LoadingState message="Preparing your study plan…" />;
  if (error) return <ErrorState message={error} onRetry={load} />;

  const weak = plan?.weak_concepts || [];
  const due = plan?.revision_due || [];

  return (
    <div id="page-today" className="page active student-page">
      <header className="page-header">
        <div>
          <h1>Today</h1>
          <p className="page-subtitle">
            {user?.username ? `Welcome back, ${user.username}` : 'Your daily learning plan'}
          </p>
        </div>
        <button className="btn btn-secondary" onClick={load}>Refresh</button>
      </header>

      <div className="dash-pill-row">
        <div className="dash-pill">
          <span className="dash-pill-val">{plan?.questions_target || 5}</span>
          <span className="dash-pill-lbl">questions today</span>
        </div>
        <div className="dash-pill">
          <span className="dash-pill-val">{plan?.revision_due_count || 0}</span>
          <span className="dash-pill-lbl">due for revision</span>
        </div>
        <div className="dash-pill">
          <span className="dash-pill-val">{weak.length}</span>
          <span className="dash-pill-lbl">weak concepts</span>
        </div>
        <div className="dash-pill">
          <span className="dash-pill-val">{plan?.session_minutes || 20}m</span>
          <span className="dash-pill-lbl">session target</span>
        </div>
      </div>

      <div className="today-hero card">
        <div className="today-hero-main">
          <div className="today-hero-label">Today&apos;s study plan</div>
          <div className="today-hero-target">
            {plan?.questions_target || 5} questions · {plan?.revision_due_count || 0} revisions
          </div>
          <p className="today-narrative">{plan?.narrative}</p>
        </div>
        <button
          className="btn btn-primary today-cta"
          onClick={() => setPage('practice')}
        >
          Start Practice
        </button>
      </div>

      <div className="today-bento">
        <section className="card bento-wide">
          <h2>Weak concepts</h2>
          {weak.length === 0 ? (
            <p className="empty-hint">No weak areas flagged yet — complete practice to build your profile.</p>
          ) : (
            <ul className="concept-chip-list">
              {weak.map(c => (
                <li key={c} className="concept-chip weak">{c}</li>
              ))}
            </ul>
          )}
        </section>

        <section className="card bento-wide">
          <h2>Due for revision</h2>
          {due.length === 0 ? (
            <p className="empty-hint">Nothing due right now. Keep practicing!</p>
          ) : (
            <ul className="revision-list">
              {due.map(d => (
                <li key={d.concept_id} className="revision-item">
                  <span className="revision-concept">{d.concept_id}</span>
                  <span className="revision-reason">{d.reason}</span>
                </li>
              ))}
            </ul>
          )}
        </section>

        {lastSession && (
          <section className="card bento-narrow continue-card">
            <h2>Continue session</h2>
            <p className="continue-meta">
              {lastSession.subject} · {lastSession.chapter || 'Adaptive'}
              {lastSession.mode && ` · ${lastSession.mode}`}
            </p>
            <button
              className="btn btn-secondary"
              onClick={() => setPage('practice')}
            >
              Resume practice
            </button>
          </section>
        )}

        <section className={`card ${lastSession ? 'bento-narrow' : 'bento-wide'}`}>
          <h2>Quick actions</h2>
          <div className="quick-actions">
            <button className="btn btn-ghost" onClick={() => setPage('mistakes')}>Review mistakes</button>
            <button className="btn btn-ghost" onClick={() => setPage('tutor')}>Ask tutor</button>
            <button className="btn btn-ghost" onClick={() => setPage('progress')}>View progress</button>
          </div>
        </section>
      </div>

      {(plan?.recommended_questions?.length > 0) && (
        <section className="card">
          <h2>Recommended for you</h2>
          <div className="rec-list">
            {plan.recommended_questions.map(r => (
              <div key={r.question_id} className="rec-row">
                <span
                  className="rec-subject-icon"
                  style={{
                    background: `${subjectColor(r.subject)}18`,
                    color: subjectColor(r.subject),
                  }}
                >
                  {subjectIcon(r.subject)}
                </span>
                <div>
                  <div className="rec-chapter">{r.chapter || r.question_id}</div>
                  <div className="rec-reasons">{(r.reasons || []).join(' · ')}</div>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
