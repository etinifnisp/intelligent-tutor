// ── Shared utility functions ───────────────────────────────────────────────
// These are referenced by multiple page components.

// API / WebSocket base URLs
export const API = 'http://127.0.0.1:8000';
export const WS  = 'ws://127.0.0.1:8000/tutor/chat';

// Returns a colour string representing mastery level 0-1
export function masteryColor(m) {
  if (m === undefined || m === null) return '#94A3B8';
  if (m < 0.4) return '#DC2626';
  if (m < 0.7) return '#D97706';
  return '#059669';
}

// Per-subject accent colours (light-theme calibrated)
export function subjectColor(s) {
  if (s === 'Physics')     return '#2563EB';
  if (s === 'Chemistry')   return '#7C3AED';
  if (s === 'Mathematics') return '#059669';
  return '#6B6880';
}

// Per-subject short text labels (no emoji)
export function subjectIcon(s) {
  if (s === 'Physics')     return 'Phy';
  if (s === 'Chemistry')   return 'Che';
  if (s === 'Mathematics') return 'Mat';
  return 'Gen';
}

// Returns a difficulty badge element (or null)
export function diffBadge(d) {
  if (!d) return null;
  const cls = d === 'Easy' ? 'badge-easy' : d === 'Hard' ? 'badge-hard' : 'badge-medium';
  return <span className={`badge ${cls}`}>{d}</span>;
}

// Minimal Markdown -> HTML renderer (bold, italic, code, code-blocks, newlines, KaTeX)
export function renderMarkdown(text) {
  let html = text
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/\$\$([\s\S]*?)\$\$/g, (match, math) => {
       try { return window.katex ? window.katex.renderToString(math.replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>'), { displayMode: true, throwOnError: false }) : match; }
       catch(e) { return match; }
    })
    .replace(/\\\[([\s\S]*?)\\\]/g, (match, math) => {
       try { return window.katex ? window.katex.renderToString(math.replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>'), { displayMode: true, throwOnError: false }) : match; }
       catch(e) { return match; }
    })
    .replace(/\$([^$]+)\$/g, (match, math) => {
       try { return window.katex ? window.katex.renderToString(math.replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>'), { displayMode: false, throwOnError: false }) : match; }
       catch(e) { return match; }
    })
    .replace(/\\\(([\s\S]*?)\\\)/g, (match, math) => {
       try { return window.katex ? window.katex.renderToString(math.replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>'), { displayMode: false, throwOnError: false }) : match; }
       catch(e) { return match; }
    })
    .replace(/```([\s\S]*?)```/g, '<pre>$1</pre>')
    .replace(/!\[([^\]]*)\]\(([^)]+)\)/g, '<img src="$2" alt="$1" style="max-width:100%; border-radius:4px; margin-top:8px;" />')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`([^`]+)`/g, '<code style="background:var(--bg-panel);border:1px solid var(--border);padding:1px 6px;border-radius:4px;font-family:JetBrains Mono,monospace;font-size:12px">$1</code>')
    .replace(/\n{2,}/g, '__DOUBLE_NEWLINE__')
    .replace(/\n/g, ' ')
    .replace(/__DOUBLE_NEWLINE__/g, '<br/><br/>');
  return { __html: html };
}
