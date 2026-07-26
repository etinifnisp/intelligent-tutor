// ── MasteryRing ────────────────────────────────────────────────────────────
// SVG donut-ring displaying a mastery percentage with animated stroke-dasharray.

export default function MasteryRing({ pct, color, size = 100 }) {
  const r    = (size - 14) / 2;
  const circ = 2 * Math.PI * r;
  const dash = circ * pct;

  return (
    <div className="mastery-ring" style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        {/* Background track */}
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="var(--border)" strokeWidth={8}/>
        {/* Filled arc */}
        <circle
          cx={size/2} cy={size/2} r={r}
          fill="none" stroke={color} strokeWidth={8}
          strokeDasharray={`${dash} ${circ}`}
          strokeLinecap="round"
          style={{ transition: 'stroke-dasharray .8s ease' }}
        />
      </svg>
      <div className="mastery-ring-label">
        <div className="mastery-ring-pct" style={{ color }}>{Math.round(pct * 100)}%</div>
        <div className="mastery-ring-sub">mastery</div>
      </div>
    </div>
  );
}
