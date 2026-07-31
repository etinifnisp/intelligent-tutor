import { useState, useEffect, useRef } from 'react';
import * as d3 from 'd3';
import { apiFetch, masteryColor, subjectColor } from '../utils.jsx';

// ── GraphPage ──────────────────────────────────────────────────────────────
// Page 4: Interactive D3 force-directed graph of the JEE knowledge concept map.
// Displays Chapters and their Concepts in a hierarchical layout.

export default function GraphPage({ user }) {
  const svgRef     = useRef(null);
  const tooltipRef = useRef(null);
  const simRef     = useRef(null);
  const rawDataRef = useRef(null);
  const masteryRef = useRef({});

  const [subjectFilter, setSubjectFilter] = useState('All');
  const [selectedNode, setSelectedNode]   = useState(null);
  const [loading, setLoading]             = useState(true);

  // ── Fetch graph topology + learner mastery on mount ───────────────────
  useEffect(() => {
    Promise.all([
      apiFetch('/graph').then(r => r.json()),
      apiFetch('/stats/me').then(r => r.json()).catch(() => ({ mastery: {}, chapter_mastery: {} })),
    ]).then(([gData, mData]) => {
      rawDataRef.current = gData;

      // Merge concept mastery and chapter mastery so D3 can colour both
      const mergedMastery = { ...(mData.mastery || {}) };
      Object.entries(mData.chapter_mastery || {}).forEach(([chap, m]) => {
         mergedMastery[chap] = m;
      });
      masteryRef.current = mergedMastery;
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [user?.id]);

  // ── Re-render graph when filter changes or data loads ─────────────────
  useEffect(() => {
    if (!loading && rawDataRef.current) renderGraph(subjectFilter);
  }, [loading, subjectFilter]);

  // ── D3 rendering ──────────────────────────────────────────────────────
  function renderGraph(filter) {
    const gData   = rawDataRef.current;
    const mastery = masteryRef.current;
    if (!gData || !svgRef.current) return;

    // Filter to chapter and concept nodes
    let graphNodes = (gData.nodes || []).filter(n => n.type === 'concept' || n.type === 'chapter');
    if (filter !== 'All') graphNodes = graphNodes.filter(n => n.subject === filter);
    const nodeIds = new Set(graphNodes.map(n => n.id));

    const edgesArray = gData.links || gData.edges || [];
    const links = edgesArray.filter(l =>
      ['prerequisite', 'hint_scaffold', 'has_concept'].includes(l.type) &&
      nodeIds.has(typeof l.source === 'object' ? l.source.id : l.source) &&
      nodeIds.has(typeof l.target === 'object' ? l.target.id : l.target)
    ).map(l => ({
      source: typeof l.source === 'object' ? l.source.id : l.source,
      target: typeof l.target === 'object' ? l.target.id : l.target,
      type:   l.type,
    }));

    const nodes = graphNodes.map(n => ({
      ...n,
      mastery: mastery[n.id] !== undefined ? mastery[n.id] : null,
    }));

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const { width, height } = svgRef.current.getBoundingClientRect();
    const W = width || 800, H = height || 600;

    const defs = svg.append('defs');

    // Premium Glow filter for glassmorphic nodes
    const filterGlow = defs.append('filter')
      .attr('id', 'glow')
      .attr('x', '-50%').attr('y', '-50%')
      .attr('width', '200%').attr('height', '200%');
    filterGlow.append('feGaussianBlur')
      .attr('stdDeviation', '8') // Increased blur for better glow
      .attr('result', 'coloredBlur');
    const feMerge = filterGlow.append('feMerge');
    feMerge.append('feMergeNode').attr('in', 'coloredBlur');
    feMerge.append('feMergeNode').attr('in', 'SourceGraphic');

    // Arrowhead markers
    ['prereq', 'hint'].forEach(t => {
      defs.append('marker')
        .attr('id', `arrow-${t}`)
        .attr('viewBox', '0 -4 8 8')
        .attr('refX', 28).attr('refY', 0)
        .attr('markerWidth', 6).attr('markerHeight', 6)
        .attr('orient', 'auto')
        .append('path')
        .attr('d', 'M0,-4L8,0L0,4')
        .attr('fill', t === 'prereq' ? '#2563EB' : '#D97706');
    });

    const g = svg.append('g');

    // Pan & zoom
    svg.call(d3.zoom().scaleExtent([0.1, 4]).on('zoom', e => g.attr('transform', e.transform)));

    // Curved Edges
    const link = g.append('g').selectAll('path')
      .data(links).join('path')
      .attr('class', 'd3-link')
      .attr('fill', 'none')
      .attr('stroke', d => {
         if (d.type === 'has_concept') return '#94A3B844';
         return d.type === 'prerequisite' ? '#2563EB66' : '#D9770666';
      })
      .attr('stroke-width', d => d.type === 'has_concept' ? 1 : 2)
      .attr('stroke-dasharray', d => d.type === 'hint_scaffold' ? '5 3' : null)
      .attr('marker-end', d => d.type === 'prerequisite' ? 'url(#arrow-prereq)' : (d.type === 'hint_scaffold' ? 'url(#arrow-hint)' : null));

    // Nodes
    const node = g.append('g').selectAll('g')
      .data(nodes).join('g')
      .attr('class', 'd3-node')
      .call(d3.drag()
        .on('start', (event, d) => { if (!event.active) sim.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })
        .on('drag',  (event, d) => { d.fx = event.x; d.fy = event.y; })
        .on('end',   (event, d) => { if (!event.active) sim.alphaTarget(0); d.fx = null; d.fy = null; })
      )
      .on('click', (event, d) => { event.stopPropagation(); setSelectedNode(d); })
      .on('mouseover', (event, d) => {
        const tip = tooltipRef.current;
        if (!tip) return;
        tip.style.opacity = '1';
        tip.innerHTML = `<strong>${d.id}</strong><br/>${d.subject || ''}<br/>Type: ${d.type}<br/>Mastery: ${d.mastery !== null ? Math.round(d.mastery * 100) + '%' : 'Not attempted'}`;
      })
      .on('mousemove', (event) => {
        const tip = tooltipRef.current;
        if (!tip) return;
        const rect = svgRef.current.parentElement.getBoundingClientRect();
        tip.style.left = (event.clientX - rect.left + 12) + 'px';
        tip.style.top  = (event.clientY - rect.top  + 12) + 'px';
      })
      .on('mouseout', () => { if (tooltipRef.current) tooltipRef.current.style.opacity = '0'; });

    // Chapter Nodes Rendering (Bigger, Glowing, Premium)
    const chapterNodes = node.filter(d => d.type === 'chapter');

    // Outer glassmorphic shell
    chapterNodes.append('circle')
      .attr('r', 28)
      .attr('fill', d => `${subjectColor(d.subject)}20`)
      .attr('stroke', d => subjectColor(d.subject))
      .attr('stroke-width', 2)
      .attr('filter', 'url(#glow)');

    // Inner mastery fill
    chapterNodes.append('circle')
      .attr('r', d => d.mastery !== null ? Math.max(8, 26 * d.mastery) : 8)
      .attr('fill', d => d.mastery !== null ? masteryColor(d.mastery) : '#4A476040')
      .attr('opacity', 0.85)
      .style('transition', 'r 0.5s ease, fill 0.5s ease');

    // Concept Nodes Rendering (Smaller, Satellite dots)
    const conceptNodes = node.filter(d => d.type === 'concept');

    conceptNodes.append('circle')
      .attr('r', 8)
      .attr('fill', d => `${masteryColor(d.mastery)}60`)
      .attr('stroke', d => masteryColor(d.mastery))
      .attr('stroke-width', 2);

    // Labels (only for chapters to avoid clutter, or very small for concepts)
    chapterNodes.append('text')
      .attr('dy', 38)
      .attr('text-anchor', 'middle')
      .attr('fill', '#1F2937')
      .attr('font-size', 11)
      .attr('font-weight', 600)
      .text(d => d.id.length > 20 ? d.id.substring(0, 18) + '...' : d.id);

    conceptNodes.append('text')
      .attr('dy', 18)
      .attr('text-anchor', 'middle')
      .attr('fill', '#6B7280')
      .attr('font-size', 8)
      .text(d => {
         const parts = d.id.split(' - ');
         const name = parts.length > 1 ? parts[1] : d.id;
         return name.length > 15 ? name.substring(0, 13) + '...' : name;
      });

    // Hierarchical Force simulation (Tuned for maximum efficiency)
    const sim = d3.forceSimulation(nodes)
      .force('link', d3.forceLink(links).id(d => d.id).distance(d => {
         if (d.type === 'has_concept') return 60; // Concepts tight around chapters
         return 220; // Chapters pushed further apart for cleaner layout
      }).strength(d => d.type === 'has_concept' ? 1.8 : 0.6))
      .force('charge', d3.forceManyBody().strength(d => d.type === 'chapter' ? -800 : -60))
      .force('center', d3.forceCenter(W / 2, H / 2))
      .force('collision', d3.forceCollide().radius(d => d.type === 'chapter' ? 50 : 15))
      .alphaDecay(0.08) // Settle faster
      .velocityDecay(0.6) // Dampen oscillations quickly
      .on('tick', () => {
        link.attr('d', d => {
           if (d.type === 'has_concept') {
              // Straight lines for satellites
              return `M${d.source.x},${d.source.y} L${d.target.x},${d.target.y}`;
           }
           // Smooth curved lines for prerequisites
           const dx = d.target.x - d.source.x;
           const dy = d.target.y - d.source.y;
           const dr = Math.sqrt(dx * dx + dy * dy) * 1.2; // Softer curves
           return `M${d.source.x},${d.source.y} A${dr},${dr} 0 0,1 ${d.target.x},${d.target.y}`;
        });
        node.attr('transform', d => `translate(${d.x},${d.y})`);
      });
    simRef.current = sim;

    svg.on('click', () => setSelectedNode(null));
  }

  const subjects = ['All', 'Physics', 'Chemistry', 'Mathematics'];

  return (
    <div id="page-graph" className="page active">

      {/* Controls bar */}
      <div className="graph-controls">
        <span className="graph-title">Concept Map (DAG)</span>
        <div style={{ display: 'flex', gap: 6 }}>
          {subjects.map(s => (
            <button
              key={s}
              className={`graph-filter-btn ${subjectFilter === s ? 'active' : ''}`}
              onClick={() => setSubjectFilter(s)}
              style={s !== 'All' ? {
                borderColor: subjectFilter === s ? subjectColor(s) : undefined,
                color:       subjectFilter === s ? subjectColor(s) : undefined,
              } : {}}
            >
              {s}
            </button>
          ))}
        </div>
        <span style={{ marginLeft: 'auto', fontSize: 12, color: 'var(--text-dim)' }}>
          Drag nodes · Scroll to zoom · Click to inspect
        </span>
      </div>

      <div className="graph-body">
        {/* Canvas */}
        <div className="graph-canvas-wrap">
          {loading ? (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', gap: 12 }}>
              <div className="spinner"/> <span style={{ color: 'var(--text-dim)' }}>Loading graph…</span>
            </div>
          ) : (
            <>
              <svg ref={svgRef} style={{ width: '100%', height: '100%' }}/>
              <div ref={tooltipRef} className="d3-tooltip"/>
            </>
          )}
        </div>

        {/* Sidebar: legend + node inspector */}
        <div className="graph-sidebar">
          <div className="graph-legend">
            <div className="legend-title">Mastery</div>
            {[['#DC2626', '< 40%'], ['#D97706', '40–70%'], ['#059669', '> 70%'], ['#94A3B8', 'Not attempted']].map(([c, l]) => (
              <div key={l} className="legend-row"><div className="legend-dot" style={{ background: c }}/><span>{l}</span></div>
            ))}
            <div className="legend-title" style={{ marginTop: 10 }}>Edge Types</div>
            <div className="legend-row"><div className="legend-line" style={{ background: '#2563EB' }}/><span>Prerequisite</span></div>
            <div className="legend-row">
              <div className="legend-line" style={{ background: '#D97706', backgroundImage: 'repeating-linear-gradient(90deg,#D97706 0,#D97706 5px,transparent 5px,transparent 8px)' }}/>
              <span>Hint scaffold</span>
            </div>
            <div className="legend-row"><div className="legend-line" style={{ background: '#94A3B8' }}/><span>Contains Concept</span></div>
            <div className="legend-title" style={{ marginTop: 10 }}>Subjects</div>
            {[['Physics', '#2563EB'], ['Chemistry', '#7C3AED'], ['Mathematics', '#059669']].map(([s, c]) => (
              <div key={s} className="legend-row">
                <div className="legend-dot" style={{ background: 'transparent', border: `2px solid ${c}` }}/>
                <span>{s}</span>
              </div>
            ))}
          </div>

          {/* Node inspector */}
          <div className="graph-node-info">
            {!selectedNode ? (
              <div style={{ color: 'var(--text-dim)', fontSize: 12, textAlign: 'center', marginTop: 20 }}>
                Click a node to inspect
              </div>
            ) : (
              <>
                <div className="node-info-name">{selectedNode.id}</div>
                <div className="node-info-sub">{selectedNode.subject || '—'}</div>
                <div className="node-info-mastery">
                  <div style={{ height: 6, background: 'var(--border)', borderRadius: 3, overflow: 'hidden', marginBottom: 4 }}>
                    <div style={{
                      height: '100%', borderRadius: 3,
                      background: masteryColor(selectedNode.mastery),
                      width: selectedNode.mastery !== null ? `${selectedNode.mastery * 100}%` : '0%',
                      transition: 'width .5s',
                    }}/>
                  </div>
                  <span style={{ fontSize: 12, color: masteryColor(selectedNode.mastery) }}>
                    {selectedNode.mastery !== null
                      ? `${Math.round(selectedNode.mastery * 100)}% mastery`
                      : 'Not yet attempted'}
                  </span>
                </div>
                <div className="node-info-row">
                  <span className="node-info-key">Type</span>
                  <span className="node-info-val" style={{ textTransform: 'capitalize' }}>{selectedNode.type}</span>
                </div>
                {selectedNode.question_count !== undefined && (
                  <div className="node-info-row">
                    <span className="node-info-key">Questions linked</span>
                    <span className="node-info-val">{selectedNode.question_count}</span>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
