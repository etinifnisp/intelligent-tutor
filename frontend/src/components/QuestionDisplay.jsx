import { renderMarkdown } from '../utils.jsx';
import { parseQuestionContent, getQuestionImages } from '../questionContent.js';

export default function QuestionDisplay({
  question,
  compact = false,
  practiceMode = false,
  revealAnswer = false,
  revealSolutionSteps = [],
}) {
  if (!question) return null;

  const parsed = parseQuestionContent(question, {
    includeAnswer: !practiceMode || revealAnswer,
    includeSolution: revealSolutionSteps.length > 0,
  });

  const images = getQuestionImages(question);
  const showAnswer = revealAnswer && parsed.correctAnswer;

  return (
    <div className={`question-display ${compact ? 'compact' : ''}`}>
      <div className="qd-meta">
        {question.subject && (
          <span className="badge" style={{ background: 'var(--accent-soft)', color: 'var(--accent)' }}>
            {question.subject}
          </span>
        )}
        {question.chapter && <span className="qd-chapter">{question.chapter}</span>}
        {question.difficulty && (
          <span className={`badge badge-${(question.difficulty || '').toLowerCase()}`}>
            {question.difficulty}
          </span>
        )}
        {question.year && (
          <span className="qd-year">{question.year} {question.exam_type?.replace('_', ' ')}</span>
        )}
        {practiceMode && !revealAnswer && (
          <span className="badge badge-practice">Answer hidden</span>
        )}
      </div>

      {parsed.stem ? (
        <div
          className="qd-text"
          dangerouslySetInnerHTML={renderMarkdown(parsed.stem)}
        />
      ) : (
        <p className="qd-empty">Question text unavailable for this item.</p>
      )}

      {images.length > 0 && (
        <div className="qd-images">
          {images.map((url, i) => (
            <figure key={url} className="qd-figure">
              <img src={url} alt={`Diagram ${i + 1}`} className="qd-diagram" loading="lazy" />
              <figcaption>Figure {i + 1}</figcaption>
            </figure>
          ))}
        </div>
      )}

      {parsed.options.length > 0 && (
        <div className="qd-options" role="list" aria-label="Answer choices">
          {parsed.options.map(opt => (
            <div key={opt.label} className="qd-option" role="listitem">
              <span className="qd-option-label">{opt.label}</span>
              <span
                className="qd-option-text"
                dangerouslySetInnerHTML={renderMarkdown(opt.text)}
              />
            </div>
          ))}
        </div>
      )}

      {revealSolutionSteps.length > 0 && parsed.solutionSteps.length > 0 && (
        <div className="qd-solution-steps">
          <h4>Worked solution</h4>
          <ol>
            {parsed.solutionSteps.map((step, i) => (
              revealSolutionSteps.includes(i) && (
                <li
                  key={i}
                  dangerouslySetInnerHTML={renderMarkdown(step)}
                />
              )
            ))}
          </ol>
        </div>
      )}

      {showAnswer && (
        <div className="qd-answer-reveal">
          <strong>Correct answer:</strong>{' '}
          <span dangerouslySetInnerHTML={renderMarkdown(String(parsed.correctAnswer))} />
        </div>
      )}
    </div>
  );
}
