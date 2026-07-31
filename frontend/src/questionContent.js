import { API } from './config.js';

const GREEK_MAP = {
  α: '\\alpha', β: '\\beta', γ: '\\gamma', δ: '\\delta', ε: '\\epsilon',
  θ: '\\theta', λ: '\\lambda', μ: '\\mu', π: '\\pi', σ: '\\sigma',
  φ: '\\phi', ω: '\\omega', Δ: '\\Delta', Σ: '\\Sigma', Ω: '\\Omega',
};

const CHOICE_LABELS = ['A', 'B', 'C', 'D'];
const OPTION_LINE = /^\s*(?:\(([a-d1-4])\)|\[([a-d1-4])\]|([a-d1-4])[\).:])\s*(.*)$/i;

export function resolveImageUrl(path) {
  if (!path) return null;
  if (path.startsWith('http://') || path.startsWith('https://')) return path;
  if (path.startsWith('/')) return `${API}${path}`;
  return `${API}/images/${path.replace(/^\.?\//, '')}`;
}

export function getQuestionImages(question) {
  const urls = [];
  for (const img of question.images || []) {
    const url = resolveImageUrl(img);
    if (url) urls.push(url);
  }
  for (const path of question.diagram_paths || []) {
    const url = resolveImageUrl(path);
    if (url) urls.push(url);
  }
  return [...new Set(urls)];
}

function normalizeLabel(value) {
  const label = String(value || '').trim().toUpperCase();
  return { 1: 'A', 2: 'B', 3: 'C', 4: 'D' }[label] || label;
}

function sanitizeOptions(options) {
  const unique = new Map();
  for (const option of options || []) {
    if (!option || typeof option !== 'object') continue;
    const label = normalizeLabel(option.label);
    const text = String(option.text || '').replace(/\s+/g, ' ').trim();
    if (CHOICE_LABELS.includes(label) && text && text !== ')' && !unique.has(label)) {
      unique.set(label, { label, text });
    }
  }
  return CHOICE_LABELS.every(label => unique.has(label))
    ? CHOICE_LABELS.map(label => unique.get(label))
    : [];
}

function parseOptionsFromText(raw) {
  const header = raw.match(/\n\s*Options?\s*:\s*/i);
  const source = header ? raw.slice(header.index + header[0].length) : raw;
  const block = source.replace(/\n\s*(?:Answer|Ans\.?|Sol\.?|Solution)\s*:?\s*[\s\S]*$/i, '');
  const options = [];
  let current = null;

  const flush = () => {
    if (current) options.push(current);
    current = null;
  };

  for (const line of block.split('\n')) {
    const match = line.match(OPTION_LINE);
    if (match) {
      flush();
      current = {
        label: normalizeLabel(match[1] || match[2] || match[3]),
        text: (match[4] || '').trim(),
      };
    } else if (current && line.trim()) {
      current.text = `${current.text} ${line.trim()}`.trim();
    }
  }
  flush();
  return sanitizeOptions(options);
}

function cleanStem(text, hasChoices) {
  let stem = String(text || '');
  const sectionStart = stem.search(/\n\s*(?:Options?|Answer|Ans\.?|Sol\.?|Solution)\s*:/i);
  if (sectionStart >= 0) stem = stem.slice(0, sectionStart);

  if (hasChoices) {
    const lines = stem.split('\n');
    const firstChoice = lines.findIndex(line => OPTION_LINE.test(line));
    if (firstChoice >= 0) stem = lines.slice(0, firstChoice).join('\n');
  }

  return stem
    .replace(/^\s*(?:Question\s*:|Q\.?\s*\d+\s*[:.)-]?)\s*/i, '')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

function normalizeAnswer(answer) {
  if (!answer) return null;
  const match = String(answer).trim().match(/(?:\(([A-D1-4])\)|\[([A-D1-4])\]|([A-D1-4]))/i);
  return match ? normalizeLabel(match[1] || match[2] || match[3]) : String(answer).trim();
}

export function parseQuestionContent(question, { includeAnswer = false, includeSolution = false } = {}) {
  const raw = String(
    question.raw_text || question.normalized_text || question.question_text || question.stem_text || '',
  ).trim();

  let options = sanitizeOptions(question.options);
  if (options.length !== 4) options = parseOptionsFromText(raw);

  const canonicalStem = options.length === 4 && question.stem_text
    ? question.stem_text
    : raw;
  const stem = cleanStem(canonicalStem, options.length === 4);

  let correctAnswer = question.correct_answer || null;
  if (!correctAnswer) {
    const match = raw.match(/\n\s*(?:Answer|Ans\.?)\s*:?\s*([^\n]+)/i);
    if (match) correctAnswer = match[1];
  }
  correctAnswer = normalizeAnswer(correctAnswer);

  let solution = question.official_solution || '';
  if (!solution) {
    const match = raw.match(/\n\s*(?:Sol\.?|Solution)\s*:?\s*([\s\S]+)$/i);
    if (match) solution = match[1].trim();
  }
  const solutionSteps = solution
    ? solution.split(/\n+/).map(step => step.trim()).filter(step => step.length > 2)
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
  out = out.replace(/(?<![$\\])√\s*\(([^)]+)\)/g, (_, inner) => `$\\sqrt{${inner}}$`);
  out = out.replace(/(?<![$\\])√\s*([A-Za-z0-9]+)/g, (_, inner) => `$\\sqrt{${inner}}$`);
  return out;
}

export const SOLUTION_STEPS = [
  { id: 'concept', label: 'Concept', description: 'Key principle to recall' },
  { id: 'formula', label: 'Formula', description: 'Equations to use' },
  { id: 'setup', label: 'Setup', description: 'How to set up the problem' },
  { id: 'solution', label: 'Full solution', description: 'Complete worked answer' },
];
