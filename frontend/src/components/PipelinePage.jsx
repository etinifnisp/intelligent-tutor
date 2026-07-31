import { useState, useEffect } from 'react';
import { masteryColor } from '../utils.jsx';

// ── PipelinePage ───────────────────────────────────────────────────────────
// Page 3: Real-time trace of the last RAG pipeline run + console logs panel.
// Subscribes to PipelineBus and renders each step as a colour-coded card.
// No emoji used anywhere.

export default function PipelinePage() {
  const [steps, setSteps] = useState([]);
  const [logs, setLogs]   = useState([]);

  useEffect(() => {
    window.PipelineBus.subscribe(setSteps);
    window.AppLogger.subscribe(setLogs);
    return () => {
      window.PipelineBus.unsubscribe(setSteps);
      window.AppLogger.unsubscribe(setLogs);
    };
  }, []);

  // ── Step metadata ─────────────────────────────────────────────────────
  const stepConfig = {
    intent_classify: { num: '1', label: 'Intent Classification', cls: 'step-intent' },
    graph_query:     { num: '2', label: 'Knowledge Graph Query',  cls: 'step-graph'  },
    file_select:     { num: '3', label: 'File Selection',         cls: 'step-files'  },
    llm_complete:    { num: '4', label: 'LLM Generation',         cls: 'step-llm'    },
    mastery_update:  { num: '5', label: 'Mastery Update',         cls: 'step-mastery'},
  };

  // ── Per-step body renderers ───────────────────────────────────────────
  function renderStepBody(step, data) {
    if (step === 'intent_classify') return (
      <div className="step-kv">
        <div className="kv-row">
          <span className="kv-key">Decision</span>
          <span className="kv-val">
            <span className={`badge ${data.lane === 'PIPELINE' ? 'badge-pipeline' : 'badge-direct'}`}>{data.lane}</span>
          </span>
        </div>
        <div className="kv-row">
          <span className="kv-key">Message</span>
          <span className="kv-val" style={{ fontStyle: 'italic', color: 'var(--text-muted)' }}>"{data.message_preview}..."</span>
        </div>
      </div>
    );

    if (step === 'graph_query') return (
      <div className="step-kv">
        <div className="kv-row"><span className="kv-key">Concept</span><span className="kv-val" style={{ color: 'var(--purple)' }}>{data.concept}</span></div>
        <div className="kv-row">
          <span className="kv-key">Current Mastery</span>
          <div className="mastery-bar-row">
            <div className="mastery-mini-bar">
              <div className="mastery-mini-fill" style={{ width: `${data.mastery * 100}%`, background: masteryColor(data.mastery) }}/>
            </div>
            <span className="kv-val">{Math.round(data.mastery * 100)}%</span>
          </div>
        </div>
        <div className="kv-row"><span className="kv-key">Prereq Chain</span><span className="kv-val">{(data.prereq_chain || []).join(' > ') || '—'}</span></div>
        <div className="kv-row"><span className="kv-key">Unmastered</span><span className="kv-val" style={{ color: 'var(--red)' }}>{(data.unmastered_prereqs || []).join(', ') || 'None'}</span></div>
        <div className="kv-row"><span className="kv-key">Hint Tools</span><span className="kv-val" style={{ color: 'var(--amber)' }}>{(data.hint_scaffolds || []).join(', ') || 'None'}</span></div>
      </div>
    );

    if (step === 'file_select') return (
      <div className="step-kv">
        <div className="kv-row">
          <span className="kv-key">Selected</span>
          <span className="kv-val">{(data.selected || []).length} / {data.total_in_store} files</span>
        </div>
        <div style={{ marginTop: 6 }}>
          {(data.selected || []).map(f => (
            <span key={f} className="file-chip">file: {f}</span>
          ))}
        </div>
      </div>
    );

    if (step === 'llm_complete') return (
      <div className="step-kv">
        <div className="kv-row"><span className="kv-key">Model</span><span className="kv-val">{data.model}</span></div>
        <div className="kv-row"><span className="kv-key">Words generated</span><span className="kv-val" style={{ color: 'var(--green)' }}>~{data.words}</span></div>
        <div className="kv-row">
          <span className="kv-key">Lane</span>
          <span className="kv-val">
            <span className={`badge ${data.lane === 'PIPELINE' ? 'badge-pipeline' : 'badge-direct'}`}>{data.lane}</span>
          </span>
        </div>
      </div>
    );

    if (step === 'mastery_update') return (
      <div className="step-kv">
        <div className="kv-row"><span className="kv-key">Concept</span><span className="kv-val" style={{ color: 'var(--purple)' }}>{data.concept}</span></div>
        <div className="kv-row">
          <span className="kv-key">Before</span>
          <div className="mastery-bar-row">
            <div className="mastery-mini-bar">
              <div className="mastery-mini-fill" style={{ width: `${data.before * 100}%`, background: masteryColor(data.before) }}/>
            </div>
            <span className="kv-val">{Math.round(data.before * 100)}%</span>
          </div>
        </div>
        <div className="kv-row">
          <span className="kv-key">After</span>
          <div className="mastery-bar-row">
            <div className="mastery-mini-bar">
              <div className="mastery-mini-fill" style={{ width: `${data.after * 100}%`, background: masteryColor(data.after) }}/>
            </div>
            <span className="kv-val">{Math.round(data.after * 100)}%</span>
          </div>
        </div>
        <div className="kv-row">
          <span className="kv-key">Delta</span>
          <span className={`kv-val ${data.delta >= 0 ? 'delta-pos' : 'delta-neg'}`}>
            {data.delta >= 0 ? '+' : ''}{(data.delta * 100).toFixed(1)}%
          </span>
        </div>
      </div>
    );

    // Fallback for unknown step types
    return <div className="step-body">{JSON.stringify(data)}</div>;
  }

  return (
    <div id="page-pipeline" className="page active">

      {/* Header */}
      <div className="pipeline-header">
        <div>
          <div className="pipeline-title">RAG Pipeline Viewer</div>
          <div className="pipeline-sub">
            Real-time trace of the last pipeline run. Send a message from the Tutor page to see it here.
          </div>
        </div>
        {steps.length > 0 && (
          <span className="badge badge-pipeline" style={{ marginLeft: 'auto', fontSize: 11 }}>
            {steps.length} steps
          </span>
        )}
      </div>

      {/* Two-column body: steps + console logs */}
      <div className="pipeline-cols">

        {/* Steps */}
        <div className="pipeline-steps-col">
          {steps.length === 0 ? (
            <div className="pipeline-idle">
              <div className="pipeline-idle-text">No pipeline run yet</div>
              <div className="pipeline-idle-sub">
                Send a message from the Tutor page to trace the RAG pipeline steps here.
              </div>
            </div>
          ) : (
            steps.map((s, i) => {
              const cfg = stepConfig[s.step] || { num: `${i + 1}`, label: s.step, cls: '' };
              return (
                <div key={i} className={`pipeline-step-card ${cfg.cls}`}>
                  <div className="step-header">
                    <div className="step-num">{cfg.num}</div>
                    <div className="step-name">{cfg.label}</div>
                    <span className="step-time">{new Date(s.ts).toLocaleTimeString()}</span>
                  </div>
                  {renderStepBody(s.step, s.data || {})}
                </div>
              );
            })
          )}
        </div>

        {/* Console logs */}
        <div className="pipeline-logs-col">
          <div className="pipeline-logs-header">Console Logs</div>
          <div className="pipeline-logs-body">
            {logs.length === 0 ? (
              <div style={{ color: 'var(--text-dim)', fontSize: 12, padding: '16px 4px', textAlign: 'center' }}>
                No logs yet
              </div>
            ) : (
              logs.map((l, i) => (
                <div key={i} className={`log-entry ${l.level}`}>
                  <span style={{ color: 'var(--border-bright)', marginRight: 6 }}>{l.ts}</span>
                  {l.msg}
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
