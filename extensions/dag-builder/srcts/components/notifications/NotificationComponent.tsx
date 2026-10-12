import React, { useState, useEffect } from 'react';
import { useWebSocket } from '../../hooks/useWebSocket';
import { ToastMessage } from '../../types';

export function NotificationComponent() {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);
  const { onMessage, offMessage } = useWebSocket();

  // Helper to add a toast
  const addToast = (message: string, type: string) => {
    const newToast: ToastMessage = {
      id: Date.now(),
      message,
      type,
    };

    setToasts(prev => [...prev, newToast]);

    // Auto-remove toast after 6 seconds
    setTimeout(() => {
      setToasts(prev => prev.filter(toast => toast.id !== newToast.id));
    }, 6000);
  };

  // Listen for WebSocket logEvent messages
  useEffect(() => {
    const handleLogEvent = (msg: { message: string; type: string }) => {
      addToast(msg.message, msg.type);
    };

    onMessage('logEvent', handleLogEvent);

    return () => {
      offMessage('logEvent', handleLogEvent);
    };
  }, [onMessage, offMessage]);

  // Listen for local toast events (from REST API errors)
  useEffect(() => {
    const handleLocalToast = (event: Event) => {
      const customEvent = event as CustomEvent<{ message: string; type: string }>;
      addToast(customEvent.detail.message, customEvent.detail.type);
    };

    window.addEventListener('localToast', handleLocalToast);

    return () => {
      window.removeEventListener('localToast', handleLocalToast);
    };
  }, []);

  return (
    <div className="notifications">
      {toasts.map(toast => (
        <div key={toast.id} className={`toast toast-${toast.type}`}>
          {toast.message}
        </div>
      ))}
    </div>
  );
}