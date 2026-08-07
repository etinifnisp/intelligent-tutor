import { renderMarkdown } from '../utils.jsx';
import { parseQuestionContent, getQuestionImages, prepareMathText } from '../questionContent.js';
import MathText from '../MathText.jsx';

export default function QuestionDisplay({
  question,
  compact = false,
  practiceMode = false,
  revealAnswer = false,
  revealSolutionSteps = [],
  selectedOption = '',
  onSelectOption = null,
  disabled = false,
}) {
  if (!question) return null;

  const parsed = parseQuestionContent(question, {
    includeAnswer: !practiceMode || revealAnswer,
    includeSolution: revealSolutionSteps.length > 0,
  });

  const images = getQuestionImages(question);
  const showAnswer = revealAnswer && parsed.correctAnswer;
  const examLabel = question.exam_type?.replaceAll('_', ' ') || question.source?.exam?.replaceAll('_', ' ');
  const sourceYear = question.year || question.source?.year;

  return (
    <div className={`question-display ${compact ? 'compact' : ''}`}>
      <div className="qd-meta">
        {sourceYear && (
          <span className="qd-source-badge"><i/>PYQ · {examLabel || 'JEE'} · {sourceYear}</span>
        )}
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
        {question.shift && question.shift !== 'N/A' && (
          <span className="qd-year">{question.shift.replaceAll('_', ' ')}</span>
        )}
        {practiceMode && !revealAnswer && (
          <span className="badge badge-practice">Answer hidden</span>
        )}
      </div>

      {parsed.stem ? (
        <div className="qd-text">
          <MathText text={prepareMathText(parsed.stem)} />
        </div>
      ) : (
        <p className="qd-empty">Question text unavailable for this item.</p>
      )}

      {images.length > 0 && (
        <div className="qd-images">
          {images.map((url, i) => (
            <figure key={url} className="qd-figure">
              <img src={url} alt={`Diagram ${i + 1}`} className="qd-diagram" loading="lazy"
                onError={event => { event.currentTarget.closest('figure').hidden = true; }} />
              <figcaption>Figure {i + 1}</figcaption>
            </figure>
          ))}
        </div>
      )}

      {parsed.options.length > 0 && (
        <div className="qd-options" role="list" aria-label="Answer choices">
          {parsed.options.map(opt => {
            const isSelected = selectedOption === opt.label;
            const isCorrect = revealAnswer && parsed.correctAnswer === opt.label;
            const isIncorrect = revealAnswer && isSelected && !isCorrect;
            const OptionTag = onSelectOption ? 'button' : 'div';
            return (
              <OptionTag
                key={opt.label}
                className={`qd-option ${isSelected ? 'selected' : ''} ${isCorrect ? 'correct' : ''} ${isIncorrect ? 'incorrect' : ''}`}
                role={onSelectOption ? undefined : 'listitem'}
                type={onSelectOption ? 'button' : undefined}
                aria-pressed={onSelectOption ? isSelected : undefined}
                disabled={onSelectOption ? disabled : undefined}
                onClick={onSelectOption ? () => onSelectOption(opt.label) : undefined}
              >
                <span className="qd-option-label">{opt.label}</span>
                <span className="qd-option-text">
                  <MathText text={prepareMathText(opt.text)} />
                </span>
                {isCorrect && <span className="qd-option-result">Correct</span>}
              </OptionTag>
            );
          })}
        </div>
      )}

      {revealSolutionSteps.length > 0 && parsed.solutionSteps.length > 0 && (
        <div className="qd-solution-steps">
          <h4>Worked solution</h4>
          <ol>
            {parsed.solutionSteps.map((step, i) => (
              revealSolutionSteps.includes(i) && (
                <li key={i}>
                  <MathText text={prepareMathText(step)} />
                </li>
              )
            ))}
          </ol>
        </div>
      )}

      {showAnswer && (
        <div className="qd-answer-reveal">
          <strong>Correct answer:</strong>{' '}
          <MathText text={String(parsed.correctAnswer)} />
        </div>
      )}
    </div>
  );
}
