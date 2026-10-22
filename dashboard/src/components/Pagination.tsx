import React from 'react';

interface PaginationProps {
  total: number;
  limit: number;
  offset: number;
  onPageChange: (newOffset: number) => void;
}

export const Pagination: React.FC<PaginationProps> = ({
  total,
  limit,
  offset,
  onPageChange,
}) => {
  const currentPage = Math.floor(offset / limit) + 1;
  const totalPages = Math.ceil(total / limit) || 1;

  const hasPrev = offset > 0;
  const hasNext = offset + limit < total;

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '16px 20px',
        borderTop: '1px solid #1e293b',
        color: '#94a3b8',
        fontSize: '0.8125rem',
      }}
    >
      <div>
        Showing <span style={{ fontWeight: 600, color: '#f8fafc' }}>{total === 0 ? 0 : offset + 1}</span> to{' '}
        <span style={{ fontWeight: 600, color: '#f8fafc' }}>{Math.min(offset + limit, total)}</span> of{' '}
        <span style={{ fontWeight: 600, color: '#f8fafc' }}>{total}</span> entries
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <button
          onClick={() => onPageChange(Math.max(0, offset - limit))}
          disabled={!hasPrev}
          style={{
            padding: '6px 14px',
            borderRadius: '6px',
            backgroundColor: hasPrev ? '#1e293b' : '#0f172a',
            color: hasPrev ? '#f8fafc' : '#475569',
            border: '1px solid #334155',
            cursor: hasPrev ? 'pointer' : 'not-allowed',
            fontWeight: 500,
          }}
        >
          Previous
        </button>

        <span style={{ padding: '0 8px', fontWeight: 600, color: '#cbd5e1' }}>
          Page {currentPage} of {totalPages}
        </span>

        <button
          onClick={() => onPageChange(offset + limit)}
          disabled={!hasNext}
          style={{
            padding: '6px 14px',
            borderRadius: '6px',
            backgroundColor: hasNext ? '#1e293b' : '#0f172a',
            color: hasNext ? '#f8fafc' : '#475569',
            border: '1px solid #334155',
            cursor: hasNext ? 'pointer' : 'not-allowed',
            fontWeight: 500,
          }}
        >
          Next
        </button>
      </div>
    </div>
  );
};
