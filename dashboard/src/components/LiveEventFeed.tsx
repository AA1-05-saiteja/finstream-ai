import React from 'react';
import { Link } from 'react-router-dom';
import { RiskBadge } from './RiskBadge';
import { TransactionRiskAssessedPayload } from '../websocket/websocketTypes';

interface LiveEventFeedProps {
  events: TransactionRiskAssessedPayload[];
  maxDisplay?: number;
}

export const LiveEventFeed: React.FC<LiveEventFeedProps> = ({ events, maxDisplay = 50 }) => {
  const displayedEvents = events.slice(0, maxDisplay);

  const formatCurrency = (val: number, cur: string = 'INR') => {
    return `${cur === 'INR' ? '₹' : cur + ' '}${val.toLocaleString('en-IN', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })}`;
  };

  return (
    <div
      style={{
        backgroundColor: '#0f172a',
        border: '1px solid #1e293b',
        borderRadius: '12px',
        padding: '20px 24px',
        boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.2)',
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span
            style={{
              width: 8,
              height: 8,
              borderRadius: '50%',
              backgroundColor: '#38bdf8',
            }}
            className="animate-pulse-glow"
          />
          <h3 style={{ fontSize: '0.875rem', fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Live Transaction Stream
          </h3>
        </div>
        <span style={{ fontSize: '0.75rem', color: '#64748b' }}>
          Real-Time Ticker ({events.length} events received)
        </span>
      </div>

      {displayedEvents.length === 0 ? (
        <div style={{ padding: '60px 20px', textAlign: 'center', color: '#64748b', fontSize: '0.875rem' }}>
          Waiting for live streaming transactions from Kafka & ML inference pipeline...
        </div>
      ) : (
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '10px',
            overflowY: 'auto',
            maxHeight: '480px',
            paddingRight: '4px',
          }}
        >
          {displayedEvents.map((evt, index) => {
            const isHigh = evt.risk_level === 'HIGH';
            const isNewest = index === 0;

            return (
              <div
                key={`${evt.transaction_id}-${index}`}
                style={{
                  padding: '12px 16px',
                  borderRadius: '8px',
                  backgroundColor: isHigh ? 'rgba(239, 68, 68, 0.08)' : '#090d16',
                  border: isHigh ? '1px solid rgba(239, 68, 68, 0.3)' : '1px solid #1e293b',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  transition: 'all 0.2s ease',
                }}
                className={isNewest ? 'animate-flash' : ''}
              >
                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Link
                      to={`/transactions/${evt.transaction_id}`}
                      style={{ color: '#38bdf8', fontWeight: 600, fontSize: '0.875rem', textDecoration: 'none', fontFamily: 'var(--font-mono)' }}
                    >
                      {evt.transaction_id}
                    </Link>
                    <span style={{ color: '#64748b', fontSize: '0.75rem' }}>•</span>
                    <Link
                      to={`/accounts/${evt.account_id}`}
                      style={{ color: '#94a3b8', fontSize: '0.75rem', textDecoration: 'none', fontFamily: 'var(--font-mono)' }}
                    >
                      {evt.account_id}
                    </Link>
                  </div>

                  <div style={{ fontSize: '0.75rem', color: '#64748b' }}>
                    {evt.merchant_category ? `${evt.merchant_category} in ${evt.city || 'India'}` : 'Transaction Event'}
                  </div>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '6px' }}>
                  <div style={{ fontWeight: 700, color: '#f8fafc', fontSize: '0.9375rem' }}>
                    {formatCurrency(evt.amount, evt.currency)}
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '0.75rem', color: '#94a3b8', fontFamily: 'var(--font-mono)' }}>
                      score: {evt.hybrid_risk_score.toFixed(4)}
                    </span>
                    <RiskBadge level={evt.risk_level} size="sm" />
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
