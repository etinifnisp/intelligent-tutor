import { useState, useEffect, useRef } from 'react';
import { API } from './utils.jsx';
import Sidebar from './components/Sidebar.jsx';
import ChatPage from './components/ChatPage.jsx';
import QuestionsPage from './components/QuestionsPage.jsx';
import DashboardPage from './components/DashboardPage.jsx';
import PipelinePage from './components/PipelinePage.jsx';
import GraphPage from './components/GraphPage.jsx';

// ── App (Root Component) ───────────────────────────────────────────────────

export default function App() {
  const [page, setPage]     = useState('chat');
  const [online, setOnline] = useState(false);

  const sessionId = useRef(
    `session_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 6)}`
  ).current;

  useEffect(() => {
    function check() {
      fetch(`${API}/questions?limit=1`)
        .then(() => setOnline(true))
        .catch(() => setOnline(false));
    }
    check();
    const t = setInterval(check, 8000);
    return () => clearInterval(t);
  }, []);

  return (
    <div id="app-shell">
      <Sidebar page={page} setPage={setPage} online={online}/>
      <div id="main">
        {page === 'chat'      && <ChatPage      sessionId={sessionId}/>}
        {page === 'questions' && <QuestionsPage sessionId={sessionId}/>}
        {page === 'dashboard' && <DashboardPage sessionId={sessionId}/>}
        {page === 'pipeline'  && <PipelinePage/>}
        {page === 'graph'     && <GraphPage     sessionId={sessionId}/>}
      </div>
    </div>
  );
}
