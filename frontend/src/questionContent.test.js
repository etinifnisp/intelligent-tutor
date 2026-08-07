import test from 'node:test';
import assert from 'node:assert/strict';

import { parseQuestionContent, prepareMathText } from './questionContent.js';

const PROBABILITY_RAW = `Question: If 
( )
( )
1
1
,
3
5
P A
P B
= =
 and 
(
)
1
2
P A
B
∪
=
 then 
A
A
P
P
B
B
′
+
=
′
 
Options:  
(a) 5
8  
(b) 4
9  
(c) 29
24  
(d) 3 
Answer: (c)`;

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

test('repairs columnar probability notation from broken PDF extraction', () => {
  const prepared = prepareMathText(PROBABILITY_RAW);

  assert.match(prepared, /P\(A\).*\\frac\{1\}\{3\}/);
  assert.match(prepared, /P\(B\).*\\frac\{1\}\{5\}/);
  assert.match(prepared, /P\(A \\cup B\).*\\frac\{1\}\{2\}/);
  assert.match(prepared, /P\(A'\) \+ P\(B'\)/);
  assert.match(prepared, /\$ and \$P\(A \\cup B\)/);
});

test('parses vertical fractions in MCQ options', () => {
  const parsed = parseQuestionContent({ raw_text: PROBABILITY_RAW });

  assert.equal(parsed.options[0].text, '5/8');
  assert.equal(parsed.options[1].text, '4/9');
  assert.equal(parsed.options[2].text, '29/24');
});
