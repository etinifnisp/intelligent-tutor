import { useState } from 'react';

export default function LandingNavbar({ activeSection, onScrollTo, onEnter }) {
  const [open, setOpen] = useState(false);

  const links = [
    { id: 'home', label: 'Home' },
    { id: 'features', label: 'Features' },
  ];

  function go(id) {
    onScrollTo(id);
    setOpen(false);
  }

  return (
    <header className="landing-navbar">
      <button className="landing-brand" onClick={() => go('home')} type="button">
        <div className="hero-brand-mark">JT</div>
        <span>JEE Tutor</span>
      </button>

      <nav className={`landing-nav ${open ? 'open' : ''}`}>
        {links.map(link => (
          <button
            key={link.id}
            type="button"
            className={`landing-nav-link ${activeSection === link.id ? 'active' : ''}`}
            onClick={() => go(link.id)}
          >
            {link.label}
          </button>
        ))}
        <button type="button" className="btn btn-primary landing-nav-cta" onClick={onEnter}>
          Start learning
        </button>
      </nav>

      <button
        type="button"
        className="landing-menu-toggle"
        onClick={() => setOpen(v => !v)}
        aria-label="Toggle menu"
      >
        <svg viewBox="0 0 24 24" width="22" height="22">
          <line x1="3" y1="6" x2="21" y2="6" stroke="currentColor" strokeWidth="2"/>
          <line x1="3" y1="12" x2="21" y2="12" stroke="currentColor" strokeWidth="2"/>
          <line x1="3" y1="18" x2="21" y2="18" stroke="currentColor" strokeWidth="2"/>
        </svg>
      </button>
    </header>
  );
}
