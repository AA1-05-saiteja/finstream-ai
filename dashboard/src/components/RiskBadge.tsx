import React from 'react';

interface RiskBadgeProps {
  level: 'LOW' | 'MEDIUM' | 'HIGH' | string;
  size?: 'sm' | 'md' | 'lg';
}

export const RiskBadge: React.FC<RiskBadgeProps> = ({ level, size = 'md' }) => {
  const normalized = (level || 'LOW').toUpperCase();

  let bg = 'rgba(16, 185, 129, 0.15)';
  let text = '#10b981';
  let border = 'rgba(16, 185, 129, 0.3)';

  if (normalized === 'HIGH') {
    bg = 'rgba(239, 68, 68, 0.2)';
    text = '#ef4444';
    border = 'rgba(239, 68, 68, 0.4)';
  } else if (normalized === 'MEDIUM') {
    bg = 'rgba(245, 158, 11, 0.2)';
    text = '#f59e0b';
    border = 'rgba(245, 158, 11, 0.4)';
  }

  const sizeStyles = {
    sm: { padding: '2px 8px', fontSize: '0.75rem' },
    md: { padding: '4px 12px', fontSize: '0.8125rem' },
    lg: { padding: '6px 16px', fontSize: '0.875rem' },
  }[size];

  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '6px',
        fontWeight: 600,
        borderRadius: '9999px',
        backgroundColor: bg,
        color: text,
        border: `1px solid ${border}`,
        textTransform: 'uppercase',
        letterSpacing: '0.05em',
        ...sizeStyles,
      }}
    >
      <span
        style={{
          width: size === 'sm' ? 5 : 6,
          height: size === 'sm' ? 5 : 6,
          borderRadius: '50%',
          backgroundColor: text,
        }}
      />
      {normalized}
    </span>
  );
};
