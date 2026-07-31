import { useState, useEffect, useCallback } from 'react';
import LandingNavbar from './LandingNavbar.jsx';
import LandingFooter from './LandingFooter.jsx';

export default function LandingLayout({ onEnter, children }) {
  const [activeSection, setActiveSection] = useState('home');

  const scrollToSection = useCallback((id) => {
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    const ids = ['home', 'features'];
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter(e => e.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio);
        if (visible[0]) setActiveSection(visible[0].target.id);
      },
      { rootMargin: '-20% 0px -55% 0px', threshold: [0, 0.25, 0.5] },
    );

    ids.forEach(id => {
      const el = document.getElementById(id);
      if (el) observer.observe(el);
    });
    return () => observer.disconnect();
  }, []);

  return (
    <div className="landing-page">
      <div className="hero-bg" aria-hidden="true">
        <div className="hero-orb hero-orb-1" />
        <div className="hero-orb hero-orb-2" />
        <div className="hero-orb hero-orb-3" />
      </div>

      <LandingNavbar
        activeSection={activeSection}
        onScrollTo={scrollToSection}
        onEnter={onEnter}
      />
      <main className="landing-main">{children}</main>
      <LandingFooter onScrollTo={scrollToSection} onEnter={onEnter} />
    </div>
  );
}
