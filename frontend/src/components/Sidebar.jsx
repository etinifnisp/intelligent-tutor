// ── Sidebar — learning-focused navigation (Phase 8) ───────────────────────

export default function Sidebar({ page, setPage, online, user }) {

  const icons = {
    today: (
      <svg viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
    ),
    practice: (
      <svg viewBox="0 0 24 24"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>
    ),
    tutor: (
      <svg viewBox="0 0 24 24"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
    ),
    mistakes: (
      <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
    ),
    progress: (
      <svg viewBox="0 0 24 24"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>
    ),
    conceptmap: (
      <svg viewBox="0 0 24 24"><circle cx="6" cy="6" r="3"/><circle cx="18" cy="6" r="3"/><circle cx="12" cy="18" r="3"/><line x1="8.5" y1="7.5" x2="10.5" y2="16"/><line x1="15.5" y1="7.5" x2="13.5" y2="16"/><line x1="9" y1="6" x2="15" y2="6"/></svg>
    ),
    admin: (
      <svg viewBox="0 0 24 24"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
    ),
  };

  const studentTabs = [
    { id: 'today',    label: 'Today'    },
    { id: 'practice', label: 'Practice' },
    { id: 'tutor',    label: 'Ask Tutor' },
    { id: 'mistakes', label: 'Mistakes' },
    { id: 'progress', label: 'Progress' },
    { id: 'conceptmap', label: 'Concept Map' },
  ];

  const demoTabs = [
    { id: 'admin', label: 'Admin / Demo' },
  ];

  return (
    <div id="sidebar">
      <div className="sidebar-logo">
        <div className="sidebar-logo-mark"><span>JT</span></div>
        <div className="sidebar-logo-text">
          JEE Tutor
          <span>Adaptive study OS</span>
        </div>
      </div>

      <div className="sidebar-section-label">Learn</div>
      <nav className="sidebar-nav">
        {studentTabs.map(t => (
          <button
            key={t.id}
            id={`nav-${t.id}`}
            className={`sidebar-btn ${page === t.id ? 'active' : ''}`}
            onClick={() => setPage(t.id)}
          >
            <span className="sidebar-btn-icon">{icons[t.id]}</span>
            {t.label}
          </button>
        ))}
      </nav>

      <div className="sidebar-section-label">Developer</div>
      <nav className="sidebar-nav">
        {demoTabs.map(t => (
          <button
            key={t.id}
            id={`nav-${t.id}`}
            className={`sidebar-btn ${page === t.id ? 'active' : ''}`}
            onClick={() => setPage(t.id)}
          >
            <span className="sidebar-btn-icon">{icons[t.id]}</span>
            {t.label}
          </button>
        ))}
      </nav>

      <div className="sidebar-spacer"/>

      <div className="sidebar-footer">
        <div className="sidebar-avatar">{user?.username?.slice(0, 1)?.toUpperCase() || 'S'}</div>
        <div className="sidebar-user">
          <strong>{user?.username || 'Student'}</strong>
          <span className="status-label"><i className={`status-dot ${online ? 'online' : ''}`}/>{online ? 'Tutor online' : 'Offline mode'}</span>
        </div>
      </div>
    </div>
  );
}
