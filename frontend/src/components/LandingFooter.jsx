export default function LandingFooter({ onScrollTo, onEnter }) {
  return (
    <footer className="landing-footer">
      <div className="landing-footer-inner">
        <div className="landing-footer-brand">
          <div className="hero-brand-mark">JT</div>
          <div>
            <strong>JEE Tutor</strong>
            <p>Adaptive learning for IIT-JEE aspirants</p>
          </div>
        </div>

        <div className="landing-footer-links">
          <div className="landing-footer-col">
            <h4>Product</h4>
            <button type="button" onClick={() => onScrollTo('home')}>Home</button>
            <button type="button" onClick={() => onScrollTo('features')}>Features</button>
            <button type="button" onClick={onEnter}>Dashboard</button>
          </div>
          <div className="landing-footer-col">
            <h4>Learn</h4>
            <span>Adaptive Practice</span>
            <span>AI Tutor</span>
            <span>Progress Tracking</span>
          </div>
          <div className="landing-footer-col">
            <h4>Subjects</h4>
            <span>Physics</span>
            <span>Chemistry</span>
            <span>Mathematics</span>
          </div>
        </div>
      </div>

      <div className="landing-footer-bottom">
        <span>&copy; {new Date().getFullYear()} JEE Intelligent Tutor</span>
        <span>Built for JEE Main &amp; Advanced preparation</span>
      </div>
    </footer>
  );
}
