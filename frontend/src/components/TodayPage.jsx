import { useState, useEffect } from 'react';
import { authFetch, subjectColor, subjectIcon } from '../utils.jsx';
import { buildStudyGroups, filterStudyGroups } from '../todayPlan.js';
import { getLastSession } from '../lastSession.js';
import LoadingState from './LoadingState.jsx';
import ErrorState from './ErrorState.jsx';

const SUBJECT_FILTERS = ['All', 'Physics', 'Chemistry', 'Mathematics'];

function fetchTodayPlan() {
  return authFetch('/learning/today/me').then((response) => {
    if (!response.ok) throw new Error('Failed to load today plan');
    return response.json();
  });
}

function formatDate(value) {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  return new Intl.DateTimeFormat(undefined, {
    day: 'numeric', month: 'short', year: 'numeric',
  }).format(date);
}

function ItemMeta({ item }) {
  const parts = [item.subject, item.difficulty].filter(Boolean);
  if (item.mastery !== null && item.mastery !== undefined) {
    parts.push(`${Math.round(item.mastery * 100)}% mastery`);
  }
  if (item.savedAt) parts.push(`Saved ${formatDate(item.savedAt)}`);

  if (parts.length === 0) return null;
  return (
    <div className="study-item-meta">
      {parts.map((part) => <span key={part}>{part}</span>)}
    </div>
  );
}

export default function TodayPage({ user, setPage }) {
  const [plan, setPlan] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [subjectFilter, setSubjectFilter] = useState('All');
  const [selectedId, setSelectedId] = useState(null);
  const [lastSession] = useState(() => getLastSession());

  function load() {
    setLoading(true);
    setError(null);
    fetchTodayPlan()
      .then(setPlan)
      .catch((loadError) => setError(loadError.message))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    let active = true;
    fetchTodayPlan()
      .then((nextPlan) => { if (active) setPlan(nextPlan); })
      .catch((loadError) => { if (active) setError(loadError.message); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [user?.id]);

  if (loading) return <LoadingState message="Preparing your study plan…" />;
  if (error) return <ErrorState message={error} onRetry={load} />;

  const groups = buildStudyGroups(plan, lastSession);
  const visibleGroups = filterStudyGroups(groups, subjectFilter)
    .filter((group) => group.items.length > 0);
  const visibleItems = visibleGroups.flatMap((group) => group.items);
  const selectedItem = visibleItems.find((item) => item.id === selectedId) || visibleItems[0] || null;
  const weakCount = Array.isArray(plan?.weak_concepts) ? plan.weak_concepts.length : 0;
  const totalAttempts = plan?.total_attempts ?? 0;
  const revisionDue = plan?.revision_due_count ?? 0;
  const selectedColor = selectedItem?.subject ? subjectColor(selectedItem.subject) : '#176bff';
  const selectedReason = selectedItem?.reasons?.join(' · ') || selectedItem?.reason || (
    selectedItem?.kind === 'focus' ? plan?.narrative : ''
  );
  const hasDetailFacts = Boolean(
    selectedItem?.subject || selectedItem?.chapter || selectedItem?.difficulty
    || selectedItem?.questionId || selectedItem?.savedAt
  );

  return (
    <div id="page-today" className="page active today-dashboard">
      <header className="today-dashboard-header">
        <div className="today-dashboard-heading">
          <span className="dashboard-kicker">Learning workspace</span>
          <h1>My Study Plan</h1>
          <p>{user?.username ? `Welcome back, ${user.username}` : 'Your evidence-based learning plan'}</p>
        </div>

        <div className="today-dashboard-summary" aria-label="Learning summary">
          <div><strong>{totalAttempts}</strong><span>Attempts recorded</span></div>
          <div><strong>{revisionDue}</strong><span>Revision due</span></div>
          <div><strong>{weakCount}</strong><span>Weak concepts</span></div>
        </div>

        <button type="button" className="dashboard-refresh" onClick={load} aria-label="Refresh study plan">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 11a8 8 0 1 0-2.3 5.7M20 4v7h-7"/></svg>
          Refresh
        </button>
      </header>

      <div className="today-dashboard-workspace">
        <section className="study-plan-board" aria-label="Study plan items">
          <div className="study-plan-controls">
            <div className="study-filter-tabs" aria-label="Filter by subject">
              {SUBJECT_FILTERS.map((subject) => (
                <button
                  type="button"
                  key={subject}
                  className={subjectFilter === subject ? 'active' : ''}
                  onClick={() => setSubjectFilter(subject)}
                >
                  {subject}
                </button>
              ))}
            </div>
            <button type="button" className="btn btn-primary study-start-btn" onClick={() => setPage('practice')}>
              Start practice
            </button>
          </div>

          <div className="study-groups">
            {visibleGroups.map((group) => (
              <section className="study-group" key={group.id}>
                <div className="study-group-heading">
                  <h2>{group.label}</h2>
                  <span>{group.items.length}</span>
                </div>
                <div className="study-group-items">
                  {group.items.map((item) => {
                    const isSelected = selectedItem?.id === item.id;
                    const color = item.subject ? subjectColor(item.subject) : '#176bff';
                    return (
                      <button
                        type="button"
                        key={item.id}
                        className={`study-item ${isSelected ? 'selected' : ''}`}
                        style={{ '--item-accent': color }}
                        onClick={() => setSelectedId(item.id)}
                        aria-pressed={isSelected}
                      >
                        <span className="study-item-subject" style={{ color }}>
                          {item.subject ? subjectIcon(item.subject) : 'AI'}
                        </span>
                        <span className="study-item-copy">
                          <span className="study-item-eyebrow">{item.eyebrow}</span>
                          <strong>{item.title}</strong>
                          <ItemMeta item={item} />
                        </span>
                        <span className={`study-item-badge ${item.kind}`}>{item.eyebrow}</span>
                        <svg className="study-item-arrow" viewBox="0 0 24 24" aria-hidden="true">
                          <path d="m9 18 6-6-6-6"/>
                        </svg>
                      </button>
                    );
                  })}
                </div>
              </section>
            ))}

            {visibleItems.length === 0 && (
              <div className="study-plan-empty">
                <span className="study-plan-empty-icon">
                  <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/></svg>
                </span>
                <h2>No live plan items{subjectFilter !== 'All' ? ` for ${subjectFilter}` : ''}</h2>
                <p>Complete a practice attempt to generate evidence-based recommendations.</p>
                <button type="button" className="btn btn-primary" onClick={() => setPage('practice')}>Start practice</button>
              </div>
            )}
          </div>
        </section>

        <aside className="study-detail-panel" aria-label="Selected study item">
          {selectedItem ? (
            <div className="study-detail-content" style={{ '--item-accent': selectedColor }}>
              <div className="study-detail-toolbar">
                <span>{selectedItem.eyebrow}</span>
                <button type="button" onClick={() => setPage('practice')} aria-label="Open practice">
                  <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M14 3h7v7M10 14 21 3M21 14v5a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5"/></svg>
                </button>
              </div>

              <div className="study-detail-title-row">
                <span className="study-detail-icon" style={{ background: `${selectedColor}14`, color: selectedColor }}>
                  {selectedItem.subject ? subjectIcon(selectedItem.subject) : 'AI'}
                </span>
                <div>
                  <span className="study-detail-subject">{selectedItem.subject || 'Adaptive learning'}</span>
                  <h2>{selectedItem.title}</h2>
                </div>
              </div>

              <div className="study-detail-tags">
                {selectedItem.difficulty && <span>{selectedItem.difficulty}</span>}
                {selectedItem.mode && <span>{selectedItem.mode}</span>}
                {selectedItem.nextReviewAt && <span>Due {formatDate(selectedItem.nextReviewAt)}</span>}
                {selectedItem.questionId && <span>PYQ recommendation</span>}
              </div>

              {selectedItem.mastery !== null && selectedItem.mastery !== undefined && (
                <div className="study-mastery-strip">
                  <div className="study-mastery-label">
                    <span>Current mastery evidence</span>
                    <strong>{Math.round(selectedItem.mastery * 100)}%</strong>
                  </div>
                  <div className="study-mastery-track">
                    <span style={{ width: `${Math.max(0, Math.min(100, selectedItem.mastery * 100))}%` }} />
                  </div>
                </div>
              )}

              {selectedReason && (
                <section className="study-detail-section">
                  <h3>Why this is in your plan</h3>
                  <p>{selectedReason}</p>
                </section>
              )}

              {hasDetailFacts && (
                <section className="study-detail-section study-detail-facts">
                  <h3>Learning details</h3>
                  {selectedItem.subject && <div><span>Subject</span><strong>{selectedItem.subject}</strong></div>}
                  {selectedItem.chapter && <div><span>Chapter</span><strong>{selectedItem.chapter}</strong></div>}
                  {selectedItem.difficulty && <div><span>Difficulty</span><strong>{selectedItem.difficulty}</strong></div>}
                  {selectedItem.questionId && <div><span>Question ID</span><strong>{selectedItem.questionId}</strong></div>}
                  {selectedItem.savedAt && <div><span>Session saved</span><strong>{formatDate(selectedItem.savedAt)}</strong></div>}
                </section>
              )}

              <div className="study-detail-actions">
                <button type="button" className="btn btn-primary" onClick={() => setPage('practice')}>Open adaptive practice</button>
                <button type="button" className="btn btn-secondary" onClick={() => setPage('tutor')}>Ask tutor</button>
              </div>
            </div>
          ) : (
            <div className="study-detail-empty">
              <span>Select a live plan item to inspect its learning evidence.</span>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}
