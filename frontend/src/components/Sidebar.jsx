// ── Sidebar — learning-focused navigation ─────────────────────────────────

import { getSelectedModelLabel } from '../modelSettings.js';

export default function Sidebar({ page, setPage, online, user, onOpenSettings }) {

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
    { id: 'today',      label: 'Dashboard' },
    { id: 'practice',  label: 'Practice' },
    { id: 'tutor',     label: 'Ask Tutor' },
    { id: 'mistakes',  label: 'Mistakes' },
    { id: 'progress',  label: 'Progress' },
    { id: 'conceptmap',label: 'Concept Map' },
  ];

  const demoTabs = [
    { id: 'admin', label: 'Admin / Demo' },
  ];

  const activeModel = getSelectedModelLabel();

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

      {/* Settings button */}
      <button
        id="nav-settings"
        className="sidebar-settings-btn"
        onClick={onOpenSettings}
        title="AI Model Settings"
        type="button"
      >
        <span className="sidebar-btn-icon">
          <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
        </span>
        AI Settings
        <span className="sidebar-openrouter-badge" title={activeModel}>{activeModel.split(' ')[0]}</span>
      </button>

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
