import { useState, useEffect } from 'react';
import { apiFetch, startGuestSession } from './utils.jsx';
import HeroPage from './components/HeroPage.jsx';
import Sidebar from './components/Sidebar.jsx';
import TodayPage from './components/TodayPage.jsx';
import PracticePage from './components/PracticePage.jsx';
import ChatPage from './components/ChatPage.jsx';
import MistakesPage from './components/MistakesPage.jsx';
import ProgressPage from './components/ProgressPage.jsx';
import GraphPage from './components/GraphPage.jsx';
import AdminPage from './components/AdminPage.jsx';

export default function App() {
  const [view, setView] = useState('landing');
  const [page, setPage] = useState('today');
  const [online, setOnline] = useState(false);
  const [mobileNav, setMobileNav] = useState(false);
  const [user, setUser] = useState(null);
  const [authError, setAuthError] = useState('');
  const [sessionState, setSessionState] = useState('loading');

  useEffect(() => {
    let active = true;

    async function bootSession() {
      setSessionState('loading');
      setAuthError('');
      try {
        const session = await startGuestSession();
        if (!active) return;
        setUser(session.user);
        setSessionState('ready');
      } catch (error) {
        if (!active) return;
        setAuthError(error.message || 'Could not start a guest session');
        setSessionState('error');
      }
    }

    bootSession();
    return () => { active = false; };
  }, []);

  useEffect(() => {
    function check() {
      apiFetch('/questions?limit=1', {}, 5000)
        .then(r => setOnline(r.ok))
        .catch(() => setOnline(false));
    }
    check();
    const t = setInterval(check, 8000);
    return () => clearInterval(t);
  }, []);

  async function retryGuestSession() {
    setSessionState('loading');
    setAuthError('');
    try {
      const session = await startGuestSession();
      setUser(session.user);
      setSessionState('ready');
    } catch (error) {
      setAuthError(error.message || 'Could not start a guest session');
      setSessionState('error');
    }
  }

  if (view === 'landing') {
    return (
      <HeroPage
        onEnter={() => { setView('dashboard'); window.scrollTo(0, 0); }}
        sessionReady={sessionState === 'ready'}
        sessionLoading={sessionState === 'loading'}
        sessionError={authError}
        onRetrySession={retryGuestSession}
      />
    );
  }

  if (sessionState === 'error') {
    return (
      <div className="app-error">
        <p>{authError}</p>
        <button type="button" className="btn btn-primary" onClick={retryGuestSession}>
          Retry connection
        </button>
      </div>
    );
  }

  if (!user) {
    return <div className="app-loading">Starting your secure guest session…</div>;
  }

  return (
    <div id="app-shell">
      <button
        className="mobile-nav-toggle"
        onClick={() => setMobileNav(v => !v)}
        aria-label="Toggle navigation"
      >
        <svg viewBox="0 0 24 24" width="20" height="20"><line x1="3" y1="6" x2="21" y2="6" stroke="currentColor" strokeWidth="2"/><line x1="3" y1="12" x2="21" y2="12" stroke="currentColor" strokeWidth="2"/><line x1="3" y1="18" x2="21" y2="18" stroke="currentColor" strokeWidth="2"/></svg>
      </button>
      <div className={`sidebar-wrap ${mobileNav ? 'open' : ''}`}>
        <Sidebar page={page} setPage={(p) => { setPage(p); setMobileNav(false); }} online={online} user={user}/>
      </div>
      {mobileNav && <div className="sidebar-overlay" onClick={() => setMobileNav(false)} />}
      <div id="main">
        {page === 'today'    && <TodayPage user={user} setPage={setPage}/>}
        {page === 'practice' && <PracticePage user={user}/>}
        {page === 'tutor'    && <ChatPage user={user}/>}
        {page === 'mistakes' && <MistakesPage user={user} setPage={setPage}/>}
        {page === 'progress' && <ProgressPage user={user}/>}
        {page === 'conceptmap' && <GraphPage user={user}/>}
        {page === 'admin'    && <AdminPage user={user}/>}
      </div>
    </div>
  );
}
