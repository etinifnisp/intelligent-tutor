import { useState, useEffect, useRef } from 'react';
import { API, WS, renderMarkdown } from '../utils.jsx';

// ── QuestionsPage ──────────────────────────────────────────────────────────
// Three-panel layout:
//   Left  (260px): Subject → Chapter tree browser
//   Center(flex:1): Questions list for selected subject+chapter
//   Right  (360px): Chat panel (AI sidebar, like Antigravity IDE)

export default function QuestionsPage({ sessionId }) {
  // ── State ──────────────────────────────────────────────────────────────
  const [chapters, setChapters]           = useState({ Physics: [], Chemistry: [], Mathematics: [] });
  const [expanded, setExpanded]           = useState({ Physics: true, Chemistry: false, Mathematics: false });
  const [selectedSubject, setSelectedSubject] = useState('Physics');
  const [selectedChapter, setSelectedChapter] = useState(null);
  const [questions, setQuestions]         = useState([]);
  const [totalQ, setTotalQ]               = useState(0);
  const [qPage, setQPage]                 = useState(1);
  const [qLoading, setQLoading]           = useState(false);
  const [selectedQ, setSelectedQ]         = useState(null);

  // Chat state
  const [messages, setMessages]   = useState([]);
  const [input, setInput]         = useState('');
  const [sending, setSending]     = useState(false);
  const wsRef                     = useRef(null);
  const chatEndRef                = useRef(null);
  const textareaRef               = useRef(null);
  const activeRef                 = useRef(true);

  const subjectColors = { Physics: '#2563EB', Chemistry: '#7C3AED', Mathematics: '#059669' };

  // ── Boot ───────────────────────────────────────────────────────────────
  useEffect(() => {
    activeRef.current = true;
    // Fetch chapters from backend
    fetch(`${API}/chapters`)
      .then(r => r.json())
      .then(d => {
        setChapters({
          Physics: ['All Chapters', ...(d.Physics || [])],
          Chemistry: ['All Chapters', ...(d.Chemistry || [])],
          Mathematics: ['All Chapters', ...(d.Mathematics || [])]
        });
      })
      .catch(() => {
        // Fallback — extract chapters by querying subjects
        ['Physics','Chemistry','Mathematics'].forEach(subj => {
          fetch(`${API}/questions?subject=${subj}&limit=10000`)
            .then(r => r.json())
            .then(d => {
              const chaps = [...new Set((d.questions || []).map(q => q.chapter).filter(Boolean))].sort();
              setChapters(prev => ({ ...prev, [subj]: ['All Chapters', ...chaps] }));
            }).catch(() => {});
        });
      });
    connectWS();
    return () => {
      activeRef.current = false;
      wsRef.current?.close();
    };
  }, []);

  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

  // ── WebSocket ──────────────────────────────────────────────────────────
  function connectWS() {
    if (!activeRef.current) return;
    const ws = new WebSocket(WS);
    wsRef.current = ws;
    ws.onopen  = () => window.AppLogger.push('info', 'Q-page WS connected');
    ws.onclose = () => {
      setSending(false);
      if (activeRef.current) {
        setTimeout(connectWS, 3000);
      }
    };
    ws.onerror = () => {
      window.AppLogger.push('error', 'Q-page WS error');
      setSending(false);
    };
    ws.onmessage = (e) => {
      const data = JSON.parse(e.data);
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
        setSending(false);
      } else if (data.type === 'error') {
        setMessages(m => [...m, { role: 'ai', text: `Error: ${data.message}` }]);
        setSending(false);
      } else if (data.type === 'pipeline_step') {
        window.PipelineBus.push({ step: data.step, data: data.data });
      }
    };
  }

  // ── Load questions when chapter selected ───────────────────────────────
  useEffect(() => {
    if (!selectedChapter) return;
    setQLoading(true);
    setQuestions([]);
    const params = new URLSearchParams({ subject: selectedSubject, chapter: selectedChapter, page: qPage, limit: 10000 });
    fetch(`${API}/questions?${params}`)
      .then(r => r.json())
      .then(d => {
        setQuestions(d.questions || []);
        setTotalQ(d.total_matches || 0);
        setQLoading(false);
      }).catch(() => setQLoading(false));
  }, [selectedSubject, selectedChapter, qPage]);

  // ── Chapter selection ──────────────────────────────────────────────────
  function selectChapter(subj, ch) {
    setSelectedSubject(subj);
    setSelectedChapter(ch);
    setQPage(1);
    setSelectedQ(null);
  }

  // ── Question click → send as context ─────────────────────────────────
  function openQuestion(q) {
    setSelectedQ(q);
    const text = `Please help me solve this question:\n\n${q.raw_text}`;
    sendMessage(text, q);
  }

  // ── Send chat message ──────────────────────────────────────────────────
  function sendMessage(text, qOverride) {
    const msg = text || input;
    if (!msg.trim() || sending || !wsRef.current) return;
    
    if (wsRef.current.readyState !== WebSocket.OPEN) {
      window.AppLogger.push('warn', 'WebSocket is not open yet. Retrying...');
      return;
    }

    const history = messages.filter(m => m.role === 'user' || m.role === 'ai')
      .slice(-6).map(m => ({ role: m.role === 'user' ? 'user' : 'model', content: m.text }));
    window.PipelineBus.newRun();
    setMessages(m => [...m, { role: 'user', text: msg }]);
    setSending(true);

    const activeQ = qOverride || selectedQ;
    const qId = activeQ ? `q_${activeQ.question_number}` : null;

    wsRef.current.send(JSON.stringify({
      session_id: sessionId,
      student_message: msg,
      question_id: qId,
      chapter_context: selectedChapter ? `${selectedSubject}: ${selectedChapter}` : null,
      chat_history: history,
    }));
    if (!text) {
      setInput('');
      if (textareaRef.current) textareaRef.current.style.height = 'auto';
    }
  }

  function handleKey(e) { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); } }
  function autoResize(e) { e.target.style.height = 'auto'; e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px'; }

  const totalPages = Math.ceil(totalQ / 20);

  // ── Render ─────────────────────────────────────────────────────────────
  return (
    <div id="questions-page">

      {/* ── LEFT: Subject/Chapter Tree ──────────────────────────────── */}
      <div className="subjects-tree">
        <div className="tree-header">Subjects</div>
        {['Physics','Chemistry','Mathematics'].map(subj => {
          const color   = subjectColors[subj];
          const subjChaps = chapters[subj] || [];
          const isOpen  = expanded[subj];
          return (
            <div key={subj}>
              {/* Subject row */}
              <div
                className={`subject-tree-row ${selectedSubject === subj && !selectedChapter ? 'selected' : ''}`}
                onClick={() => setExpanded(e => ({ ...e, [subj]: !e[subj] }))}
              >
                <span className="subject-tree-chevron" style={{ transform: isOpen ? 'rotate(90deg)' : '' }}>›</span>
                <span className="subject-tree-name" style={{ color }}>{subj}</span>
                <span className="subject-tree-count">{subjChaps.length}</span>
              </div>
              {/* Chapter list */}
              {isOpen && (
                <div className="chapter-tree-list">
                  {subjChaps.length === 0 ? (
                    <div className="tree-loading">Loading...</div>
                  ) : subjChaps.map(ch => (
                    <div
                      key={ch}
                      className={`chapter-tree-item ${selectedSubject === subj && selectedChapter === ch ? 'selected' : ''}`}
                      style={selectedSubject === subj && selectedChapter === ch ? { borderLeft: `2px solid ${color}`, color } : {}}
                      onClick={() => selectChapter(subj, ch)}
                    >
                      {ch}
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* ── CENTER: Questions List ──────────────────────────────────── */}
      <div className="questions-center">
        {!selectedChapter ? (
          <div className="questions-empty">
            <div className="questions-empty-title">Select a chapter</div>
            <div className="questions-empty-sub">Choose a subject and chapter from the left panel to browse questions.</div>
          </div>
        ) : (
          <>
            <div className="questions-center-header">
              <div>
                <div className="qc-chapter">{selectedChapter}</div>
                <div className="qc-meta">
                  {selectedSubject} · {totalQ} questions
                </div>
              </div>
              {totalPages > 1 && (
                <div className="q-pagination">
                  <button className="btn btn-ghost" disabled={qPage === 1} onClick={() => setQPage(p => p - 1)}>Prev</button>
                  <span className="q-page-info">{qPage} / {totalPages}</span>
                  <button className="btn btn-ghost" disabled={qPage === totalPages} onClick={() => setQPage(p => p + 1)}>Next</button>
                </div>
              )}
            </div>

            <div className="questions-list-body">
              {qLoading ? (
                <div style={{ display: 'flex', justifyContent: 'center', padding: 40 }}>
                  <div className="spinner"/>
                </div>
              ) : questions.map((q, i) => (
                <div
                  key={q.question_number || i}
                  className={`question-card ${selectedQ?.question_number === q.question_number ? 'selected' : ''}`}
                  onClick={() => openQuestion(q)}
                >
                  <div className="qcard-top">
                    <span className="qcard-num">Q{q.question_number}</span>
                    <span className={`badge badge-${(q.difficulty||'').toLowerCase()}`}>{q.difficulty || 'N/A'}</span>
                    <span className="qcard-year">{q.year} {q.exam_type?.replace('_',' ')}</span>
                  </div>
                  <div className="qcard-text" dangerouslySetInnerHTML={renderMarkdown(q.raw_text.replace(/^Question:\s*/i, ''))} />

                  {q.images && q.images.length > 0 && (
                    <div className="qcard-images" style={{ marginTop: 12, display: 'flex', flexDirection: 'column', gap: 10 }}>
                      {q.images.map((imgUrl, imgIdx) => (
                        <img key={imgIdx} src={imgUrl} alt={`Figure for Q${q.question_number}`} style={{ maxWidth: '100%', borderRadius: 6, border: '1px solid var(--border)' }} />
                      ))}
                    </div>
                  )}

                  <div className="qcard-topic">{q.topic}</div>
                </div>
              ))}
            </div>
          </>
        )}
      </div>

      {/* ── RIGHT: Chat Panel ───────────────────────────────────────── */}
      <div className="chat-panel">
        <div className="chat-panel-header">
          <div className="chat-panel-title">AI Tutor</div>
          {selectedChapter && (
            <span className="chat-panel-context">
              {selectedSubject} · {selectedChapter}
            </span>
          )}
        </div>

        <div className="chat-panel-messages" ref={chatEndRef}>
          {messages.length === 0 ? (
            <div className="chat-panel-empty">
              Click a question to discuss it, or type below.
            </div>
          ) : (
            messages.map((m, i) => {
              if (m.role === 'status') return null;
              if (m.role === 'user') return (
                <div key={i} className="panel-msg panel-msg-user">{m.text}</div>
              );
              return (
                <div key={i} className="panel-msg panel-msg-ai">
                  <span dangerouslySetInnerHTML={renderMarkdown(m.text)}/>
                  {m.role === 'streaming' && <span className="typing-cursor"/>}
                </div>
              );
            })
          )}
          <div ref={chatEndRef}/>
        </div>

        <div className="chat-panel-input">
          <div className="chat-input-inner">
            <textarea
              id="qpage-chat-textarea"
              ref={textareaRef}
              className="chat-input-textarea"
              rows={1}
              placeholder="Ask about this chapter..."
              value={input}
              onChange={e => { setInput(e.target.value); autoResize(e); }}
              onKeyDown={handleKey}
              disabled={sending}
            />
            <button
              id="qpage-send-btn"
              className="chat-send-btn"
              onClick={() => sendMessage()}
              disabled={sending || !input.trim()}
            >
              <svg viewBox="0 0 24 24"><path d="M22 2L11 13M22 2L15 22 11 13 2 9l20-7z" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round"/></svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
