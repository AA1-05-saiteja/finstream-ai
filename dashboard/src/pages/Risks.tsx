import React, { useEffect, useState } from 'react';
import { getRisks } from '../api/risks';
import { RiskAssessment } from '../types/api';
import { RiskTable } from '../components/RiskTable';
import { Pagination } from '../components/Pagination';
import { LoadingState } from '../components/LoadingState';
import { ErrorState } from '../components/ErrorState';

export const Risks: React.FC = () => {
  const [risks, setRisks] = useState<RiskAssessment[]>([]);
  const [total, setTotal] = useState(0);
  const [limit] = useState(25);
  const [offset, setOffset] = useState(0);
  const [riskTier, setRiskTier] = useState<string>('ALL');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchRisksData = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await getRisks({
        limit,
        offset,
        risk_level: riskTier !== 'ALL' ? riskTier : undefined,
      });
      setRisks(res.items);
      setTotal(res.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch risk assessments');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRisksData();
  }, [offset, riskTier]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', padding: '28px 32px' }}>
      <div>
        <h1 style={{ fontSize: '1.75rem', fontWeight: 800, color: '#f8fafc', letterSpacing: '-0.025em' }}>
          Anomaly & Risk Monitor
        </h1>
        <p style={{ color: '#94a3b8', fontSize: '0.875rem', marginTop: '4px' }}>
          Real-time dual-model risk scoring and unsupervised anomaly detection indices.
        </p>
      </div>

      {/* Tier Filter Bar */}
      <div
        style={{
          backgroundColor: '#0f172a',
          border: '1px solid #1e293b',
          borderRadius: '12px',
          padding: '16px 20px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {['ALL', 'HIGH', 'MEDIUM', 'LOW'].map((tier) => {
            const isSelected = riskTier === tier;
            return (
              <button
                key={tier}
                onClick={() => {
                  setRiskTier(tier);
                  setOffset(0);
                }}
                style={{
                  padding: '6px 14px',
                  borderRadius: '6px',
                  backgroundColor: isSelected ? '#3b82f6' : '#1e293b',
                  color: isSelected ? '#ffffff' : '#94a3b8',
                  border: '1px solid #334155',
                  fontSize: '0.8125rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                }}
              >
                {tier === 'ALL' ? 'All Tiers' : `${tier} Risk`}
              </button>
            );
          })}
        </div>

        <span style={{ fontSize: '0.8125rem', color: '#64748b' }}>
          Total Scored Records: <strong style={{ color: '#f8fafc' }}>{total}</strong>
        </span>
      </div>

      {error && <ErrorState message={error} onRetry={fetchRisksData} />}

      {/* Table Container */}
      <div
        style={{
          backgroundColor: '#0f172a',
          border: '1px solid #1e293b',
          borderRadius: '12px',
          overflow: 'hidden',
          boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.2)',
        }}
      >
        {loading && risks.length === 0 ? (
          <LoadingState message="Fetching risk evaluations..." />
        ) : (
          <>
            <RiskTable risks={risks} />
            <Pagination
              total={total}
              limit={limit}
              offset={offset}
              onPageChange={(newOffset) => setOffset(newOffset)}
            />
          </>
        )}
      </div>
    </div>
  );
};
