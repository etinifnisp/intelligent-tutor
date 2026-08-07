import LandingLayout from './LandingLayout.jsx';
import FeaturesSection from './FeaturesSection.jsx';

export default function HeroPage({ onEnter, sessionReady, sessionLoading, sessionError, onRetrySession }) {
  const enterDisabled = !sessionReady;
  const enterLabel = sessionLoading
    ? 'Connecting to tutor…'
    : sessionReady
      ? 'Open my study plan'
      : 'Connection unavailable';

  return (
    <LandingLayout onEnter={onEnter}>
      <section id="home" className="hero-section">
        <div className="hero-content">
          <div className="hero-copy">
            <p className="hero-eyebrow"><span/>Built for focused JEE preparation</p>
            <h1 className="hero-title">Study smarter.<br/><em>Rank higher.</em></h1>
            <p className="hero-subtitle">
              A personal AI study system that finds your gaps, explains difficult ideas,
              and turns every practice session into measurable progress.
            </p>

            <div className="hero-actions">
              <button
                type="button"
                className="btn btn-primary hero-cta"
                onClick={onEnter}
                disabled={enterDisabled}
              >
                {enterLabel}
                <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
                  <path d="M5 12h14M13 6l6 6-6 6" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </button>
              {sessionError && (
                <div className="hero-session-error">
                  <p>{sessionError}</p>
                  <button type="button" className="btn btn-secondary" onClick={onRetrySession}>
                    Retry connection
                  </button>
                </div>
              )}
              <button type="button" className="btn btn-secondary hero-cta-secondary"
                onClick={() => document.getElementById('features')?.scrollIntoView({ behavior: 'smooth' })}>
                See how it works
              </button>
            </div>

            <div className="hero-proof">
              <span><strong>6,500+</strong> past questions</span>
              <span><strong>3</strong> core subjects</span>
              <span><strong>24/7</strong> guided tutoring</span>
            </div>
          </div>

          <div className="hero-visual" aria-label="Study progress preview">
            <div className="hero-visual-top">
              <div><span className="visual-kicker">TODAY'S FOCUS</span><h2>Build momentum</h2></div>
              <span className="visual-date">DAY 24</span>
            </div>
            <div className="visual-score-row">
              <div className="visual-ring"><span>78<small>%</small></span></div>
              <div className="visual-score-copy"><strong>On track</strong><span>12% above last week</span></div>
            </div>
            <div className="visual-subjects">
              <div><span>Physics</span><i><b style={{ width: '82%' }}/></i><em>82%</em></div>
              <div><span>Chemistry</span><i><b style={{ width: '68%' }}/></i><em>68%</em></div>
              <div><span>Mathematics</span><i><b style={{ width: '74%' }}/></i><em>74%</em></div>
            </div>
            <div className="visual-next">
              <span className="visual-next-icon">→</span>
              <div><small>NEXT UP</small><strong>Rotational Dynamics</strong></div>
              <em>18 min</em>
            </div>
            <div className="visual-float visual-float-one">+12% mastery</div>
            <div className="visual-float visual-float-two">4 day streak</div>
          </div>
        </div>
      </section>

      <FeaturesSection onEnter={onEnter} />
    </LandingLayout>
  );
}
