import React from 'react';

interface RiskSummaryProps {
  lowCount: number;
  mediumCount: number;
  highCount: number;
  total: number;
}

export const RiskSummary: React.FC<RiskSummaryProps> = ({
  lowCount,
  mediumCount,
  highCount,
  total,
}) => {
  const lowPct = total > 0 ? (lowCount / total) * 100 : 0;
  const medPct = total > 0 ? (mediumCount / total) * 100 : 0;
  const highPct = total > 0 ? (highCount / total) * 100 : 0;

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
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <h3 style={{ fontSize: '0.875rem', fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Real-Time Risk Distribution
        </h3>
        <span style={{ fontSize: '0.75rem', color: '#64748b' }}>
          Session Events: <strong style={{ color: '#f8fafc' }}>{total}</strong>
        </span>
      </div>

      {/* Stacked Percentage Bar */}
      <div
        style={{
          width: '100%',
          height: '10px',
          backgroundColor: '#1e293b',
          borderRadius: '5px',
          display: 'flex',
          overflow: 'hidden',
          marginBottom: '16px',
        }}
      >
        <div style={{ width: `${lowPct}%`, backgroundColor: '#10b981', transition: 'width 0.3s ease' }} />
        <div style={{ width: `${medPct}%`, backgroundColor: '#f59e0b', transition: 'width 0.3s ease' }} />
        <div style={{ width: `${highPct}%`, backgroundColor: '#ef4444', transition: 'width 0.3s ease' }} />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px' }}>
        <div style={{ padding: '10px', backgroundColor: '#090d16', borderRadius: '8px', border: '1px solid #1e293b' }}>
          <div style={{ fontSize: '0.75rem', color: '#10b981', fontWeight: 600 }}>LOW RISK</div>
          <div style={{ fontSize: '1.25rem', fontWeight: 700, color: '#f8fafc' }}>{lowCount}</div>
          <div style={{ fontSize: '0.7rem', color: '#64748b' }}>{lowPct.toFixed(1)}% of total</div>
        </div>

        <div style={{ padding: '10px', backgroundColor: '#090d16', borderRadius: '8px', border: '1px solid #1e293b' }}>
          <div style={{ fontSize: '0.75rem', color: '#f59e0b', fontWeight: 600 }}>MEDIUM RISK</div>
          <div style={{ fontSize: '1.25rem', fontWeight: 700, color: '#f8fafc' }}>{mediumCount}</div>
          <div style={{ fontSize: '0.7rem', color: '#64748b' }}>{medPct.toFixed(1)}% of total</div>
        </div>

        <div style={{ padding: '10px', backgroundColor: '#090d16', borderRadius: '8px', border: '1px solid #1e293b' }}>
          <div style={{ fontSize: '0.75rem', color: '#ef4444', fontWeight: 600 }}>HIGH RISK</div>
          <div style={{ fontSize: '1.25rem', fontWeight: 700, color: '#f8fafc' }}>{highCount}</div>
          <div style={{ fontSize: '0.7rem', color: '#64748b' }}>{highPct.toFixed(1)}% of total</div>
        </div>
      </div>
    </div>
  );
};
