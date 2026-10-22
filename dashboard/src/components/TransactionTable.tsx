import React from 'react';
import { Link } from 'react-router-dom';
import { Transaction } from '../types/api';

interface TransactionTableProps {
  transactions: Transaction[];
  onSelectTransaction?: (tx: Transaction) => void;
}

export const TransactionTable: React.FC<TransactionTableProps> = ({ transactions }) => {
  if (transactions.length === 0) {
    return (
      <div style={{ padding: '40px 20px', textAlign: 'center', color: '#64748b' }}>
        No transactions found matching current criteria.
      </div>
    );
  }

  const formatCurrency = (val: number, cur: string = 'INR') => {
    return `${cur === 'INR' ? '₹' : cur + ' '}${val.toLocaleString('en-IN', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })}`;
  };

  const formatDate = (iso: string) => {
    try {
      const d = new Date(iso);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) + ' ' + d.toLocaleDateString([], { month: 'short', day: 'numeric' });
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
            <th style={{ padding: '12px 16px', fontWeight: 600 }}>Timestamp</th>
            <th style={{ padding: '12px 16px', fontWeight: 600 }}>Account</th>
            <th style={{ padding: '12px 16px', fontWeight: 600 }}>Amount</th>
            <th style={{ padding: '12px 16px', fontWeight: 600 }}>Merchant / Category</th>
            <th style={{ padding: '12px 16px', fontWeight: 600 }}>City</th>
            <th style={{ padding: '12px 16px', fontWeight: 600 }}>Channel</th>
            <th style={{ padding: '12px 16px', fontWeight: 600 }}>Scenario</th>
          </tr>
        </thead>
        <tbody>
          {transactions.map((tx) => (
            <tr
              key={tx.transaction_id}
              style={{
                borderBottom: '1px solid #1e293b',
                transition: 'background-color 0.15s ease',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = '#131d35')}
              onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
            >
              <td style={{ padding: '14px 16px', fontFamily: 'var(--font-mono)' }}>
                <Link
                  to={`/transactions/${tx.transaction_id}`}
                  style={{ color: '#38bdf8', fontWeight: 600, textDecoration: 'none' }}
                >
                  {tx.transaction_id}
                </Link>
              </td>
              <td style={{ padding: '14px 16px', color: '#94a3b8' }}>
                {formatDate(tx.timestamp)}
              </td>
              <td style={{ padding: '14px 16px', fontFamily: 'var(--font-mono)' }}>
                <Link
                  to={`/accounts/${tx.account_id}`}
                  style={{ color: '#cbd5e1', textDecoration: 'none' }}
                >
                  {tx.account_id}
                </Link>
              </td>
              <td style={{ padding: '14px 16px', fontWeight: 700, color: '#f8fafc' }}>
                {formatCurrency(tx.amount, tx.currency)}
              </td>
              <td style={{ padding: '14px 16px' }}>
                <div style={{ color: '#f8fafc', fontWeight: 500 }}>{tx.merchant_id}</div>
                <div style={{ color: '#64748b', fontSize: '0.75rem' }}>{tx.merchant_category}</div>
              </td>
              <td style={{ padding: '14px 16px', color: '#cbd5e1' }}>{tx.city}</td>
              <td style={{ padding: '14px 16px' }}>
                <span style={{ padding: '3px 8px', borderRadius: '4px', backgroundColor: '#1e293b', color: '#94a3b8', fontSize: '0.75rem', fontWeight: 600 }}>
                  {tx.channel}
                </span>
              </td>
              <td style={{ padding: '14px 16px' }}>
                <span
                  style={{
                    padding: '3px 8px',
                    borderRadius: '4px',
                    backgroundColor: tx.scenario_label === 'NORMAL' ? 'rgba(100, 116, 139, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                    color: tx.scenario_label === 'NORMAL' ? '#94a3b8' : '#f87171',
                    fontSize: '0.75rem',
                    fontWeight: 600,
                  }}
                >
                  {tx.scenario_label}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
