import React from 'react';

interface ErrorStateProps {
  title?: string;
  message: string;
  onRetry?: () => void;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = 'Failed to load data',
  message,
  onRetry,
}) => {
  return (
    <div
      style={{
        backgroundColor: 'rgba(239, 68, 68, 0.08)',
        border: '1px solid rgba(239, 68, 68, 0.3)',
        borderRadius: '12px',
        padding: '24px',
        textAlign: 'center',
        margin: '20px 0',
      }}
    >
      <div style={{ color: '#ef4444', fontWeight: 600, fontSize: '1rem', marginBottom: '6px' }}>
        {title}
      </div>
      <div style={{ color: '#94a3b8', fontSize: '0.875rem', marginBottom: onRetry ? '16px' : '0' }}>
        {message}
      </div>
      {onRetry && (
        <button
          onClick={onRetry}
          style={{
            padding: '8px 18px',
            backgroundColor: '#ef4444',
            color: '#ffffff',
            borderRadius: '6px',
            border: 'none',
            fontWeight: 600,
            fontSize: '0.8125rem',
            cursor: 'pointer',
          }}
        >
          Retry Request
        </button>
      )}
    </div>
  );
};
