// ── Shared utility functions ───────────────────────────────────────────────

import { API, WS_BASE } from './config.js';

export { API, WS_BASE };
const AUTH_TOKEN_KEY = 'jee_tutor_access_token';
const AUTH_EXEMPT_PREFIXES = ['/auth/guest', '/auth/login', '/auth/register', '/auth/refresh', '/health'];

export function setAccessToken(token) {
  if (token) sessionStorage.setItem(AUTH_TOKEN_KEY, token);
  else sessionStorage.removeItem(AUTH_TOKEN_KEY);
}

export function getAccessToken() {
  return sessionStorage.getItem(AUTH_TOKEN_KEY);
}

export async function fetchWithTimeout(url, options = {}, timeoutMs = 15000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } finally {
    clearTimeout(timer);
  }
}

function shouldAttachAuth(path) {
  return !AUTH_EXEMPT_PREFIXES.some((prefix) => path.startsWith(prefix));
}

export async function apiFetch(path, options = {}, timeoutMs = 15000) {
  const headers = new Headers(options.headers || {});
  const token = getAccessToken();
  if (shouldAttachAuth(path) && token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`);
  }
  return fetchWithTimeout(`${API}${path}`, { ...options, headers }, timeoutMs);
}

/** Backward-compatible alias — apiFetch now attaches auth automatically. */
export function authFetch(path, options = {}, timeoutMs = 15000) {
  return apiFetch(path, options, timeoutMs);
}

export async function waitForBackend(maxWaitMs = 60000) {
  const start = Date.now();
  while (Date.now() - start < maxWaitMs) {
    try {
      const response = await fetchWithTimeout(`${API}/health/live`, {}, 3000);
      if (response.ok) return true;
    } catch {
      // Backend still booting or unreachable — retry.
    }
    await new Promise((resolve) => setTimeout(resolve, 1000));
  }
  return false;
}

export async function startGuestSession(retries = 3) {
  const backendReady = await waitForBackend();
  if (!backendReady) {
    throw new Error('Backend is not responding. Start it with `python app.py` in the backend folder.');
  }

  let lastError = null;
  for (let attempt = 0; attempt < retries; attempt += 1) {
    try {
      const response = await apiFetch('/auth/guest', { method: 'POST' }, 15000);
      if (!response.ok) {
        const message = response.status === 429
          ? 'Too many guest sessions from this device. Wait a moment and retry.'
          : 'Could not start a guest session';
        throw new Error(message);
      }
      const session = await response.json();
      setAccessToken(session.access_token);
      return session;
    } catch (error) {
      lastError = error;
      if (attempt < retries - 1) {
        await new Promise((resolve) => setTimeout(resolve, 1000 * (attempt + 1)));
      }
    }
  }
  throw lastError || new Error('Could not start a guest session');
}

export function createTutorSocket() {
  const token = getAccessToken();
  if (!token) return new WebSocket(WS_BASE);
  return new WebSocket(WS_BASE, [`bearer.${token}`]);
}

/** @deprecated Use createTutorSocket — tokens are no longer passed in the URL. */
export function wsUrl() {
  return WS_BASE;
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
