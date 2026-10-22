import React from 'react';
import { Link } from 'react-router-dom';
import { RiskAssessment } from '../types/api';
import { RiskBadge } from './RiskBadge';

interface RiskTableProps {
  risks: RiskAssessment[];
}

export const RiskTable: React.FC<RiskTableProps> = ({ risks }) => {
  if (risks.length === 0) {
    return (
      <div style={{ padding: '40px 20px', textAlign: 'center', color: '#64748b' }}>
        No risk assessments found matching current filter.
      </div>
    );
  }

  const formatDate = (iso?: string | null) => {
    if (!iso) return 'N/A';
    try {
      const d = new Date(iso);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } catch {
      return iso;
    }
  };

  return (
    <div style={{ width: '100%', overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.8125rem' }}>
        <thead>
          <tr style={{ backgroundColor: '#090d16', borderBottom: '1px solid #1e293b', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            <th style={{ padding: '12px 16px', fontWeight: 600 }}>Transaction ID</th>
            <th style={{ padding: '12px 16px', fontWeight: 600 }}>Risk Level</th>
            <th style={{ padding: '12px 16px', fontWeight: 600 }}>Hybrid Risk Score</th>
            <th style={{ padding: '12px 16px', fontWeight: 600 }}>XGBoost Prob</th>
            <th style={{ padding: '12px 16px', fontWeight: 600 }}>IF Score (Norm)</th>
            <th style={{ padding: '12px 16px', fontWeight: 600 }}>Timestamp</th>
            <th style={{ padding: '12px 16px', fontWeight: 600 }}>Actions</th>
          </tr>
        </thead>
        <tbody>
          {risks.map((risk) => (
            <tr
              key={risk.transaction_id}
              style={{
                borderBottom: '1px solid #1e293b',
                transition: 'background-color 0.15s ease',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = '#131d35')}
              onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
            >
              <td style={{ padding: '14px 16px', fontFamily: 'var(--font-mono)' }}>
                <Link
                  to={`/risks/${risk.transaction_id}`}
                  style={{ color: '#38bdf8', fontWeight: 600, textDecoration: 'none' }}
                >
                  {risk.transaction_id}
                </Link>
              </td>
              <td style={{ padding: '14px 16px' }}>
                <RiskBadge level={risk.risk_level} size="sm" />
              </td>
              <td style={{ padding: '14px 16px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <div
                    style={{
                      width: '60px',
                      height: '6px',
                      backgroundColor: '#1e293b',
                      borderRadius: '3px',
                      overflow: 'hidden',
                    }}
                  >
                    <div
                      style={{
                        width: `${Math.min(risk.hybrid_risk_score * 100, 100)}%`,
                        height: '100%',
                        backgroundColor:
                          risk.risk_level === 'HIGH'
                            ? '#ef4444'
                            : risk.risk_level === 'MEDIUM'
                            ? '#f59e0b'
                            : '#10b981',
                      }}
                    />
                  </div>
                  <span style={{ fontWeight: 700, color: '#f8fafc', fontFamily: 'var(--font-mono)' }}>
                    {risk.hybrid_risk_score.toFixed(4)}
                  </span>
                </div>
              </td>
              <td style={{ padding: '14px 16px', color: '#cbd5e1', fontFamily: 'var(--font-mono)' }}>
                {risk.xgboost_probability.toFixed(4)}
              </td>
              <td style={{ padding: '14px 16px', color: '#cbd5e1', fontFamily: 'var(--font-mono)' }}>
                {risk.isolation_forest_normalized.toFixed(4)}
              </td>
              <td style={{ padding: '14px 16px', color: '#94a3b8' }}>
                {formatDate(risk.created_at)}
              </td>
              <td style={{ padding: '14px 16px' }}>
                <Link
                  to={`/risks/${risk.transaction_id}`}
                  style={{
                    padding: '4px 10px',
                    borderRadius: '4px',
                    backgroundColor: 'rgba(56, 189, 248, 0.1)',
                    color: '#38bdf8',
                    border: '1px solid rgba(56, 189, 248, 0.3)',
                    textDecoration: 'none',
                    fontWeight: 600,
                    fontSize: '0.75rem',
                  }}
                >
                  Inspect SHAP
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
