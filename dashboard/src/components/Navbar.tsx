import React from 'react';
import { Link } from 'react-router-dom';
import { ConnectionStatus } from './ConnectionStatus';
import { WebSocketConnectionState } from '../websocket/websocketTypes';

interface NavbarProps {
  wsState: WebSocketConnectionState;
}

export const Navbar: React.FC<NavbarProps> = ({ wsState }) => {
  return (
    <header
      style={{
        height: '64px',
        backgroundColor: '#0b1120',
        borderBottom: '1px solid #1e293b',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 24px',
        position: 'sticky',
        top: 0,
        zIndex: 50,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <Link to="/" style={{ display: 'flex', alignItems: 'center', gap: '10px', textDecoration: 'none' }}>
          <div
            style={{
              width: 32,
              height: 32,
              borderRadius: '8px',
              backgroundColor: '#3b82f6',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#ffffff',
              fontWeight: 800,
              fontSize: '1.125rem',
            }}
          >
            F
          </div>
          <div>
            <span style={{ fontSize: '1.125rem', fontWeight: 800, color: '#f8fafc', letterSpacing: '-0.025em' }}>
              FinStream <span style={{ color: '#38bdf8' }}>AI</span>
            </span>
          </div>
        </Link>
        <span
          style={{
            padding: '2px 8px',
            borderRadius: '4px',
            backgroundColor: 'rgba(56, 189, 248, 0.12)',
            color: '#38bdf8',
            fontSize: '0.6875rem',
            fontWeight: 700,
            letterSpacing: '0.05em',
            textTransform: 'uppercase',
          }}
        >
          Research Prototype
        </span>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        <ConnectionStatus state={wsState} />
        
        <div style={{ fontSize: '0.75rem', color: '#64748b', display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span>API:</span>
          <span style={{ color: '#94a3b8', fontFamily: 'var(--font-mono)' }}>http://localhost:8000</span>
        </div>
      </div>
    </header>
  );
};
