import { useEffect, useRef, useState, useCallback } from 'react';
import { wsUrl, closeWebSocket } from '../utils.jsx';

export function useTutorSocket(userId) {
  const wsRef = useRef(null);
  const [connected, setConnected] = useState(false);
  const [sending, setSending] = useState(false);
  const activeRef = useRef(true);

  const connect = useCallback(() => {
    if (!activeRef.current) return;
    const ws = new WebSocket(wsUrl());
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
    const handler = (e) => {
      const data = JSON.parse(e.data);
      onEvent?.(data);
      if (data.type === 'done' || data.type === 'error') {
        setSending(false);
        wsRef.current?.removeEventListener('message', handler);
      }
    };
    wsRef.current.addEventListener('message', handler);
    wsRef.current.send(JSON.stringify(payload));
    return true;
  }, []);

  return { connected, sending, send, wsRef };
}
