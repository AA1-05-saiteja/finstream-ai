import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { getAccountRisk, getAccountTransactions } from '../api/accounts';
import { AccountRisk, Transaction } from '../types/api';
import { RiskBadge } from '../components/RiskBadge';
import { TransactionTable } from '../components/TransactionTable';
import { LoadingState } from '../components/LoadingState';
import { ErrorState } from '../components/ErrorState';

export const AccountDetails: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [accountRisk, setAccountRisk] = useState<AccountRisk | null>(null);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAccountData = async () => {
    if (!id) return;
    try {
      setLoading(true);
      setError(null);
      const [riskRes, txRes] = await Promise.all([
        getAccountRisk(id),
        getAccountTransactions(id, { limit: 50 }).catch(() => ({ items: [], total: 0, limit: 50, offset: 0 })),
      ]);
      setAccountRisk(riskRes);
      setTransactions(txRes.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Account data not found');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAccountData();
  }, [id]);

  if (loading) {
    return <LoadingState message={`Fetching risk profile for account ${id}...`} />;
  }

  if (error || !accountRisk) {
    return (
      <div style={{ padding: '28px 32px' }}>
        <Link to="/transactions" style={{ color: '#38bdf8', textDecoration: 'none', fontSize: '0.875rem' }}>
          ← Back to Transactions
        </Link>
        <ErrorState message={error || 'Account not found'} onRetry={fetchAccountData} />
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', padding: '28px 32px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <Link to="/transactions" style={{ color: '#38bdf8', textDecoration: 'none', fontSize: '0.875rem', fontWeight: 600 }}>
            ← Back to Transactions
          </Link>
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px', marginTop: '8px' }}>
            <h1 style={{ fontSize: '1.75rem', fontWeight: 800, color: '#f8fafc', fontFamily: 'var(--font-mono)' }}>
              Account Risk Profile: {accountRisk.account_id}
            </h1>
            <RiskBadge level={accountRisk.risk_level} size="lg" />
          </div>
        </div>

        <span
          style={{
            padding: '4px 12px',
            borderRadius: '9999px',
            backgroundColor: accountRisk.source === 'redis_hot_state' ? 'rgba(59, 130, 246, 0.15)' : 'rgba(100, 116, 139, 0.15)',
            color: accountRisk.source === 'redis_hot_state' ? '#38bdf8' : '#94a3b8',
            fontSize: '0.75rem',
            fontWeight: 600,
            border: '1px solid rgba(59, 130, 246, 0.3)',
          }}
        >
          Source: {accountRisk.source === 'redis_hot_state' ? 'Redis Hot Cache (Fast State)' : 'PostgreSQL Historical Fallback'}
        </span>
      </div>

      {/* Risk Metrics Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
        <div style={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '12px', padding: '20px' }}>
          <span style={{ color: '#94a3b8', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Latest Risk Score</span>
          <div style={{ fontSize: '1.75rem', fontWeight: 800, color: '#f8fafc', fontFamily: 'var(--font-mono)', marginTop: '4px' }}>
            {accountRisk.hybrid_risk_score.toFixed(4)}
          </div>
        </div>

        <div style={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '12px', padding: '20px' }}>
          <span style={{ color: '#94a3b8', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Latest Transaction ID</span>
          <div style={{ fontSize: '1.25rem', fontWeight: 700, color: '#38bdf8', fontFamily: 'var(--font-mono)', marginTop: '4px' }}>
            {accountRisk.transaction_id ? (
              <Link to={`/transactions/${accountRisk.transaction_id}`} style={{ color: '#38bdf8', textDecoration: 'none' }}>
                {accountRisk.transaction_id}
              </Link>
            ) : (
              'N/A'
            )}
          </div>
        </div>

        <div style={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '12px', padding: '20px' }}>
          <span style={{ color: '#94a3b8', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Account Total Transactions</span>
          <div style={{ fontSize: '1.75rem', fontWeight: 800, color: '#f8fafc', marginTop: '4px' }}>
            {transactions.length}
          </div>
        </div>
      </div>

      {/* Account Transaction History */}
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
          Account Transaction History
        </h3>

        <TransactionTable transactions={transactions} />
      </div>
    </div>
  );
};
