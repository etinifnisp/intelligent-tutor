// ── Sidebar ──────────────────────────────────────────────────────────────────

export default function Sidebar({ page, setPage, online }) {

  const icons = {
    chat: (
      <svg viewBox="0 0 24 24">
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
      </svg>
    ),
    questions: (
      <svg viewBox="0 0 24 24">
        <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>
        <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
      </svg>
    ),
    dashboard: (
      <svg viewBox="0 0 24 24">
        <rect x="3" y="3" width="7" height="7" rx="1"/>
        <rect x="14" y="3" width="7" height="7" rx="1"/>
        <rect x="3" y="14" width="7" height="7" rx="1"/>
        <rect x="14" y="14" width="7" height="7" rx="1"/>
      </svg>
    ),
    pipeline: (
      <svg viewBox="0 0 24 24">
        <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
      </svg>
    ),
    graph: (
      <svg viewBox="0 0 24 24">
        <circle cx="5" cy="12" r="2"/><circle cx="12" cy="5" r="2"/>
        <circle cx="19" cy="12" r="2"/><circle cx="12" cy="19" r="2"/>
        <line x1="7" y1="12" x2="10" y2="12"/>
        <line x1="12" y1="7" x2="12" y2="10"/>
        <line x1="14" y1="12" x2="17" y2="12"/>
        <line x1="12" y1="14" x2="12" y2="17"/>
      </svg>
    ),
  };

  const tabs = [
    { id: 'chat',      label: 'Chat'      },
    { id: 'questions', label: 'Questions' },
    { id: 'dashboard', label: 'Dashboard' },
    { id: 'pipeline',  label: 'Pipeline'  },
    { id: 'graph',     label: 'Graph'     },
  ];

  return (
    <div id="sidebar">
      <div className="sidebar-logo">
        JEE Intelligent Tutor
        <span>Powered by Gemini</span>
      </div>

      <div className="sidebar-section-label">Navigation</div>

      <nav className="sidebar-nav">
        {tabs.map(t => (
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
        <span className={`status-dot ${online ? 'online' : ''}`}/>
        <span className="status-label">{online ? 'Backend Online' : 'Offline'}</span>
      </div>
    </div>
  );
}
