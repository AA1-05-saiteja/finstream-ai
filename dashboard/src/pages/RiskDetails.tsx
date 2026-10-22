import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { getRisk, getShapExplanations } from '../api/risks';
import { RiskAssessment, SHAPExplanation } from '../types/api';
import { RiskBadge } from '../components/RiskBadge';
import { ShapChart } from '../components/ShapChart';
import { LoadingState } from '../components/LoadingState';
import { ErrorState } from '../components/ErrorState';

export const RiskDetails: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [risk, setRisk] = useState<RiskAssessment | null>(null);
  const [explanations, setExplanations] = useState<SHAPExplanation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchRiskAndShap = async () => {
    if (!id) return;
    try {
      setLoading(true);
      setError(null);
      const [riskRes, shapRes] = await Promise.all([
        getRisk(id),
        getShapExplanations(id).catch(() => []),
      ]);
      setRisk(riskRes);
      setExplanations(shapRes);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Risk assessment not found');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRiskAndShap();
  }, [id]);

  if (loading) {
    return <LoadingState message={`Fetching risk & SHAP attributions for ${id}...`} />;
  }

  if (error || !risk) {
    return (
      <div style={{ padding: '28px 32px' }}>
        <Link to="/risks" style={{ color: '#38bdf8', textDecoration: 'none', fontSize: '0.875rem' }}>
          ← Back to Risk Monitor
        </Link>
        <ErrorState message={error || 'Risk assessment not found'} onRetry={fetchRiskAndShap} />
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', padding: '28px 32px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <Link to="/risks" style={{ color: '#38bdf8', textDecoration: 'none', fontSize: '0.875rem', fontWeight: 600 }}>
            ← Back to Risk Monitor
          </Link>
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px', marginTop: '8px' }}>
            <h1 style={{ fontSize: '1.75rem', fontWeight: 800, color: '#f8fafc', fontFamily: 'var(--font-mono)' }}>
              Risk Assessment: {risk.transaction_id}
            </h1>
            <RiskBadge level={risk.risk_level} size="lg" />
          </div>
        </div>

        <Link
          to={`/transactions/${risk.transaction_id}`}
          style={{
            padding: '8px 16px',
            backgroundColor: '#3b82f6',
            color: '#ffffff',
            borderRadius: '6px',
            textDecoration: 'none',
            fontSize: '0.8125rem',
            fontWeight: 600,
          }}
        >
          View Full Transaction Details →
        </Link>
      </div>

      {/* Model Breakdown Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px' }}>
        <div
          style={{
            backgroundColor: '#0f172a',
            border: '1px solid #1e293b',
            borderRadius: '12px',
            padding: '20px',
            boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.2)',
          }}
        >
          <span style={{ color: '#94a3b8', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Supervised Model
          </span>
          <div style={{ fontSize: '1.125rem', fontWeight: 700, color: '#f8fafc', margin: '4px 0' }}>
            XGBoost Probability
          </div>
          <div style={{ fontSize: '1.75rem', fontWeight: 800, color: '#38bdf8', fontFamily: 'var(--font-mono)' }}>
            {risk.xgboost_probability.toFixed(4)}
          </div>
          <div style={{ color: '#64748b', fontSize: '0.75rem', marginTop: '4px' }}>
            Trained on synthetic anomaly labels
          </div>
        </div>

        <div
          style={{
            backgroundColor: '#0f172a',
            border: '1px solid #1e293b',
            borderRadius: '12px',
            padding: '20px',
            boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.2)',
          }}
        >
          <span style={{ color: '#94a3b8', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Unsupervised Model
          </span>
          <div style={{ fontSize: '1.125rem', fontWeight: 700, color: '#f8fafc', margin: '4px 0' }}>
            Isolation Forest (Normalized)
          </div>
          <div style={{ fontSize: '1.75rem', fontWeight: 800, color: '#38bdf8', fontFamily: 'var(--font-mono)' }}>
            {risk.isolation_forest_normalized.toFixed(4)}
          </div>
          <div style={{ color: '#64748b', fontSize: '0.75rem', marginTop: '4px' }}>
            Raw decision score: {risk.isolation_forest_score.toFixed(4)}
          </div>
        </div>

        <div
          style={{
            backgroundColor: '#0f172a',
            border: '1px solid #1e293b',
            borderRadius: '12px',
            padding: '20px',
            boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.2)',
          }}
        >
          <span style={{ color: '#94a3b8', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Combined Assessment
          </span>
          <div style={{ fontSize: '1.125rem', fontWeight: 700, color: '#f8fafc', margin: '4px 0' }}>
            Hybrid Risk Score
          </div>
          <div style={{ fontSize: '1.75rem', fontWeight: 800, color: '#f8fafc', fontFamily: 'var(--font-mono)' }}>
            {risk.hybrid_risk_score.toFixed(4)}
          </div>
          <div style={{ color: '#64748b', fontSize: '0.75rem', marginTop: '4px' }}>
            Weighting: 0.70 XGB + 0.30 IF
          </div>
        </div>
      </div>

      {/* SHAP Visualization */}
      <ShapChart explanations={explanations} />
    </div>
  );
};
