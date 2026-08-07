import { useState, useEffect, useRef } from 'react';
import ChatMessageContent from './ChatMessageContent.jsx';
import { scrollChatToBottom } from '../chatScroll.js';
import { useTutorSocket } from '../hooks/useTutorSocket.js';

export default function ChatPage({ user }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput]       = useState('');
  const [questionContext, setQuestionContext] = useState('');

  const messagesRef = useRef(null);
  const textareaRef = useRef(null);
  const { connected, sending, send } = useTutorSocket(user?.id);

  useEffect(() => { scrollChatToBottom(messagesRef.current); }, [messages]);

  function handleTutorEvent(data) {
    if (data.type === 'token') {
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
    } else if (data.type === 'tutor_meta') {
      const meta = data.data || {};
      setMessages(m => [...m, {
        role: 'meta',
        verification: meta.verification_status,
        hintLevel: meta.hint_level,
        concept: meta.active_concept,
      }]);
    } else if (data.type === 'error') {
      setMessages(m => [...m, { role: 'ai', text: `Error: ${data.message}` }]);
    } else if (data.type === 'pipeline_step') {
      window.PipelineBus.push({ step: data.step, data: data.data });
      window.AppLogger?.push('info', `Pipeline: ${data.step}`);
    }
  }

  function sendMessage() {
    if (!input.trim() || sending) return;
    const history = messages.filter(m => m.role === 'user' || m.role === 'ai')
      .slice(-6).map(m => ({ role: m.role === 'user' ? 'user' : 'model', content: m.text }));
    window.PipelineBus.newRun();
    setMessages(m => [...m, { role: 'user', text: input }]);
    const payload = {
      student_message: input,
      chat_history: history,
      question_id: null,
      chapter_context: questionContext || null,
    };
    setInput('');
    if (textareaRef.current) textareaRef.current.style.height = 'auto';
    send(payload, handleTutorEvent);
  }

  function handleKey(e) { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); } }
  function autoResize(e) { e.target.style.height = 'auto'; e.target.style.height = Math.min(e.target.scrollHeight, 160) + 'px'; }
  function clearChat() { setMessages([]); window.PipelineBus.newRun(); }

  const suggestions = [
    'Show me how to approach a Newton\'s Laws problem',
    'Help me reason through the difference between NaOH and KOH',
    'Guide me through deriving kinetic energy one step at a time',
    'Check my working: $F = ma$ when mass is 2 kg and $a = 5\\,\\text{m/s}^2$',
  ];

  return (
    <div id="chat-view">
      <div className="chat-header">
        <div>
          <div className="chat-header-chapter">Ask Tutor</div>
          <div className="chat-header-subject">
            {connected ? 'Method-first guidance that keeps the final answer hidden' : 'Reconnecting to tutor…'}
          </div>
        </div>
        <div className="chat-header-actions">
          {messages.length > 0 && (
            <button className="btn btn-ghost" onClick={clearChat} id="clear-chat-btn">New Chat</button>
          )}
        </div>
      </div>

      <div className="tutor-context-bar">
        <input
          type="text"
          className="context-input"
          placeholder="Optional context — e.g. Physics: Work Energy Theorem"
          value={questionContext}
          onChange={e => setQuestionContext(e.target.value)}
        />
      </div>

      <div className="chat-messages" ref={messagesRef}>
        {messages.length === 0 ? (
          <div className="chat-empty">
            <div className="chat-empty-icon">
              <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="var(--accent)"
                strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 2L2 7l10 5 10-5-10-5z"/>
                <path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/>
              </svg>
            </div>
            <div className="chat-empty-title">What would you like to learn?</div>
            <div className="chat-empty-sub">
              Ask how to approach a problem or paste your working. The tutor explains how and why one step at a time, then lets you continue.
            </div>
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
            if (m.role === 'meta') return (
              <div key={i} className="msg-meta-row">
                {m.verification && (
                  <span className={`verification-badge ${m.verification.toLowerCase()}`}>{m.verification}</span>
                )}
                {m.hintLevel > 0 && <span className="msg-status-pill">Hint level {m.hintLevel}</span>}
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
                  <ChatMessageContent text={m.text} streaming={m.role === 'streaming'} />
                  {m.role === 'streaming' && <span className="typing-cursor"/>}
                </div>
              </div>
            );
          })
        )}
      </div>

      <div className="chat-input-bar">
        <div className="chat-input-inner">
          <textarea
            id="chat-textarea"
            ref={textareaRef}
            className="chat-input-textarea"
            rows={1}
            placeholder="Ask how to solve a JEE problem or paste your working…"
            value={input}
            onChange={e => { setInput(e.target.value); autoResize(e); }}
            onKeyDown={handleKey}
            disabled={sending || !connected}
          />
          <button id="chat-send-btn" className="chat-send-btn" onClick={sendMessage}
            disabled={sending || !connected || !input.trim()} title="Send (Enter)">
            {sending
              ? <svg viewBox="0 0 24 24" width="16" height="16"><circle cx="12" cy="12" r="3" fill="currentColor"/></svg>
              : <svg viewBox="0 0 24 24"><path d="M22 2L11 13M22 2L15 22 11 13 2 9l20-7z" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round"/></svg>
            }
          </button>
        </div>
        <div className="chat-input-hint">Enter to send · Shift+Enter for new line · Supports $LaTeX$ formulas</div>
      </div>
    </div>
  );
}
