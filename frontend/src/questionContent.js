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
      const prev = current.text.trim();
      const next = line.trim();
      if (/^\d{1,3}$/.test(prev) && /^\d{1,3}$/.test(next)) {
        current.text = `${prev}/${next}`;
      } else {
        current.text = `${current.text} ${next}`.trim();
      }
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

// PDF extraction often emits box-drawing glyphs and columnar math as many short lines.
const PDF_DRAWING_RE = /[\u239b-\u23b9\u2500-\u257f\u2e00-\u2e7f\ufb00-\ufb4f]/g;
const MATH_FRAGMENT_LINE = /^[\dA-Za-z∪∩′'′=+\-(),./\\^_{}\s]{1,12}$/;

function stripPdfDrawingChars(text) {
  return text
    .split('\n')
    .filter(line => line.replace(PDF_DRAWING_RE, '').trim().length > 0)
    .join('\n')
    .replace(PDF_DRAWING_RE, ' ');
}

function collapsePdfMathLines(text) {
  const lines = text.split('\n').map(line => line.trim());
  const merged = [];
  let buffer = '';

  const flush = () => {
    if (buffer) {
      merged.push(buffer);
      buffer = '';
    }
  };

  for (const line of lines) {
    if (!line) {
      flush();
      continue;
    }
    if (MATH_FRAGMENT_LINE.test(line) && !/^(Question|Options?|Answer|Solution)$/i.test(line)) {
      buffer = buffer ? `${buffer} ${line}` : line;
      continue;
    }
    flush();
    merged.push(line);
  }
  flush();
  return merged.join('\n');
}

function mergeVerticalFractions(text) {
  return text.replace(
    /(^|[\s,(=+\-*/])(\d{1,3})\s*\n\s*(\d{1,3})(?=[\s,;.)=\n+\-*/]|$)/gm,
    (_, before, num, den) => `${before}$\\frac{${num}}{${den}}$`,
  );
}

function repairColumnarProbability(text) {
  let out = text;

  // P(A)=1/3, P(B)=1/5 from columnar "1 1 , 3 5 P A P B = ="
  out = out.replace(
    /(\d)\s+(\d)\s*,\s*(\d)\s+(\d)\s+P\s*A\s+P\s*B(?:\s*=\s*)+/gi,
    (_, n1, n2, d1, d2) => `$P(A)=\\frac{${n1}}{${d1}}$, $P(B)=\\frac{${n2}}{${d2}}$`,
  );

  // P(A ∪ B) = 1/2 from "1 2 P A B ∪ ="
  out = out.replace(
    /(\d)\s+(\d+)\s+P\s*A\s*B\s*∪(?:\s*=\s*)?/gi,
    (_, n, d) => `$P(A \\cup B)=\\frac{${n}}{${d}}$`,
  );
  out = out.replace(
    /(\d)\s+(\d+)\s+P\s*A\s*B\s*∩(?:\s*=\s*)?/gi,
    (_, n, d) => `$P(A \\cap B)=\\frac{${n}}{${d}}$`,
  );

  return out;
}

function repairComplementFragments(text) {
  return text
    .replace(/\bA\s+A\s+P\s+P\s+B\s+B\s*['′]\s*\+\s*=\s*['′]/g, "$P(A') + P(B') = ?$")
    .replace(/\bA\s+A\s+P\s+P\s+B\s+B\s*['′]\s*\/\s*['′]/g, "$\\frac{P(A')}{P(B')}$");
}

function repairProbabilityNotation(text) {
  let out = text
    .replace(/[′’`´]/g, "'")
    .replace(/\(\s*\)/g, '');

  out = repairComplementFragments(out);

  out = out
    .replace(/\bP\s*\(\s*([A-Z])\s*\/\s*([A-Z])\s*\)/g, 'P($1/$2)')
    .replace(/\bP\s+([A-Z])\s+([A-Z])\s*∪/g, 'P($1 $\\cup$ $2)')
    .replace(/\bP\s+([A-Z])\s+([A-Z])\s*∩/g, 'P($1 $\\cap$ $2)')
    .replace(/\bP\s+([A-Z])\b/g, 'P($1)')
    .replace(/\b([A-Z])\s*'\s*∩\s*([A-Z])\s*'/g, "$1' $\\cap$ $2'")
    .replace(/\b([A-Z])\s*'\s*∪\s*([A-Z])\s*'/g, "$1' $\\cup$ $2'")
    .replace(/\bP\s*\(\s*([A-Z])'\s*\)/g, "P($1')");

  return out;
}

function wrapBareMathExpressions(text) {
  const MATH_RE = /(\$\$[\s\S]+?\$\$|\$[^$\n]+?\$)/g;
  const parts = [];
  let last = 0;
  let match;
  while ((match = MATH_RE.exec(text)) !== null) {
    if (match.index > last) parts.push({ text: text.slice(last, match.index), isMath: false });
    parts.push({ text: match[0], isMath: true });
    last = match.index + match[0].length;
  }
  if (last < text.length) parts.push({ text: text.slice(last), isMath: false });

  return parts.map(part => {
    if (part.isMath) return part.text;
    return part.text.replace(
      /(^|[\s(=,])(P\([^$\n]{1,40}\))(?=$|[\s,.;:=?])/g,
      (_, before, expr) => `${before}$${expr}$`,
    );
  }).join('');
}

function normalizeMathSpacing(text) {
  return text
    .replace(/(\$)(and|then|so|if)\b/gi, '$1 $2')
    .replace(/\b(and|then|so|if)(\$)/gi, '$1 $2');
}

export function prepareMathText(text) {
  if (!text) return '';
  let out = String(text);

  out = stripPdfDrawingChars(out);
  out = collapsePdfMathLines(out);
  out = mergeVerticalFractions(out);
  out = repairColumnarProbability(out);
  out = repairProbabilityNotation(out);

  // ── Missing-glyph artifacts from PDF extraction ───────────────────────────
  out = out.replace(/[\u25a1\u22a0\u2610\u2612\u2b1c]/g, '{\\square}');

  // ── Wrap bare math expressions that aren't already delimited ──────────────
  function wrapIfNotDelimited(str, re, wrapper) {
    // Split on existing $...$ regions and only apply re to text regions
    const parts = [];
    const MATH_RE = /(\$\$[\s\S]+?\$\$|\$[^$\n]+?\$)/g;
    let last = 0, m;
    while ((m = MATH_RE.exec(str)) !== null) {
      if (m.index > last) parts.push({ text: str.slice(last, m.index), isMath: false });
      parts.push({ text: m[0], isMath: true });
      last = m.index + m[0].length;
    }
    if (last < str.length) parts.push({ text: str.slice(last), isMath: false });
    return parts.map(p => p.isMath ? p.text : p.text.replace(re, wrapper)).join('');
  }

  // Greek letters → inline math
  const GREEK = {
    'α':'\\alpha','β':'\\beta','γ':'\\gamma','δ':'\\delta','ε':'\\epsilon',
    'ζ':'\\zeta','η':'\\eta','θ':'\\theta','ι':'\\iota','κ':'\\kappa',
    'λ':'\\lambda','μ':'\\mu','ν':'\\nu','ξ':'\\xi','π':'\\pi',
    'ρ':'\\rho','σ':'\\sigma','τ':'\\tau','φ':'\\phi','χ':'\\chi',
    'ψ':'\\psi','ω':'\\omega','Γ':'\\Gamma','Δ':'\\Delta','Θ':'\\Theta',
    'Λ':'\\Lambda','Ξ':'\\Xi','Π':'\\Pi','Σ':'\\Sigma','Φ':'\\Phi',
    'Ψ':'\\Psi','Ω':'\\Omega',
  };
  // Build a single regex for all Greek letters and replace each with $\letter$
  const greekRe = new RegExp('[' + Object.keys(GREEK).join('') + ']', 'g');
  out = wrapIfNotDelimited(out, greekRe, ch => `$${GREEK[ch]}$`);

  // Common math operators / symbols → LaTeX equivalents (keep as text, KaTeX will render)
  const SYMBOL_MAP = [
    [/→/g, ' $\\rightarrow$ '],
    [/←/g, ' $\\leftarrow$ '],
    [/↔/g, ' $\\leftrightarrow$ '],
    [/⇒/g, ' $\\Rightarrow$ '],
    [/⇔/g, ' $\\Leftrightarrow$ '],
    [/∞/g, ' $\\infty$ '],
    [/±/g, ' $\\pm$ '],
    [/∓/g, ' $\\mp$ '],
    [/×/g, ' $\\times$ '],
    [/÷/g, ' $\\div$ '],
    [/≤/g, ' $\\leq$ '],
    [/≥/g, ' $\\geq$ '],
    [/≠/g, ' $\\neq$ '],
    [/≈/g, ' $\\approx$ '],
    [/∈/g, ' $\\in$ '],
    [/∉/g, ' $\\notin$ '],
    [/∑/g, ' $\\sum$ '],
    [/∏/g, ' $\\prod$ '],
    [/∫/g, ' $\\int$ '],
    [/∂/g, ' $\\partial$ '],
    [/∇/g, ' $\\nabla$ '],
    [/√/g, ' $\\sqrt{}$ '],
    [/∝/g, ' $\\propto$ '],
    [/∪/g, ' $\\cup$ '],
    [/∩/g, ' $\\cap$ '],
    [/⊂/g, ' $\\subset$ '],
    [/⊃/g, ' $\\supset$ '],
    [/⊆/g, ' $\\subseteq$ '],
    [/⊇/g, ' $\\supseteq$ '],
    [/∀/g, ' $\\forall$ '],
    [/∃/g, ' $\\exists$ '],
    [/¬/g, ' $\\neg$ '],
    [/∧/g, ' $\\land$ '],
    [/∨/g, ' $\\lor$ '],
    [/°/g, '^\\circ'],
  ];
  for (const [re, replacement] of SYMBOL_MAP) {
    out = wrapIfNotDelimited(out, re, () => replacement);
  }

  // Superscripts: x^2, A^n, x^{n+1} — only if not already in $...$
  out = wrapIfNotDelimited(
    out,
    /(?<![\$\\])([A-Za-z0-9])\^(\{[^}]+\}|[0-9]+)/g,
    (_, base, exp) => `$${base}^${exp}$`,
  );

  // Subscripts: x_1, A_n — only if not already in $...$
  out = wrapIfNotDelimited(
    out,
    /(?<![\$\\])([A-Za-z])_([0-9]+|[a-z])/g,
    (_, base, sub) => `$${base}_{${sub}}$`,
  );

  // Square root: √(expr) or √expr
  out = wrapIfNotDelimited(out, /√\(([^)]+)\)/g, (_, inner) => `$\\sqrt{${inner}}$`);
  out = wrapIfNotDelimited(out, /√([A-Za-z0-9]+)/g, (_, inner) => `$\\sqrt{${inner}}$`);

  // Simple fractions: a/b where a and b look like variables/numbers
  out = wrapIfNotDelimited(
    out,
    /(?<![\$\/\w])(\d+|[A-Za-z])\/(\d+|[A-Za-z])(?![\w\/])/g,
    (_, a, b) => `$\\frac{${a}}{${b}}$`,
  );

  out = wrapBareMathExpressions(out);
  out = normalizeMathSpacing(out);

  // Drop stray "=" left over from columnar PDF extraction.
  out = out.replace(/\s+=\s+(?=and\b)/gi, ' ');

  // Merge adjacent inline segments: $a$ $b$ → $a b$
  out = out.replace(/\$([^$\n]{1,120})\$\s*\$([^$\n]{1,120})\$/g, (_, a, b) => `$${a} ${b}$`);

  return out.replace(/\s{2,}/g, ' ').trim();
}

export const SOLUTION_STEPS = [
  { id: 'concept', label: 'Concept', description: 'Key principle to recall' },
  { id: 'formula', label: 'Formula', description: 'Equations to use' },
  { id: 'setup', label: 'Setup', description: 'How to set up the problem' },
  { id: 'solution', label: 'Full solution', description: 'Complete worked answer' },
];
