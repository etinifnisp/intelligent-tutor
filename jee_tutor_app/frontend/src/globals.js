// ── Global Logger ──────────────────────────────────────────────────────────
// Pub/sub event bus for console log entries streamed to the Logs panel.
// Attached to window so all components can reach it without prop drilling
// (kept as-is from the original vanilla implementation).
window.AppLogger = (() => {
  let _logs = [], _subs = [];
  return {
    push(level, msg) {
      const e = { level, msg, ts: new Date().toLocaleTimeString() };
      _logs.push(e);
      if (_logs.length > 200) _logs.shift();
      _subs.forEach(fn => fn([..._logs]));
    },
    subscribe(fn)   { _subs.push(fn); fn([..._logs]); },
    unsubscribe(fn) { _subs = _subs.filter(s => s !== fn); },
  };
})();

// ── Pipeline Event Bus ─────────────────────────────────────────────────────
// Pub/sub event bus for per-turn RAG pipeline step events.
window.PipelineBus = (() => {
  let _runs = [], _current = [], _subs = [];
  return {
    push(step_data) {
      _current.push({ ...step_data, ts: Date.now() });
      _subs.forEach(fn => fn([..._current]));
    },
    newRun() {
      if (_current.length > 0) _runs.unshift([..._current]);
      if (_runs.length > 20) _runs.pop();
      _current = [];
      _subs.forEach(fn => fn([]));
    },
    subscribe(fn)   { _subs.push(fn); fn([..._current]); },
    unsubscribe(fn) { _subs = _subs.filter(s => s !== fn); },
  };
})();
