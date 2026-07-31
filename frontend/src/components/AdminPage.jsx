import { useState } from 'react';
import PipelinePage from './PipelinePage.jsx';
import GraphPage from './GraphPage.jsx';

export default function AdminPage({ user }) {
  const [tab, setTab] = useState('pipeline');
  const isAdmin = user?.role === 'ADMIN' || user?.role === 'TEACHER';

  return (
    <div id="page-admin" className="page active student-page">
      <header className="page-header">
        <div>
          <h1>Admin &amp; Demo</h1>
          <p className="page-subtitle">
            Pipeline traces, knowledge graph, and developer tools
            {!isAdmin && ' (demo view)'}
          </p>
        </div>
      </header>

      <div className="admin-tabs">
        <button
          className={`admin-tab ${tab === 'pipeline' ? 'active' : ''}`}
          onClick={() => setTab('pipeline')}
        >
          Pipeline
        </button>
        <button
          className={`admin-tab ${tab === 'graph' ? 'active' : ''}`}
          onClick={() => setTab('graph')}
        >
          Knowledge Graph
        </button>
      </div>

      <div className="admin-content">
        {tab === 'pipeline' && <PipelinePage />}
        {tab === 'graph' && <GraphPage user={user} />}
      </div>
    </div>
  );
}
