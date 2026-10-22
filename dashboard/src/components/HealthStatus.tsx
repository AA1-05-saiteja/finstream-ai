import React from 'react';
import { DependencyHealthResponse } from '../types/api';
import { WebSocketConnectionState } from '../websocket/websocketTypes';

interface HealthStatusProps {
  dependencies: DependencyHealthResponse | null;
  wsState: WebSocketConnectionState;
  loading?: boolean;
}

export const HealthStatus: React.FC<HealthStatusProps> = ({ dependencies, wsState, loading }) => {
  const services = [
    {
      name: 'FastAPI Backend',
      status: dependencies?.api === 'ok' ? 'ONLINE' : 'CHECKING',
      isOk: dependencies?.api === 'ok',
    },
    {
      name: 'PostgreSQL Relational DB',
      status: dependencies?.postgresql === 'available' ? 'AVAILABLE' : 'OFFLINE',
      isOk: dependencies?.postgresql === 'available',
    },
    {
      name: 'Redis Cache & Hot State',
      status: dependencies?.redis === 'available' ? 'AVAILABLE' : 'OFFLINE',
      isOk: dependencies?.redis === 'available',
    },
    {
      name: 'WebSocket Stream',
      status: wsState,
      isOk: wsState === 'CONNECTED',
    },
  ];

  return (
    <div
      style={{
        backgroundColor: '#0f172a',
        border: '1px solid #1e293b',
        borderRadius: '12px',
        padding: '20px 24px',
        boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.2)',
      }}
    >
      <h3 style={{ fontSize: '0.875rem', fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '16px' }}>
        Infrastructure Health Status
      </h3>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '16px' }}>
        {services.map((svc) => (
          <div
            key={svc.name}
            style={{
              padding: '12px 16px',
              borderRadius: '8px',
              backgroundColor: '#090d16',
              border: '1px solid #1e293b',
              display: 'flex',
              flexDirection: 'column',
              gap: '6px',
            }}
          >
            <span style={{ fontSize: '0.75rem', color: '#64748b' }}>{svc.name}</span>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span
                style={{
                  width: 8,
                  height: 8,
                  borderRadius: '50%',
                  backgroundColor: svc.isOk ? '#10b981' : (loading ? '#f59e0b' : '#ef4444'),
                }}
              />
              <span style={{ fontSize: '0.8125rem', fontWeight: 600, color: svc.isOk ? '#10b981' : (loading ? '#f59e0b' : '#ef4444') }}>
                {loading && !dependencies ? 'CHECKING...' : svc.status}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
