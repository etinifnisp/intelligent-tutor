/**
 * Renders tutor chat messages with paragraph blocks and MathJax math.
 * Does not run prepareMathText (that pipeline is for PDF-extracted questions).
 */
import MathText from '../MathText.jsx';

const MATH_SEGMENT_RE = /(\$\$[\s\S]+?\$\$|\$[^$\n]+?\$|\\\[[\s\S]+?\\\]|\\\([^\\]*?\\\))/g;

function normalizeChatText(text) {
  return String(text)
    .replace(/<br\s*\/?>/gi, '\n')
    .replace(/\r\n/g, '\n');
}

function splitMathAndText(text) {
  const parts = [];
  let last = 0;
  let match;
  const re = new RegExp(MATH_SEGMENT_RE.source, 'g');
  while ((match = re.exec(text)) !== null) {
    if (match.index > last) parts.push({ type: 'text', text: text.slice(last, match.index) });
    parts.push({ type: 'math', text: match[0] });
    last = match.index + match[0].length;
  }
  if (last < text.length) parts.push({ type: 'text', text: text.slice(last) });
  return parts.length ? parts : [{ type: 'text', text }];
}

function formatTextMarkdown(text) {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/`([^`]+)`/g, '<code>$1</code>');
}

function RichLine({ text }) {
  const parts = splitMathAndText(text);
  return (
    <>
      {parts.map((part, i) =>
        part.type === 'math' ? (
          <MathText key={i} text={part.text} />
        ) : (
          <span key={i} dangerouslySetInnerHTML={{ __html: formatTextMarkdown(part.text) }} />
        ),
      )}
    </>
  );
}

function renderParagraph(para) {
  const lines = para.split('\n');
  if (lines.length === 1) return <RichLine text={lines[0]} />;
  return lines.map((line, i) => (
    <span key={i}>
      {i > 0 && <br />}
      <RichLine text={line} />
    </span>
  ));
}

export default function ChatMessageContent({ text, streaming = false }) {
  if (!text) return null;

  const normalized = normalizeChatText(text);
  const paragraphs = normalized.split(/\n{2,}/).filter((p) => p.trim());

  return (
    <div className="chat-message-content">
      {paragraphs.map((para, i) => {
        const trimmed = para.trim();
        const isBlockquote = trimmed.startsWith('>');
        const body = isBlockquote
          ? trimmed.replace(/^>\s?/gm, '').trim()
          : trimmed;
        const isLastStreaming = streaming && i === paragraphs.length - 1;

        return (
          <div
            key={i}
            className={`chat-para${isBlockquote ? ' chat-para-quote' : ''}`}
          >
            {isLastStreaming ? (
              <span className="chat-streaming-plain">{body}</span>
            ) : (
              renderParagraph(body)
            )}
          </div>
        );
      })}
    </div>
  );
}
