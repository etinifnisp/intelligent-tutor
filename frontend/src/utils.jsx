// ── Shared utility functions ───────────────────────────────────────────────

import { API, WS_BASE } from './config.js';

export { API, WS_BASE };
const AUTH_TOKEN_KEY = 'jee_tutor_access_token';

export function setAccessToken(token) {
  if (token) sessionStorage.setItem(AUTH_TOKEN_KEY, token);
  else sessionStorage.removeItem(AUTH_TOKEN_KEY);
}

export function getAccessToken() {
  return sessionStorage.getItem(AUTH_TOKEN_KEY);
}

export async function apiFetch(path, options = {}) {
  return fetch(`${API}${path}`, options);
}

/** @deprecated Use apiFetch — auth removed; kept for existing imports */
export function authFetch(path, options = {}) {
  const token = getAccessToken();
  const headers = new Headers(options.headers || {});
  if (token) headers.set('Authorization', `Bearer ${token}`);
  return apiFetch(path, { ...options, headers });
}

export function wsUrl() {
  const token = getAccessToken();
  return token ? `${WS_BASE}?token=${encodeURIComponent(token)}` : WS_BASE;
}

// Returns a colour string representing mastery level 0-1
export function masteryColor(m) {
  if (m === undefined || m === null) return '#9CA3AF';
  if (m < 0.4) return '#DC2626';
  if (m < 0.7) return '#D97706';
  return '#16A34A';
}

export function subjectColor(s) {
  if (s === 'Physics')     return '#4F6BF6';
  if (s === 'Chemistry')   return '#7C3AED';
  if (s === 'Mathematics') return '#16A34A';
  return '#6B7280';
}

export function subjectIcon(s) {
  if (s === 'Physics')     return 'Phy';
  if (s === 'Chemistry')   return 'Che';
  if (s === 'Mathematics') return 'Mat';
  return 'Gen';
}

export function diffBadge(d) {
  if (!d) return null;
  const cls = d === 'Easy' ? 'badge-easy' : d === 'Hard' ? 'badge-hard' : 'badge-medium';
  return <span className={`badge ${cls}`}>{d}</span>;
}

export function closeWebSocket(ws) {
  if (!ws) return;
  if (ws.readyState === WebSocket.CONNECTING) {
    ws.addEventListener('open', () => ws.close(), { once: true });
  } else if (ws.readyState === WebSocket.OPEN) {
    ws.close();
  }
}

import { prepareMathText } from './questionContent.js';

export function renderMarkdown(text) {
  if (!text) return { __html: '' };
  let html = prepareMathText(text)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>')
    .replace(/\n/g, '<br/>');
  if (window.katex) {
    html = html.replace(/\$\$(.+?)\$\$/g, (_, tex) => {
      try { return `<div class="math-block">${window.katex.renderToString(tex, { displayMode: true, throwOnError: false })}</div>`; }
      catch { return `$$${tex}$$`; }
    });
    html = html.replace(/\$([^$\n]+?)\$/g, (_, tex) => {
      try { return window.katex.renderToString(tex, { displayMode: false, throwOnError: false }); }
      catch { return `$${tex}$`; }
    });
  }
  return { __html: html };
}

export function questionId(q) {
  if (!q) return null;
  if (q.question_id && String(q.question_id).startsWith('q_')) return q.question_id;
  const num = q.question_number ?? q.legacy_question_number;
  return num != null ? `q_${num}` : q.question_id || null;
}

export function confidenceValue(idx) {
  return [0.2, 0.4, 0.6, 0.8, 1.0][idx] ?? 0.6;
}
