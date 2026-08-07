export function scrollChatToBottom(messagePane) {
  if (!messagePane) return;
  messagePane.scrollTop = messagePane.scrollHeight;
}
