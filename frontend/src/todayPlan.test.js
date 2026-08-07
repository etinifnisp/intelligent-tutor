import test from 'node:test';
import assert from 'node:assert/strict';

import { buildStudyGroups, filterStudyGroups } from './todayPlan.js';

test('buildStudyGroups uses only supplied learning-plan and session data', () => {
  const groups = buildStudyGroups({
    recommended_questions: [{
      question_id: 'q-17',
      subject: 'Physics',
      chapter: 'Laws of Motion',
      difficulty: 'Medium',
      reasons: ['Targets a weak prerequisite'],
    }],
    revision_due: [{
      concept_id: 'Chemical Bonding',
      subject: 'Chemistry',
      p_known: 0.38,
      next_review_at: '2026-07-31T12:00:00Z',
      reason: 'Spaced review is due',
    }],
    weak_concepts: ['Chemical Bonding', 'Quadratic Equations'],
  }, {
    subject: 'Mathematics',
    chapter: 'Sequences and Series',
    mode: 'adaptive',
    savedAt: 123,
  });

  assert.deepEqual(groups.map((group) => group.items.length), [1, 1, 1, 1]);
  assert.equal(groups[0].items[0].title, 'Sequences and Series');
  assert.equal(groups[1].items[0].questionId, 'q-17');
  assert.equal(groups[2].items[0].mastery, 0.38);
  assert.equal(groups[3].items[0].title, 'Quadratic Equations');
});

test('filterStudyGroups does not invent a subject for unclassified concepts', () => {
  const groups = buildStudyGroups({ weak_concepts: ['Vectors'] });
  const physics = filterStudyGroups(groups, 'Physics');

  assert.equal(physics.flatMap((group) => group.items).length, 0);
  assert.equal(filterStudyGroups(groups, 'All')[3].items[0].title, 'Vectors');
});
