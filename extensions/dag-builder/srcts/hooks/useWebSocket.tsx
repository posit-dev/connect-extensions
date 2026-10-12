/**
 * WebSocket hook for DAG Builder
 * Replaces shiny-react hooks with standard WebSocket communication
 */

import { useState, useEffect, useCallback, useRef } from 'react';

type MessageHandler = (data: any) => void;

interface WebSocketHook {
  isConnected: boolean;
  sendMessage: (type: string, data: any) => void;
  onMessage: (type: string, handler: MessageHandler) => void;
  offMessage: (type: string, handler: MessageHandler) => void;
}

const WS_URL = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}${window.location.pathname}ws`;

// Singleton WebSocket connection
let wsInstance: WebSocket | null = null;
let messageHandlers: Map<string, Set<MessageHandler>> = new Map();
let reconnectTimeout: number | null = null;
let connectionPromise: Promise<void> | null = null;

const connectWebSocket = (): Promise<void> => {
  if (connectionPromise) {
    return connectionPromise;
  }

  connectionPromise = new Promise((resolve, reject) => {
    if (wsInstance && wsInstance.readyState === WebSocket.OPEN) {
      resolve();
      connectionPromise = null;
      return;
    }

    if (wsInstance) {
      wsInstance.close();
    }

    wsInstance = new WebSocket(WS_URL);

    wsInstance.onopen = () => {
      console.log('WebSocket connected');
      connectionPromise = null;
      resolve();
    };

    wsInstance.onerror = (error) => {
      console.error('WebSocket error:', error);
      connectionPromise = null;
      reject(error);
    };

    wsInstance.onclose = () => {
      console.log('WebSocket disconnected, attempting to reconnect...');
      connectionPromise = null;

      // Attempt to reconnect after 2 seconds
      if (reconnectTimeout) {
        clearTimeout(reconnectTimeout);
      }
      reconnectTimeout = setTimeout(() => {
        connectWebSocket();
      }, 2000);
    };

    wsInstance.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        const { type, data } = message;

        // Call all registered handlers for this message type
        const handlers = messageHandlers.get(type);
        if (handlers) {
          handlers.forEach(handler => handler(data));
        }
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
      }
    };
  });

  return connectionPromise;
};

export const useWebSocket = (): WebSocketHook => {
  const [isConnected, setIsConnected] = useState(false);
  const handlersRef = useRef<Map<string, Set<MessageHandler>>>(new Map());

  useEffect(() => {
    // Connect to WebSocket
    connectWebSocket()
      .then(() => setIsConnected(true))
      .catch(error => console.error('Failed to connect:', error));

    // Update connection status based on WebSocket state
    const checkConnection = setInterval(() => {
      if (wsInstance) {
        setIsConnected(wsInstance.readyState === WebSocket.OPEN);
      }
    }, 1000);

    return () => {
      clearInterval(checkConnection);
      // Clean up handlers registered by this component
      handlersRef.current.forEach((handlers, type) => {
        handlers.forEach(handler => {
          const globalHandlers = messageHandlers.get(type);
          if (globalHandlers) {
            globalHandlers.delete(handler);
          }
        });
      });
    };
  }, []);

  const sendMessage = useCallback((type: string, data: any) => {
    if (wsInstance && wsInstance.readyState === WebSocket.OPEN) {
      wsInstance.send(JSON.stringify({ type, data }));
    } else {
      console.warn('WebSocket not connected, message not sent:', type);
      // Try to reconnect and send after connection
      connectWebSocket().then(() => {
        if (wsInstance && wsInstance.readyState === WebSocket.OPEN) {
          wsInstance.send(JSON.stringify({ type, data }));
        }
      });
    }
  }, []);

  const onMessage = useCallback((type: string, handler: MessageHandler) => {
    if (!messageHandlers.has(type)) {
      messageHandlers.set(type, new Set());
    }
    messageHandlers.get(type)!.add(handler);

    // Track handlers for cleanup
    if (!handlersRef.current.has(type)) {
      handlersRef.current.set(type, new Set());
    }
    handlersRef.current.get(type)!.add(handler);
  }, []);

  const offMessage = useCallback((type: string, handler: MessageHandler) => {
    const handlers = messageHandlers.get(type);
    if (handlers) {
      handlers.delete(handler);
    }

    // Remove from component's handler tracking
    const componentHandlers = handlersRef.current.get(type);
    if (componentHandlers) {
      componentHandlers.delete(handler);
    }
  }, []);

  return {
    isConnected,
    sendMessage,
    onMessage,
    offMessage
  };
};
