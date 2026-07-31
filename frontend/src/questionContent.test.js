import test from 'node:test';
import assert from 'node:assert/strict';

import { parseQuestionContent } from './questionContent.js';

test('keeps answer and choices out of the visible stem after reveal', () => {
  const question = {
    raw_text: [
      'Question: What is 2 + 2?',
      'Options:',
      '(a) 2',
      '(b) 3',
      '(c) 4',
      '(d) 5',
      'Answer: (c)',
    ].join('\n'),
  };

  const parsed = parseQuestionContent(question, { includeAnswer: true });

  assert.equal(parsed.stem, 'What is 2 + 2?');
  assert.equal(parsed.options.length, 4);
  assert.equal(parsed.correctAnswer, 'C');
});

test('prefers the canonical stem and returns exactly A-D once', () => {
  const question = {
    stem_text: 'A clean previous-year question stem.',
    raw_text: 'Paper instructions\n[A] duplicated raw choice\n[B] duplicated raw choice',
    options: [
      { label: 'A', text: 'First' },
      { label: 'B', text: 'Second' },
      { label: 'C', text: 'Third' },
      { label: 'D', text: 'Fourth' },
      { label: 'A', text: 'Duplicate' },
    ],
  };

  const parsed = parseQuestionContent(question);

  assert.equal(parsed.stem, 'A clean previous-year question stem.');
  assert.deepEqual(parsed.options.map(option => option.label), ['A', 'B', 'C', 'D']);
});
