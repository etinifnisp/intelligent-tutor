import { useState, useEffect } from 'react';
import { API, masteryColor, subjectColor, subjectIcon } from '../utils.jsx';
import MasteryRing from './MasteryRing.jsx';

// ── DashboardPage ──────────────────────────────────────────────────────────
// Page 2: Learner stats, per-subject mastery rings, adaptive study path,
// and misconception list. Polls /stats/:session_id every 30 seconds.
// No emoji used anywhere.

export default function DashboardPage({ sessionId }) {
  const [stats, setStats]       = useState(null);
  const [chapters, setChapters] = useState({ Physics: [], Chemistry: [], Mathematics: [] });
  const [loading, setLoading]   = useState(true);

  function load() {
    Promise.all([
      fetch(`${API}/stats/${sessionId}`).then(r => r.json()),
      fetch(`${API}/chapters`).then(r => r.json())
    ])
    .then(([statsData, chaptersData]) => {
      setStats(statsData);
      setChapters(chaptersData);
      setLoading(false);
    })
    .catch(() => {
      setLoading(false);
      window.AppLogger.push('error', 'Failed to load dashboard');
    });
  }

  // Initial load + 30-second polling
  useEffect(() => {
    load();
    const t = setInterval(load, 30000);
    return () => clearInterval(t);
  }, []);

  // ── Loading state ─────────────────────────────────────────────────────
  if (loading) return (
    <div id="page-dashboard" className="page active"
      style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div className="spinner"/>
    </div>
  );

  const mastery        = stats?.mastery || {};
  const avgs           = stats?.subject_averages || {};
  const chapterMastery = stats?.chapter_mastery || {};
  const subjectChapters = stats?.subject_chapters || { Physics: [], Chemistry: [], Mathematics: [] };
  const subjects       = ['Physics', 'Chemistry', 'Mathematics'];
  const misconceptions = Object.entries(stats?.misconceptions || {});
  const nextConcepts   = stats?.next_concepts || {};

  // ── Group chapters by subject ───────────────
  const chaptersBySubject = { Physics: [], Chemistry: [], Mathematics: [], Other: [] };
  subjects.forEach(subj => {
    (subjectChapters[subj] || []).forEach(chapter => {
       const m = chapterMastery[chapter] || 0.0;
       chaptersBySubject[subj].push({ name: chapter, m });
    });
    // Sort chapters by mastery descending
    chaptersBySubject[subj].sort((a, b) => b.m - a.m);
  });

  return (
    <div id="page-dashboard" className="page active">

      {/* ── Header stats bar ─────────────────────────────────────────── */}
      <div className="dash-header">
        <div className="dash-stat">
          <div className="dash-stat-val" style={{ fontSize: 14, fontFamily: 'JetBrains Mono, monospace' }}>
            {sessionId.substring(0, 14)}
          </div>
          <div className="dash-stat-lbl">Session ID</div>
        </div>
        <div className="dash-divider"/>
        <div className="dash-stat">
          <div className="dash-stat-val">{stats?.session_count || 0}</div>
          <div className="dash-stat-lbl">Turns</div>
        </div>
        <div className="dash-divider"/>
        <div className="dash-stat">
          <div className="dash-stat-val">{Object.keys(mastery).length}</div>
          <div className="dash-stat-lbl">Concepts Studied</div>
        </div>
        <div className="dash-divider"/>
        <div className="dash-stat">
          <div className="dash-stat-val">{misconceptions.length}</div>
          <div className="dash-stat-lbl">Misconceptions</div>
        </div>
        <div style={{ marginLeft: 'auto' }}>
          <button id="dashboard-refresh-btn" className="btn btn-secondary" onClick={load}
            style={{ padding: '6px 16px', fontSize: 12 }}>
            Refresh
          </button>
        </div>
      </div>

      {/* ── Per-subject mastery cards ─────────────────────────────────── */}
      <div className="subject-cards">
        {subjects.map(subj => {
          const avg      = avgs[subj] || 0;
          const color    = subjectColor(subj);
          const abbr     = subjectIcon(subj);
          const concepts = chaptersBySubject[subj];
          return (
            <div key={subj} className="subject-card" style={{ borderTop: `3px solid ${color}` }}>
              <div className="subject-card-header">
                <div className="subject-icon" style={{ background: `${color}14`, color }}>
                  {abbr}
                </div>
                <div>
                  <div className="subject-title">{subj}</div>
                  <div className="subject-sub">{chaptersBySubject[subj].length} chapters tracked</div>
                </div>
              </div>

              <MasteryRing pct={avg} color={color} size={110}/>

              <div className="concept-list" style={{ maxHeight: '200px', overflowY: 'auto', paddingRight: '4px' }}>
                {concepts.length === 0 && (
                  <div style={{ fontSize: 12, color: 'var(--text-dim)', textAlign: 'center' }}>
                    No data yet — start chatting
                  </div>
                )}
                {concepts.map(({ name, m }) => (
                  <div key={name} className="concept-row">
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span className="concept-name">{name}</span>
                      <span style={{ fontSize: 11, color: masteryColor(m), fontWeight: 600 }}>
                        {Math.round(m * 100)}%
                      </span>
                    </div>
                    <div className="concept-bar-bg">
                      <div className="concept-bar-fill"
                        style={{ width: `${m * 100}%`, background: masteryColor(m) }}/>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>

      {/* ── Adaptive Study Path ───────────────────────────────────────── */}
      <div className="next-concepts">
        <h3>Adaptive Study Path</h3>
        {subjects.map(subj => {
          const color = subjectColor(subj);
          const abbr  = subjectIcon(subj);
          return nextConcepts[subj] ? (
            <div key={subj} className="next-concept-row">
              <div className="next-concept-icon" style={{ background: `${color}14`, color }}>
                {abbr}
              </div>
              <div>
                <div className="next-concept-name">{nextConcepts[subj]}</div>
                <div className="next-concept-sub">{subj}</div>
              </div>
              <div style={{ marginLeft: 'auto' }}>
                <span className="badge" style={{ background: `${color}14`, color }}>
                  Next Up
                </span>
              </div>
            </div>
          ) : (
            <div key={subj} className="next-concept-row" style={{ opacity: 0.5 }}>
              <div className="next-concept-icon" style={{ background: `${color}14`, color }}>
                {abbr}
              </div>
              <div className="next-concept-sub">
                {subj} — all prerequisites complete or not yet started
              </div>
            </div>
          );
        })}
      </div>

      {/* ── Misconceptions ────────────────────────────────────────────── */}
      {misconceptions.length > 0 && (
        <div className="misconceptions-list">
          <h3>Detected Misconceptions</h3>
          {misconceptions.map(([chapter, desc]) => (
            <div key={chapter} className="misconception-row">
              <div className="misconception-chapter">{chapter}</div>
              <div className="misconception-text">{desc}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
