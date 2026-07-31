const FEATURES = [
  {
    icon: 'AP',
    color: '#4F6BF6',
    bg: '#EEF2FF',
    title: 'Adaptive Practice',
    description: 'Questions are selected based on your mastery level, weak concepts, and revision schedule — always in your zone of proximal development.',
    bullets: ['BKT-based mastery tracking', 'Subject & chapter filters', 'Timed practice mode'],
  },
  {
    icon: 'AI',
    color: '#7C3AED',
    bg: '#F3E8FF',
    title: 'Socratic AI Tutor',
    description: 'Get guided hints instead of instant answers. The tutor uses a 4-step hint ladder: concept, formula, setup, and full solution.',
    bullets: ['Real-time WebSocket chat', 'Answer verification', 'KaTeX math rendering'],
  },
  {
    icon: 'KG',
    color: '#16A34A',
    bg: '#DCFCE7',
    title: 'Knowledge Graph',
    description: '6,500+ JEE questions linked to a concept graph across Physics, Chemistry, and Mathematics with prerequisite tracking.',
    bullets: ['6,683 concept nodes', 'Adaptive study paths', 'Misconception detection'],
  },
  {
    icon: 'RAG',
    color: '#D97706',
    bg: '#FEF3C7',
    title: 'Hybrid Retrieval',
    description: 'FTS5 keyword search combined with FAISS vector embeddings for finding relevant questions and concept notes.',
    bullets: ['Local sentence-transformers', 'Reciprocal rank fusion', 'Semantic reranking'],
  },
  {
    icon: 'TD',
    color: '#DC2626',
    bg: '#FEE2E2',
    title: 'Today Dashboard',
    description: 'A daily study plan with revision due items, weak concept focus, and recommended questions to keep you on track.',
    bullets: ['Revision scheduler', 'Weak concept alerts', 'Session targets'],
  },
  {
    icon: 'PR',
    color: '#0891B2',
    bg: '#CFFAFE',
    title: 'Progress & Mistakes',
    description: 'Track mastery per concept, review past mistakes, and see your strongest and weakest areas over time.',
    bullets: ['Per-concept BKT states', 'Mistake review queue', 'Accuracy metrics'],
  },
];

const STATS = [
  { value: '6,567+', label: 'JEE Questions' },
  { value: '6,683', label: 'Graph Nodes' },
  { value: '3', label: 'Subjects' },
  { value: '4-step', label: 'Hint Ladder' },
];

export default function FeaturesSection({ onEnter }) {
  return (
    <section id="features" className="features-section">
      <div className="features-hero">
        <p className="hero-eyebrow">Platform capabilities</p>
        <h2 className="features-title">Everything you need to crack JEE</h2>
        <p className="features-lead">
          An end-to-end intelligent tutoring system — from adaptive question selection
          to Socratic guidance, built on real past-paper data and a knowledge graph.
        </p>
      </div>

      <div className="features-stats">
        {STATS.map(s => (
          <div key={s.label} className="features-stat">
            <div className="features-stat-val">{s.value}</div>
            <div className="features-stat-lbl">{s.label}</div>
          </div>
        ))}
      </div>

      <div className="features-grid">
        {FEATURES.map(f => (
          <article key={f.title} className="features-card">
            <div className="features-card-icon" style={{ background: f.bg, color: f.color }}>
              {f.icon}
            </div>
            <h3>{f.title}</h3>
            <p>{f.description}</p>
            <ul>
              {f.bullets.map(b => (
                <li key={b}>{b}</li>
              ))}
            </ul>
          </article>
        ))}
      </div>

      <div className="features-cta">
        <h2>Ready to start learning?</h2>
        <p>Jump into your personalized dashboard and begin practicing today.</p>
        <button type="button" className="btn btn-primary hero-cta" onClick={onEnter}>
          Go to Dashboard
          <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
            <path d="M5 12h14M13 6l6 6-6 6" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </button>
      </div>
    </section>
  );
}
