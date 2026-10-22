import React, { useEffect, useState } from 'react';
import { getTransactions } from '../api/transactions';
import { Transaction } from '../types/api';
import { TransactionTable } from '../components/TransactionTable';
import { Pagination } from '../components/Pagination';
import { LoadingState } from '../components/LoadingState';
import { ErrorState } from '../components/ErrorState';

export const Transactions: React.FC = () => {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [total, setTotal] = useState(0);
  const [limit] = useState(25);
  const [offset, setOffset] = useState(0);
  const [accountId, setAccountId] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchTx = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await getTransactions({
        limit,
        offset,
        account_id: accountId ? accountId.trim() : undefined,
      });
      setTransactions(res.items);
      setTotal(res.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch transactions');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTx();
  }, [offset, accountId]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setOffset(0);
    setAccountId(searchTerm);
  };

  const handleClear = () => {
    setSearchTerm('');
    setAccountId('');
    setOffset(0);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', padding: '28px 32px' }}>
      <div>
        <h1 style={{ fontSize: '1.75rem', fontWeight: 800, color: '#f8fafc', letterSpacing: '-0.025em' }}>
          Transaction History
        </h1>
        <p style={{ color: '#94a3b8', fontSize: '0.875rem', marginTop: '4px' }}>
          Audited immutable financial transaction events stored in PostgreSQL.
        </p>
      </div>

      {/* Filter / Search Bar */}
      <div
        style={{
          backgroundColor: '#0f172a',
          border: '1px solid #1e293b',
          borderRadius: '12px',
          padding: '16px 20px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: '16px',
        }}
      >
        <form onSubmit={handleSearch} style={{ display: 'flex', alignItems: 'center', gap: '10px', flex: 1, maxWidth: '450px' }}>
          <input
            type="text"
            placeholder="Filter by Account ID (e.g. ACC0042)..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{
              flex: 1,
              padding: '8px 14px',
              backgroundColor: '#090d16',
              border: '1px solid #334155',
              borderRadius: '6px',
              color: '#f8fafc',
              fontSize: '0.8125rem',
              outline: 'none',
              fontFamily: 'var(--font-mono)',
            }}
          />
          <button
            type="submit"
            style={{
              padding: '8px 16px',
              backgroundColor: '#3b82f6',
              color: '#ffffff',
              border: 'none',
              borderRadius: '6px',
              fontSize: '0.8125rem',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            Filter
          </button>
          {accountId && (
            <button
              type="button"
              onClick={handleClear}
              style={{
                padding: '8px 12px',
                backgroundColor: '#1e293b',
                color: '#94a3b8',
                border: '1px solid #334155',
                borderRadius: '6px',
                fontSize: '0.8125rem',
                cursor: 'pointer',
              }}
            >
              Clear
            </button>
          )}
        </form>

        <span style={{ fontSize: '0.8125rem', color: '#64748b' }}>
          Total Persisted: <strong style={{ color: '#f8fafc' }}>{total}</strong>
        </span>
      </div>

      {error && <ErrorState message={error} onRetry={fetchTx} />}

      {/* Main Table Container */}
      <div
        style={{
          backgroundColor: '#0f172a',
          border: '1px solid #1e293b',
          borderRadius: '12px',
          overflow: 'hidden',
          boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.2)',
        }}
      >
        {loading && transactions.length === 0 ? (
          <LoadingState message="Fetching transactions from database..." />
        ) : (
          <>
            <TransactionTable transactions={transactions} />
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
