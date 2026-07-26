import { useState, useEffect, useRef } from 'react';
import { WS, renderMarkdown } from '../utils.jsx';

// ── ChatPage ──────────────────────────────────────────────────────────────
// Default landing page: a full-screen, ChatGPT-style AI chat.
// Works on any JEE topic — no chapter selection required.

export default function ChatPage({ sessionId }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput]       = useState('');
  const [sending, setSending]   = useState(false);

  const wsRef       = useRef(null);
  const chatEndRef  = useRef(null);
  const textareaRef = useRef(null);

  useEffect(() => { connectWS(); return () => wsRef.current?.close(); }, []);
  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

  function connectWS() {
    const ws = new WebSocket(WS);
    wsRef.current = ws;
    ws.onopen  = () => window.AppLogger.push('info', 'WebSocket connected');
    ws.onclose = () => {
      window.AppLogger.push('warn', 'WS disconnected — reconnecting in 3s');
      setTimeout(connectWS, 3000);
    };
    ws.onerror = () => window.AppLogger.push('error', 'WS error');
    ws.onmessage = (e) => {
      const data = JSON.parse(e.data);
      if (data.type === 'status') {
        setMessages(m => [...m, { role: 'status', text: `${data.lane}` }]);
      } else if (data.type === 'token') {
        setMessages(m => {
          const prev = [...m];
          const last = prev[prev.length - 1];
          if (last && last.role === 'streaming') { last.text += data.text; return [...prev]; }
          return [...prev, { role: 'streaming', text: data.text }];
        });
      } else if (data.type === 'done') {
        setMessages(m => {
          const prev = [...m];
          const last = prev[prev.length - 1];
          if (last && last.role === 'streaming') last.role = 'ai';
          return [...prev];
        });
        setSending(false);
      } else if (data.type === 'error') {
        setMessages(m => [...m, { role: 'ai', text: `Error: ${data.message}` }]);
        setSending(false);
      } else if (data.type === 'pipeline_step') {
        window.PipelineBus.push({ step: data.step, data: data.data });
        window.AppLogger.push('info', `Pipeline: ${data.step}`);
      }
    };
  }

  function send() {
    if (!input.trim() || sending || !wsRef.current) return;
    const history = messages.filter(m => m.role === 'user' || m.role === 'ai')
      .slice(-6).map(m => ({ role: m.role === 'user' ? 'user' : 'model', content: m.text }));
    window.PipelineBus.newRun();
    setMessages(m => [...m, { role: 'user', text: input }]);
    setSending(true);
    wsRef.current.send(JSON.stringify({ session_id: sessionId, student_message: input, chat_history: history }));
    setInput('');
    if (textareaRef.current) textareaRef.current.style.height = 'auto';
  }

  function handleKey(e) { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } }
  function autoResize(e) { e.target.style.height = 'auto'; e.target.style.height = Math.min(e.target.scrollHeight, 160) + 'px'; }
  function clearChat() { setMessages([]); window.PipelineBus.newRun(); }

  const suggestions = [
    'Explain Newton\'s Laws of Motion with examples',
    'What is the difference between NaOH and KOH?',
    'Derive the formula for kinetic energy',
    'Solve: If f(x) = x² + 3x + 2, find f\'(x)',
  ];

  return (
    <div id="chat-view">
      {/* Header */}
      <div className="chat-header">
        <div>
          <div className="chat-header-chapter">JEE Intelligent Tutor</div>
          <div className="chat-header-subject">Ask any Physics, Chemistry, or Mathematics question</div>
        </div>
        <div className="chat-header-actions">
          {messages.length > 0 && (
            <button className="btn btn-ghost" onClick={clearChat} id="clear-chat-btn">New Chat</button>
          )}
        </div>
      </div>

      {/* Messages */}
      <div className="chat-messages">
        {messages.length === 0 ? (
          <div className="chat-empty">
            <div className="chat-empty-icon">
              <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="var(--accent)"
                strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 2L2 7l10 5 10-5-10-5z"/>
                <path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/>
              </svg>
            </div>
            <div className="chat-empty-title">What would you like to learn today?</div>
            <div className="chat-empty-sub">Ask a concept, request a derivation, or say "quiz me on Thermodynamics".</div>
            <div className="suggestions-grid">
              {suggestions.map((s, i) => (
                <button key={i} className="suggestion-btn" onClick={() => { setInput(s); textareaRef.current?.focus(); }}>
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((m, i) => {
            if (m.role === 'status') return (
              <div key={i} className="msg-status-row">
                <span className="msg-status-pill">{m.text}</span>
              </div>
            );
            if (m.role === 'user') return (
              <div key={i} className="msg-row user">
                <div className="msg-bubble user">{m.text}</div>
              </div>
            );
            return (
              <div key={i} className="msg-row ai">
                <div className="msg-bubble ai">
                  <span dangerouslySetInnerHTML={renderMarkdown(m.text)}/>
                  {m.role === 'streaming' && <span className="typing-cursor"/>}
                </div>
              </div>
            );
          })
        )}
        <div ref={chatEndRef}/>
      </div>

      {/* Fixed input bar */}
      <div className="chat-input-bar">
        <div className="chat-input-inner">
          <textarea
            id="chat-textarea"
            ref={textareaRef}
            className="chat-input-textarea"
            rows={1}
            placeholder="Ask any JEE question..."
            value={input}
            onChange={e => { setInput(e.target.value); autoResize(e); }}
            onKeyDown={handleKey}
            disabled={sending}
          />
          <button id="chat-send-btn" className="chat-send-btn" onClick={send}
            disabled={sending || !input.trim()} title="Send (Enter)">
            {sending
              ? <svg viewBox="0 0 24 24" width="16" height="16"><circle cx="12" cy="12" r="3" fill="currentColor"/></svg>
              : <svg viewBox="0 0 24 24"><path d="M22 2L11 13M22 2L15 22 11 13 2 9l20-7z" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round"/></svg>
            }
          </button>
        </div>
        <div className="chat-input-hint">Enter to send · Shift+Enter for new line</div>
      </div>
    </div>
  );
}
