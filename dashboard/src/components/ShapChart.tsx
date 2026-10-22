import React from 'react';
import { SHAPExplanation } from '../types/api';

interface ShapChartProps {
  explanations: SHAPExplanation[];
}

export const ShapChart: React.FC<ShapChartProps> = ({ explanations }) => {
  if (!explanations || explanations.length === 0) {
    return (
      <div style={{ padding: '30px 20px', textAlign: 'center', color: '#64748b', backgroundColor: '#090d16', borderRadius: '8px', border: '1px solid #1e293b' }}>
        No SHAP local explanation factors available for this transaction.
      </div>
    );
  }

  // Calculate max absolute contribution for scaling bars
  const maxAbs = Math.max(...explanations.map((e) => Math.abs(e.shap_value)), 0.001);

  return (
    <div
      style={{
        backgroundColor: '#0f172a',
        border: '1px solid #1e293b',
        borderRadius: '12px',
        padding: '24px',
        boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.2)',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
        <h3 style={{ fontSize: '1rem', fontWeight: 600, color: '#f8fafc' }}>
          Top Feature Attributions (SHAP Local Explanation)
        </h3>
        <span style={{ fontSize: '0.75rem', color: '#64748b' }}>
          Model: <strong style={{ color: '#38bdf8' }}>XGBoost TreeExplainer</strong>
        </span>
      </div>

      <p style={{ fontSize: '0.8125rem', color: '#94a3b8', marginBottom: '20px' }}>
        Shows which behavioral and velocity features pushed the risk score higher (red) or lower (green).
      </p>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
        {explanations.map((item, idx) => {
          const isPositive = item.shap_value > 0;
          const barWidth = Math.min((Math.abs(item.shap_value) / maxAbs) * 100, 100);
          const barColor = isPositive ? '#ef4444' : '#10b981';
          const badgeBg = isPositive ? 'rgba(239, 68, 68, 0.15)' : 'rgba(16, 185, 129, 0.15)';
          const badgeText = isPositive ? '#f87171' : '#34d399';

          return (
            <div
              key={`${item.feature}-${idx}`}
              style={{
                padding: '12px 16px',
                backgroundColor: '#090d16',
                borderRadius: '8px',
                border: '1px solid #1e293b',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#64748b', width: '20px' }}>
                    #{item.rank || idx + 1}
                  </span>
                  <span style={{ fontWeight: 600, color: '#f8fafc', fontSize: '0.875rem' }}>
                    {item.feature}
                  </span>
                  <span style={{ fontSize: '0.75rem', color: '#64748b', fontFamily: 'var(--font-mono)' }}>
                    (val: {typeof item.feature_value === 'number' ? item.feature_value.toLocaleString() : item.feature_value})
                  </span>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <span
                    style={{
                      padding: '2px 8px',
                      borderRadius: '4px',
                      backgroundColor: badgeBg,
                      color: badgeText,
                      fontSize: '0.75rem',
                      fontWeight: 700,
                      fontFamily: 'var(--font-mono)',
                    }}
                  >
                    {item.shap_value >= 0 ? `+${item.shap_value.toFixed(4)}` : item.shap_value.toFixed(4)}
                  </span>
                  <span style={{ fontSize: '0.75rem', color: isPositive ? '#ef4444' : '#10b981', fontWeight: 600 }}>
                    {item.direction.replace('_', ' ')}
                  </span>
                </div>
              </div>

              {/* Magnitude Bar */}
              <div
                style={{
                  width: '100%',
                  height: '6px',
                  backgroundColor: '#1e293b',
                  borderRadius: '3px',
                  overflow: 'hidden',
                }}
              >
                <div
                  style={{
                    width: `${barWidth}%`,
                    height: '100%',
                    backgroundColor: barColor,
                    borderRadius: '3px',
                    transition: 'width 0.4s ease',
                  }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
