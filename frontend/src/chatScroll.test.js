import test from 'node:test';
import assert from 'node:assert/strict';

import { scrollChatToBottom } from './chatScroll.js';

test('scrollChatToBottom scrolls only the message pane', () => {
  let scrollIntoViewCalled = false;
  const messagePane = {
    scrollHeight: 920,
    scrollTop: 0,
    scrollIntoView() {
      scrollIntoViewCalled = true;
    },
  };

  scrollChatToBottom(messagePane);

  assert.equal(messagePane.scrollTop, 920);
  assert.equal(scrollIntoViewCalled, false);
});

test('scrollChatToBottom tolerates an unmounted pane', () => {
  assert.doesNotThrow(() => scrollChatToBottom(null));
});
