import { useEffect, useRef, useState, useCallback } from 'react';
import { createTutorSocket, closeWebSocket } from '../utils.jsx';

const REQUEST_TIMEOUT_MS = 45000;

export function useTutorSocket(userId) {
  const wsRef = useRef(null);
  const [connected, setConnected] = useState(false);
  const [sending, setSending] = useState(false);
  const activeRef = useRef(true);

  const connect = useCallback(() => {
    if (!activeRef.current) return;
    const ws = createTutorSocket();
    wsRef.current = ws;
    ws.onopen = () => {
      setConnected(true);
      window.AppLogger?.push('info', 'Tutor socket connected');
    };
    ws.onclose = () => {
      setConnected(false);
      setSending(false);
      if (activeRef.current) setTimeout(connect, 3000);
    };
    ws.onerror = () => {
      window.AppLogger?.push('error', 'Tutor socket error');
      setSending(false);
    };
  }, []);

  useEffect(() => {
    activeRef.current = true;
    connect();
    return () => {
      activeRef.current = false;
      closeWebSocket(wsRef.current);
    };
  }, [userId, connect]);

  const send = useCallback((payload, onEvent) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      onEvent?.({ type: 'error', message: 'Not connected to tutor. Retrying…' });
      return false;
    }
    setSending(true);
    let settled = false;

    const finish = (event) => {
      if (settled) return;
      settled = true;
      clearTimeout(timeoutId);
      setSending(false);
      wsRef.current?.removeEventListener('message', handler);
      onEvent?.(event);
    };

    const handler = (e) => {
      let data;
      try {
        data = JSON.parse(e.data);
      } catch {
        finish({ type: 'error', message: 'Received an invalid tutor response.' });
        return;
      }
      onEvent?.(data);
      if (data.type === 'done' || data.type === 'error') {
        finish(data);
      }
    };

    const timeoutId = setTimeout(() => {
      finish({ type: 'error', message: 'Tutor response timed out. Please retry.' });
    }, REQUEST_TIMEOUT_MS);

    wsRef.current.addEventListener('message', handler);
    try {
      wsRef.current.send(JSON.stringify(payload));
    } catch {
      finish({ type: 'error', message: 'Could not send your message. Please retry.' });
      return false;
    }
    return true;
  }, []);

  return { connected, sending, send, wsRef };
}
