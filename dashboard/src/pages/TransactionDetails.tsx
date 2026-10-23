import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { getTransaction } from '../api/transactions';
import { TransactionDetail } from '../types/api';
import { RiskBadge } from '../components/RiskBadge';
import { ShapChart } from '../components/ShapChart';
import { LoadingState } from '../components/LoadingState';
import { ErrorState } from '../components/ErrorState';

export const TransactionDetails: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [detail, setDetail] = useState<TransactionDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDetail = async () => {
    if (!id) return;
    try {
      setLoading(true);
      setError(null);
      const res = await getTransaction(id);
      setDetail(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Transaction not found');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDetail();
  }, [id]);

  if (loading) {
    return <LoadingState message={`Fetching details for transaction ${id}...`} />;
  }

  if (error || !detail) {
    return (
      <div style={{ padding: '28px 32px' }}>
        <Link to="/transactions" style={{ color: '#38bdf8', textDecoration: 'none', fontSize: '0.875rem' }}>
          ← Back to Transactions
        </Link>
        <ErrorState message={error || 'Transaction not found'} onRetry={fetchDetail} />
      </div>
    );
  }

  const { transaction: tx, risk, explanations } = detail;

  const formatCurrency = (val: number, cur: string = 'INR') => {
    return `${cur === 'INR' ? '₹' : cur + ' '}${val.toLocaleString('en-IN', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })}`;
  };

  const formatDisplayTimestamp = (iso?: string | null) => {
    if (!iso) return '—';
    try {
      if (typeof iso === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(iso.trim())) {
        const [y, m, d] = iso.trim().split('-');
        const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
        return `${d} ${months[parseInt(m, 10) - 1]} ${y}`;
      }
      const d = new Date(iso);
      if (isNaN(d.getTime())) return String(iso);
      const day = String(d.getDate()).padStart(2, '0');
      const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
      const month = months[d.getMonth()];
      const year = d.getFullYear();
      let hours = d.getHours();
      const minutes = String(d.getMinutes()).padStart(2, '0');
      const ampm = hours >= 12 ? 'PM' : 'AM';
      hours = hours % 12;
      hours = hours ? hours : 12;
      const strHours = String(hours).padStart(2, '0');
      return `${day} ${month} ${year}, ${strHours}:${minutes} ${ampm}`;
    } catch {
      return String(iso);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', padding: '28px 32px' }}>
      {/* Navigation Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <Link to="/transactions" style={{ color: '#38bdf8', textDecoration: 'none', fontSize: '0.875rem', fontWeight: 600 }}>
            ← Back to Transactions
          </Link>
          <h1 style={{ fontSize: '1.75rem', fontWeight: 800, color: '#f8fafc', marginTop: '8px', fontFamily: 'var(--font-mono)' }}>
            {tx.transaction_id}
          </h1>
        </div>

        {risk && <RiskBadge level={risk.risk_level} size="lg" />}
      </div>

      {/* Grid: Transaction Metadata + Risk Evaluation */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '20px' }}>
        {/* Transaction Metadata Card */}
        <div
          style={{
            backgroundColor: '#0f172a',
            border: '1px solid #1e293b',
            borderRadius: '12px',
            padding: '24px',
            boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.2)',
          }}
        >
          <h3 style={{ fontSize: '1rem', fontWeight: 600, color: '#f8fafc', marginBottom: '16px' }}>
            Event Metadata
          </h3>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', fontSize: '0.875rem' }}>
            <div>
              <span style={{ color: '#64748b', fontSize: '0.75rem' }}>Amount</span>
              <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#f8fafc' }}>
                {formatCurrency(tx.amount, tx.currency)}
              </div>
            </div>

            <div>
              <span style={{ color: '#64748b', fontSize: '0.75rem' }}>Account ID</span>
              <div>
                <Link to={`/accounts/${tx.account_id}`} style={{ color: '#38bdf8', fontWeight: 600, textDecoration: 'none', fontFamily: 'var(--font-mono)' }}>
                  {tx.account_id}
                </Link>
              </div>
            </div>

            <div>
              <span style={{ color: '#64748b', fontSize: '0.75rem' }}>Merchant & Vertical</span>
              <div style={{ color: '#f8fafc', fontWeight: 500 }}>{tx.merchant_id} ({tx.merchant_category})</div>
            </div>

            <div>
              <span style={{ color: '#64748b', fontSize: '0.75rem' }}>Location & Channel</span>
              <div style={{ color: '#f8fafc', fontWeight: 500 }}>{tx.city} • {tx.channel}</div>
            </div>

            <div>
              <span style={{ color: '#64748b', fontSize: '0.75rem' }}>Device ID</span>
              <div style={{ color: '#cbd5e1', fontFamily: 'var(--font-mono)' }}>{tx.device_id}</div>
            </div>

            <div>
              <span style={{ color: '#64748b', fontSize: '0.75rem' }}>Scenario Classification</span>
              <div style={{ color: '#cbd5e1', fontWeight: 600 }}>{tx.scenario_label}</div>
            </div>

            <div style={{ gridColumn: 'span 2' }}>
              <span style={{ color: '#64748b', fontSize: '0.75rem' }}>Event Timestamp</span>
              <div style={{ color: '#cbd5e1', fontFamily: 'var(--font-mono)' }}>{formatDisplayTimestamp(tx.timestamp)}</div>
            </div>
          </div>
        </div>

        {/* Risk Intelligence Card */}
        <div
          style={{
            backgroundColor: '#0f172a',
            border: '1px solid #1e293b',
            borderRadius: '12px',
            padding: '24px',
            boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.2)',
          }}
        >
          <h3 style={{ fontSize: '1rem', fontWeight: 600, color: '#f8fafc', marginBottom: '16px' }}>
            Anomaly Risk Assessment
          </h3>

          {risk ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div style={{ padding: '16px', backgroundColor: '#090d16', borderRadius: '8px', border: '1px solid #1e293b' }}>
                <span style={{ color: '#64748b', fontSize: '0.75rem' }}>Hybrid Risk Score (0.70 XGB + 0.30 IF)</span>
                <div style={{ fontSize: '1.75rem', fontWeight: 800, color: '#f8fafc', fontFamily: 'var(--font-mono)' }}>
                  {risk.hybrid_risk_score.toFixed(4)}
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div style={{ padding: '12px', backgroundColor: '#090d16', borderRadius: '8px', border: '1px solid #1e293b' }}>
                  <span style={{ color: '#64748b', fontSize: '0.75rem' }}>XGBoost Probability</span>
                  <div style={{ fontSize: '1.125rem', fontWeight: 700, color: '#38bdf8', fontFamily: 'var(--font-mono)' }}>
                    {risk.xgboost_probability.toFixed(4)}
                  </div>
                </div>

                <div style={{ padding: '12px', backgroundColor: '#090d16', borderRadius: '8px', border: '1px solid #1e293b' }}>
                  <span style={{ color: '#64748b', fontSize: '0.75rem' }}>Isolation Forest (Norm)</span>
                  <div style={{ fontSize: '1.125rem', fontWeight: 700, color: '#38bdf8', fontFamily: 'var(--font-mono)' }}>
                    {risk.isolation_forest_normalized.toFixed(4)}
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div style={{ color: '#64748b', padding: '20px 0' }}>No risk evaluation recorded for this transaction.</div>
          )}
        </div>
      </div>

      {/* SHAP Explanations Section */}
      <ShapChart explanations={explanations} />
    </div>
  );
};
