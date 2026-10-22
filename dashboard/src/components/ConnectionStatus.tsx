import React from 'react';
import { WebSocketConnectionState } from '../websocket/websocketTypes';

interface ConnectionStatusProps {
  state: WebSocketConnectionState;
}

export const ConnectionStatus: React.FC<ConnectionStatusProps> = ({ state }) => {
  const configs: Record<WebSocketConnectionState, { label: string; bg: string; dot: string; text: string }> = {
    CONNECTED: {
      label: 'STREAM LIVE',
      bg: 'rgba(16, 185, 129, 0.15)',
      dot: '#10b981',
      text: '#10b981',
    },
    CONNECTING: {
      label: 'CONNECTING',
      bg: 'rgba(59, 130, 246, 0.15)',
      dot: '#3b82f6',
      text: '#3b82f6',
    },
    RECONNECTING: {
      label: 'RECONNECTING',
      bg: 'rgba(245, 158, 11, 0.15)',
      dot: '#f59e0b',
      text: '#f59e0b',
    },
    DISCONNECTED: {
      label: 'DISCONNECTED',
      bg: 'rgba(100, 116, 139, 0.15)',
      dot: '#64748b',
      text: '#94a3b8',
    },
    ERROR: {
      label: 'STREAM OFFLINE',
      bg: 'rgba(239, 68, 68, 0.15)',
      dot: '#ef4444',
      text: '#ef4444',
    },
  };

  const cfg = configs[state] || configs.DISCONNECTED;

  return (
    <div
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '8px',
        padding: '6px 14px',
        borderRadius: '9999px',
        backgroundColor: cfg.bg,
        border: `1px solid ${cfg.dot}40`,
        color: cfg.text,
        fontSize: '0.75rem',
        fontWeight: 700,
        letterSpacing: '0.05em',
      }}
    >
      <span
        style={{
          width: 8,
          height: 8,
          borderRadius: '50%',
          backgroundColor: cfg.dot,
          boxShadow: state === 'CONNECTED' ? `0 0 8px ${cfg.dot}` : 'none',
        }}
        className={state === 'CONNECTED' ? 'animate-pulse-glow' : ''}
      />
      {cfg.label}
    </div>
  );
};
