import test from 'node:test';
import assert from 'node:assert/strict';

import { isLearningStepDisabled } from './learningSteps.js';

test('allows a learner to open any help stage when the tutor is idle', () => {
  assert.equal(isLearningStepDisabled({ sending: false, stepIndex: 3, hintLevel: 0 }), false);
});

test('temporarily disables help stages only while a response is loading', () => {
  assert.equal(isLearningStepDisabled({ sending: true, stepIndex: 0, hintLevel: 0 }), true);
  assert.equal(isLearningStepDisabled({ sending: true, stepIndex: 3, hintLevel: 0 }), true);
});
