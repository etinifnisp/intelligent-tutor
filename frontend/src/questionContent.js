import { API } from './config.js';

const GREEK_MAP = {
  α: '\\alpha', β: '\\beta', γ: '\\gamma', δ: '\\delta', ε: '\\epsilon',
  θ: '\\theta', λ: '\\lambda', μ: '\\mu', π: '\\pi', σ: '\\sigma',
  φ: '\\phi', ω: '\\omega', Δ: '\\Delta', Σ: '\\Sigma', Ω: '\\Omega',
};

const OPTION_LINE = /^\s*(?:\(([a-d1-4])\)|\[([A-D1-4])\]|([A-D1-4])[\).:])\s*(.+)$/i;
const NUMERIC_OPTION = /^\s*\((\d)\)\s*(.+)$/;

export function resolveImageUrl(path) {
  if (!path) return null;
  if (path.startsWith('http://') || path.startsWith('https://')) return path;
  if (path.startsWith('/')) return `${API}${path}`;
  return `${API}/images/${path.replace(/^\.?\//, '')}`;
}

export function getQuestionImages(question) {
  const urls = [];
  for (const img of question.images || []) {
    const u = resolveImageUrl(img);
    if (u) urls.push(u);
  }
  for (const p of question.diagram_paths || []) {
    const u = resolveImageUrl(p);
    if (u) urls.push(u);
  }
  return [...new Set(urls)];
}

function cleanStem(text) {
  return text
    .replace(/^Question:\s*/i, '')
    .replace(/\bQ\.?\s*\d+\.?\s*/i, '')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

function parseOptionsFromText(raw) {
  const options = [];
  const optionsBlock = raw.match(/\nOptions?\s*:\s*([\s\S]*?)(?:\n(?:Answer|Ans\.?|Sol\.?|Solution)\s*:|$)/i);
  const block = optionsBlock ? optionsBlock[1] : raw;
  const lines = block.split('\n');

  for (const line of lines) {
    const m = line.match(OPTION_LINE);
    const num = line.match(NUMERIC_OPTION);
    if (m) {
      const label = (m[1] || m[2] || m[3]).toUpperCase();
      const text = (m[4] || '').trim();
      if (!text || text === ')') continue;
      const normalized = /^\d$/.test(label)
        ? String.fromCharCode(64 + Number(label))
        : label;
      options.push({ label: normalized, text });
    } else if (num) {
      options.push({
        label: String.fromCharCode(64 + Number(num[1])),
        text: num[2].trim(),
      });
    }
  }
  return options;
}

function parseStructuredOptions(question) {
  if (!Array.isArray(question.options)) return [];
  return question.options
    .filter(opt => opt?.text && opt.text.trim() && opt.text.trim() !== ')')
    .map(opt => ({
      label: String(opt.label || '').toUpperCase(),
      text: opt.text.trim(),
    }));
}

export function parseQuestionContent(question, { includeAnswer = false, includeSolution = false } = {}) {
  const raw = (
    question.raw_text ||
    question.stem_text ||
    question.normalized_text ||
    question.question_text ||
    ''
  ).trim();

  let correctAnswer = question.correct_answer || null;
  let solution = question.official_solution || '';

  const answerMatch = raw.match(/\n(?:Answer|Ans\.?)\s*:?\s*([^\n]+)/i);
  if (answerMatch && !correctAnswer) {
    correctAnswer = answerMatch[1].trim();
  }

  const solMatch = raw.match(/\n(?:Sol\.?|Solution)\s*:?\s*([\s\S]+)$/i);
  if (solMatch && !solution) {
    solution = solMatch[1].trim();
  }

  let stem = raw;
  if (!includeAnswer) {
    stem = stem
      .replace(/\n(?:Answer|Ans\.?)\s*:?[^\n]*[\s\S]*$/i, '')
      .replace(/\n(?:Sol\.?|Solution)\s*:?[\s\S]*$/i, '')
      .replace(/\nOptions?\s*:[\s\S]*$/i, '');
  } else if (!includeSolution) {
    stem = stem.replace(/\n(?:Sol\.?|Solution)\s*:?[\s\S]*$/i, '');
  }

  stem = cleanStem(stem);

  let options = parseStructuredOptions(question);
  if (options.length < 2) {
    const fromText = parseOptionsFromText(raw);
    if (fromText.length >= 2) options = fromText;
  }

  if (options.length < 2) {
    const inline = [...stem.matchAll(/\(([1-4])\)/g)];
    if (inline.length >= 2) {
      const tail = stem.split(/\n/).slice(-6);
      const numeric = tail
        .map(l => l.match(NUMERIC_OPTION))
        .filter(Boolean)
        .map(m => ({
          label: String.fromCharCode(64 + Number(m[1])),
          text: m[2].trim(),
        }));
      if (numeric.length >= 2) options = numeric;
    }
  }

  if (options.length >= 2) {
    const optionPattern = new RegExp(
      options.map(o => `\\(${o.label}\\)|\\(${o.label.toLowerCase()}\\)`).join('|'),
      'g',
    );
    stem = stem.replace(optionPattern, '').replace(/\n{2,}/g, '\n').trim();
  }

  stem = stem.replace(/\n(\(\d\)\s*)+$/g, '').trim();

  const solutionSteps = solution
    ? solution
        .split(/\n+/)
        .map(s => s.trim())
        .filter(s => s.length > 2)
    : [];

  return {
    stem,
    options,
    correctAnswer: includeAnswer ? correctAnswer : null,
    solution: includeSolution ? solution : null,
    solutionSteps: includeSolution ? solutionSteps : [],
  };
}

export function prepareMathText(text) {
  if (!text) return '';

  let out = text;

  for (const [char, latex] of Object.entries(GREEK_MAP)) {
    out = out.replace(new RegExp(char, 'g'), `$${latex}$`);
  }

  out = out.replace(
    /\(\s*radius of earth\s*;\s*\)/gi,
    '<span class="math-placeholder" title="Symbol missing in source PDF">R<sub>e</sub></span>',
  );
  out = out.replace(/;\s*\)/g, '<span class="math-placeholder">[symbol]</span>)');
  out = out.replace(/\s+;\s+(?=[).,])/g, ' <span class="math-placeholder">[symbol]</span> ');

  out = out.replace(
    /(?<![$\\])(\b[A-Za-z]{1,3})\s*\/\s*([A-Za-z0-9]{1,3}\b)/g,
    (_, a, b) => `$${a}/${b}$`,
  );
  out = out.replace(
    /(?<![$\\])([A-Za-z])(\^[0-9]+|\^\{[^}]+\})/g,
    (_, base, exp) => `$${base}${exp}$`,
  );
  out = out.replace(
    /(?<![$\\])√\s*\(([^)]+)\)/g,
    (_, inner) => `$\\sqrt{${inner}}$`,
  );
  out = out.replace(
    /(?<![$\\])√\s*([A-Za-z0-9]+)/g,
    (_, inner) => `$\\sqrt{${inner}}$`,
  );

  return out;
}

export const SOLUTION_STEPS = [
  { id: 'concept', label: 'Concept', description: 'Key principle to recall' },
  { id: 'formula', label: 'Formula', description: 'Equations to use' },
  { id: 'setup', label: 'Setup', description: 'How to set up the problem' },
  { id: 'solution', label: 'Full solution', description: 'Complete worked answer' },
];
