import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import {
  API, apiFetch, authFetch, confidenceValue, questionId,
} from '../utils.jsx';
import { parseQuestionContent, SOLUTION_STEPS } from '../questionContent.js';
import { isLearningStepDisabled } from '../learningSteps.js';
import { useTutorSocket } from '../hooks/useTutorSocket.js';
import QuestionDisplay from './QuestionDisplay.jsx';
import ChatMessageContent from './ChatMessageContent.jsx';
import LoadingState from './LoadingState.jsx';
import ErrorState from './ErrorState.jsx';
import { saveLastSession } from '../lastSession.js';

const CONFIDENCE_LABELS = ['Not sure', 'Low', 'Medium', 'High', 'Very confident'];
const HINT_MESSAGES = [
  'Can I get a hint?',
  'I need another hint — what formula should I use?',
  'Still stuck — can you show me the setup without the final answer?',
  'Please show the full solution.',
];

export default function PracticePage({ user }) {
  const [mode, setMode] = useState('adaptive');
  const [subject, setSubject] = useState('');
  const [chapter, setChapter] = useState('');
  const [difficulty, setDifficulty] = useState('');
  const [chapters, setChapters] = useState({ Physics: [], Chemistry: [], Mathematics: [] });
  const [question, setQuestion] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [answer, setAnswer] = useState('');
  const [confidenceIdx, setConfidenceIdx] = useState(2);
  const [hintLevel, setHintLevel] = useState(0);
  const [feedback, setFeedback] = useState(null);
  const [tutorReply, setTutorReply] = useState('');
  const [attempts, setAttempts] = useState(0);
  const [timerSec, setTimerSec] = useState(0);
  const [timedMode, setTimedMode] = useState(false);
  const [revealAnswer, setRevealAnswer] = useState(false);
  const [revealedStepCount, setRevealedStepCount] = useState(0);
  const [similarQuestions, setSimilarQuestions] = useState([]);
  const [similarLoading, setSimilarLoading] = useState(false);
  const [similarExpanded, setSimilarExpanded] = useState({});
  const startRef = useRef(null);
  const { connected, sending, send } = useTutorSocket(user?.id);

  const parsedQuestion = useMemo(
    () => (question ? parseQuestionContent(question, { includeSolution: true }) : null),
    [question],
  );

  const mcqOptions = useMemo(() => {
    if (parsedQuestion?.options?.length === 4) {
      return parsedQuestion.options.map(o => o.label);
    }
    return [];
  }, [parsedQuestion]);

  const solutionStepIndices = useMemo(() => {
    if (!parsedQuestion?.solutionSteps?.length) return [];
    return Array.from({ length: Math.min(revealedStepCount, parsedQuestion.solutionSteps.length) }, (_, i) => i);
  }, [parsedQuestion, revealedStepCount]);

  useEffect(() => {
    apiFetch('/chapters').then(r => r.json()).then(setChapters).catch(() => {});
  }, []);

  function pickQuestionFromRecommendations(recommendations) {
    const withQuestions = (recommendations || []).filter(rec => rec?.question && (
      rec.question.raw_text || rec.question.stem_text || rec.question.normalized_text
    ));
    if (!withQuestions.length) return null;
    const rec = withQuestions[Math.floor(Math.random() * withQuestions.length)];
    return rec.question;
  }

  function hasQuestionText(q) {
    return Boolean(q?.raw_text || q?.stem_text || q?.normalized_text || q?.question_text);
  }

  useEffect(() => {
    if (!timedMode) return;
    const t = setInterval(() => setTimerSec(s => s + 1), 1000);
    return () => clearInterval(t);
  }, [timedMode]);

  const loadQuestion = useCallback(() => {
    setLoading(true);
    setError(null);
    setAnswer('');
    setFeedback(null);
    setTutorReply('');
    setHintLevel(0);
    setRevealAnswer(false);
    setRevealedStepCount(0);
    startRef.current = Date.now();

    if (mode === 'adaptive') {
      const params = new URLSearchParams({ limit: '10' });
      if (subject) params.set('subject', subject);
      authFetch(`/learning/next-question?${params}`)
        .then(r => {
          if (!r.ok) throw new Error('Could not load adaptive question');
          return r.json();
        })
        .then(d => {
          const q = pickQuestionFromRecommendations(d.recommendations);
          if (!q) throw new Error('No questions available for adaptive practice');
          setQuestion(q);
          setAttempts(0);
          saveLastSession({
            subject: q.subject,
            chapter: q.chapter,
            questionId: questionId(q),
            mode: 'adaptive',
          });
        })
        .catch(e => setError(e.message))
        .finally(() => setLoading(false));
      return;
    }

    const params = new URLSearchParams({ limit: '200', practice_ready: 'true' });
    if (subject) params.set('subject', subject);
    if (chapter) params.set('chapter', chapter);
    fetch(`${API}/questions?${params}`)
      .then(r => r.json())
      .then(d => {
        let pool = d.questions || [];
        if (difficulty) {
          pool = pool.filter(q => (q.difficulty || '').toLowerCase() === difficulty.toLowerCase());
        }
        if (!pool.length) throw new Error('No questions match your filters');
        const q = pool[Math.floor(Math.random() * pool.length)];
        if (!hasQuestionText(q)) throw new Error('Selected question has no displayable text');
        setQuestion(q);
        setAttempts(0);
        saveLastSession({
          subject: q.subject,
          chapter: q.chapter,
          questionId: questionId(q),
          mode: 'practice',
        });
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [mode, subject, chapter, difficulty]);

  useEffect(() => { loadQuestion(); }, [loadQuestion]);

  // Fetch similar PYQs once the answer is revealed
  useEffect(() => {
    if (!revealAnswer || !question) return;
    const qid = questionId(question);
    if (!qid) return;
    setSimilarQuestions([]);
    setSimilarExpanded({});
    setSimilarLoading(true);
    authFetch(`/questions/${encodeURIComponent(qid)}/similar?top_k=3`)
      .then(r => r.json())
      .then(d => setSimilarQuestions(d.results || []))
      .catch(() => setSimilarQuestions([]))
      .finally(() => setSimilarLoading(false));
  }, [revealAnswer, question]);

  function handleTutorEvent(data) {
    if (data.type === 'token') {
      setTutorReply(prev => prev + (data.text || ''));
    } else if (data.type === 'tutor_meta') {
      const meta = data.data || {};
      setFeedback({
        verification: meta.verification_status,
        hintLevel: meta.hint_level,
        intent: meta.intent,
        pedagogy: meta.pedagogy_mode,
      });
      if (meta.hint_level) setHintLevel(meta.hint_level);
      if (meta.hint_level >= 4) setRevealAnswer(true);
      if (meta.verification_status) setRevealAnswer(true);
    } else if (data.type === 'pipeline_step' && data.step === 'mastery_update') {
      setFeedback(prev => ({ ...prev, mastery: data.data }));
    } else if (data.type === 'error') {
      setError(data.message);
    }
  }

  function submitAnswer(ans) {
    if (!question || sending) return;
    const msg = ans || answer;
    if (!msg.trim()) return;
    const elapsed = startRef.current ? Date.now() - startRef.current : null;
    setTutorReply('');
    setFeedback(null);
    setAttempts(a => a + 1);

    send({
      student_message: msg.trim().startsWith('option') ? msg : `My answer: ${msg}`,
      question_id: questionId(question),
      chapter_context: question.chapter ? `${question.subject}: ${question.chapter}` : null,
      chat_history: [],
      confidence_before: confidenceValue(confidenceIdx),
      response_time_ms: elapsed,
    }, handleTutorEvent);
  }

  function revealLocalStep(stepIndex) {
    if (!question || sending) return;
    const totalSteps = parsedQuestion?.solutionSteps?.length || 0;
    const perHint = totalSteps > 0 ? Math.max(1, Math.ceil(totalSteps / 4)) : 0;

    setHintLevel(stepIndex + 1);
    if (totalSteps > 0) {
      setRevealedStepCount(prev => Math.min(totalSteps, Math.max(prev, (stepIndex + 1) * perHint)));
    }
    if (stepIndex >= 3) setRevealAnswer(true);

    const idx = Math.min(stepIndex, HINT_MESSAGES.length - 1);
    setTutorReply('');
    setFeedback(null);
    send({
      student_message: HINT_MESSAGES[idx],
      question_id: questionId(question),
      chapter_context: question.chapter ? `${question.subject}: ${question.chapter}` : null,
      chat_history: [],
    }, handleTutorEvent);
  }

  function selectOption(opt) {
    setAnswer(`option ${opt}`);
    setFeedback(null);
    setTutorReply('');
  }

  const selectedOption = answer.startsWith('option ') ? answer.slice(7) : '';

  return (
    <div id="page-practice" className="page active student-page">
      <header className="page-header">
        <div>
          <h1>PYQ Practice</h1>
          <p className="page-subtitle">
            {connected ? 'AI tutor connected' : 'Reconnecting…'}
            {timedMode && ` · ${Math.floor(timerSec / 60)}:${String(timerSec % 60).padStart(2, '0')}`}
          </p>
        </div>
        <div className="practice-header-actions">
          <label className="toggle-label">
            <input type="checkbox" checked={timedMode} onChange={e => {
              setTimedMode(e.target.checked);
              setTimerSec(0);
            }} />
            Timed mode
          </label>
        </div>
      </header>

      <div className="practice-toolbar card">
        <div className="practice-toolbar-intro">
          <span>Question source</span>
          <strong>Verified previous-year papers</strong>
        </div>
        <select value={mode} onChange={e => setMode(e.target.value)} className="filter-select">
          <option value="adaptive">Adaptive PYQs</option>
          <option value="practice">Browse PYQs</option>
        </select>
        <select value={subject} onChange={e => setSubject(e.target.value)} className="filter-select">
          <option value="">All subjects</option>
          <option value="Physics">Physics</option>
          <option value="Chemistry">Chemistry</option>
          <option value="Mathematics">Mathematics</option>
        </select>
        {mode === 'practice' && (
          <>
            <select value={chapter} onChange={e => setChapter(e.target.value)} className="filter-select">
              <option value="">All chapters</option>
              {(chapters[subject] || []).map(c => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
            <select value={difficulty} onChange={e => setDifficulty(e.target.value)} className="filter-select">
              <option value="">Any difficulty</option>
              <option value="Easy">Easy</option>
              <option value="Medium">Medium</option>
              <option value="Hard">Hard</option>
            </select>
          </>
        )}
        <button className="btn btn-secondary" onClick={loadQuestion} disabled={loading}>
          New question
        </button>
      </div>

      {loading && <LoadingState message="Loading a previous-year question…" />}
      {error && !loading && <ErrorState message={error} onRetry={loadQuestion} />}

      {!loading && question && (
        <div className="practice-workspace">
          <div className="practice-question card">
            <QuestionDisplay
              question={question}
              practiceMode
              revealAnswer={revealAnswer}
              revealSolutionSteps={solutionStepIndices}
              selectedOption={selectedOption}
              onSelectOption={selectOption}
              disabled={sending || revealAnswer}
            />
            <section className="practice-learning-help" aria-labelledby="step-help-title">
              <div className="learning-help-header">
                <div className="learning-help-icon">01</div>
                <div>
                  <span className="learning-help-kicker">Guided learning</span>
                  <h2 id="step-help-title">Step-by-step help</h2>
                  <p>Reveal only what you need. Work from the core concept toward the complete solution.</p>
                </div>
              </div>

              <div className="solution-stepper learning-stepper">
                {SOLUTION_STEPS.map((step, idx) => (
                  <button
                    key={step.id}
                    className={`solution-step-btn ${hintLevel > idx ? 'revealed' : ''} ${hintLevel === idx ? 'next' : ''}`}
                    onClick={() => revealLocalStep(idx)}
                    disabled={isLearningStepDisabled({ sending, stepIndex: idx, hintLevel })}
                    title={step.description}
                  >
                    <span className="solution-step-num">{hintLevel > idx ? '✓' : idx + 1}</span>
                    <span className="solution-step-copy">
                      <strong>{step.label}</strong>
                      <small>{step.description}</small>
                    </span>
                  </button>
                ))}
              </div>

              {sending && hintLevel > 0 && (
                <div className="learning-help-loading"><span className="spinner"/>Preparing the next learning step…</div>
              )}

              {(feedback || tutorReply) && (
                <div className="practice-feedback learning-feedback">
                  <div className="learning-feedback-label">
                    <span>AI tutor explanation</span>
                    {feedback?.verification && (
                      <span className={`verification-badge ${feedback.verification.toLowerCase()}`}>
                        {feedback.verification}
                      </span>
                    )}
                  </div>
                  {feedback?.mastery && <div className="mastery-update-pill">Mastery updated</div>}
                  {tutorReply && (
                    <div className="tutor-feedback-text">
                      <ChatMessageContent text={tutorReply} />
                    </div>
                  )}
                </div>
              )}

              {!tutorReply && !sending && (
                <p className="learning-help-note">Start with Concept for a small nudge. The correct answer stays hidden until you submit or reach the full solution.</p>
              )}
            </section>

            {revealAnswer && (
              <section className="similar-pyqs-section" aria-labelledby="similar-pyqs-title">
                <div className="similar-pyqs-header">
                  <div className="similar-pyqs-icon">📚</div>
                  <div>
                    <span className="similar-pyqs-kicker">Reinforce your understanding</span>
                    <h2 id="similar-pyqs-title">Similar PYQs from Previous Years</h2>
                    <p>Practice these related questions from past JEE papers to solidify the concept.</p>
                  </div>
                </div>

                {similarLoading && (
                  <div className="similar-pyqs-loading">
                    <span className="spinner" />
                    Finding similar previous-year questions…
                  </div>
                )}

                {!similarLoading && similarQuestions.length === 0 && (
                  <p className="similar-pyqs-empty">No similar questions found in the index for this topic.</p>
                )}

                {!similarLoading && similarQuestions.length > 0 && (
                  <div className="similar-pyqs-list">
                    {similarQuestions.map((sq, i) => {
                      const isOpen = !!similarExpanded[i];
                      const diffCls = sq.difficulty === 'Easy' ? 'badge-easy' : sq.difficulty === 'Hard' ? 'badge-hard' : 'badge-medium';
                      return (
                        <div key={sq.question_id || i} className={`similar-pyq-card ${isOpen ? 'open' : ''}`}>
                          <button
                            className="similar-pyq-header"
                            onClick={() => setSimilarExpanded(prev => ({ ...prev, [i]: !isOpen }))}
                            aria-expanded={isOpen}
                          >
                            <div className="similar-pyq-meta">
                              {sq.year && <span className="similar-pyq-year">{sq.year}</span>}
                              {sq.exam_type && <span className="similar-pyq-exam">{sq.exam_type}</span>}
                              {sq.topic && <span className="similar-pyq-topic">{sq.topic}</span>}
                              {sq.difficulty && <span className={`badge ${diffCls}`}>{sq.difficulty}</span>}
                            </div>
                            <div className="similar-pyq-stem">
                              {(sq.stem_text || '').slice(0, 180)}{sq.stem_text?.length > 180 ? '…' : ''}
                            </div>
                            <span className="similar-pyq-chevron" aria-hidden="true">{isOpen ? '▲' : '▼'}</span>
                          </button>

                          {isOpen && (
                            <div className="similar-pyq-body">
                              <p className="similar-pyq-full-stem">{sq.stem_text}</p>
                              {sq.options?.length === 4 && (
                                <div className="similar-pyq-options">
                                  {sq.options.map(opt => (
                                    <div
                                      key={opt.label}
                                      className={`similar-pyq-option ${
                                        sq.correct_answer === opt.label ? 'correct' : ''
                                      }`}
                                    >
                                      <span className="similar-pyq-option-label">{opt.label}</span>
                                      <span>{opt.text}</span>
                                    </div>
                                  ))}
                                </div>
                              )}
                              {sq.correct_answer && (
                                <p className="similar-pyq-answer">
                                  ✅ Correct answer: <strong>{sq.correct_answer}</strong>
                                </p>
                              )}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </section>
            )}
          </div>

          <div className="practice-panel card">
            <div className="confidence-block">
              <label>How confident are you?</label>
              <div className="confidence-slider-row">
                <input
                  type="range"
                  min={0}
                  max={4}
                  value={confidenceIdx}
                  onChange={e => setConfidenceIdx(Number(e.target.value))}
                  className="confidence-slider"
                />
                <span className="confidence-label">{CONFIDENCE_LABELS[confidenceIdx]}</span>
              </div>
            </div>

            <div className="answer-block">
              <label>{mcqOptions.length === 4 ? 'Your selected answer' : 'Your answer'}</label>
              {mcqOptions.length === 4 && (
                <div className={`selected-answer ${selectedOption ? 'has-value' : ''}`}>
                  <span>{selectedOption || '—'}</span>
                  <p>{selectedOption ? `Option ${selectedOption} selected` : 'Choose one option from the question'}</p>
                </div>
              )}
              {mcqOptions.length !== 4 && (
                <textarea
                  className="answer-input"
                  rows={3}
                  placeholder="Type your answer or working…"
                  value={answer}
                  onChange={e => setAnswer(e.target.value)}
                  disabled={sending}
                />
              )}
              <button
                className="btn btn-primary submit-attempt-btn"
                onClick={() => submitAnswer()}
                disabled={sending || !answer.trim()}
              >
                {sending ? 'Checking…' : 'Check answer'}
              </button>
            </div>

            <div className="practice-actions">
              <button className="btn btn-secondary" onClick={loadQuestion} disabled={loading}>
                Next question
              </button>
              <button
                className="btn btn-ghost"
                onClick={() => {
                  setAnswer('');
                  setFeedback(null);
                  setTutorReply('');
                  setHintLevel(0);
                  setRevealAnswer(false);
                  setRevealedStepCount(0);
                  startRef.current = Date.now();
                }}
              >
                Retry question
              </button>
            </div>
            <p className="attempt-count">Attempts this question: {attempts}</p>
          </div>
        </div>
      )}
    </div>
  );
}
