import React from 'react';

interface StatusCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon?: React.ReactNode;
  trend?: string;
  variant?: 'default' | 'primary' | 'danger' | 'warning' | 'success';
}

export const StatusCard: React.FC<StatusCardProps> = ({
  title,
  value,
  subtitle,
  icon,
  trend,
  variant = 'default',
}) => {
  const borderColors = {
    default: '#1e293b',
    primary: '#3b82f6',
    danger: '#ef4444',
    warning: '#f59e0b',
    success: '#10b981',
  };

  return (
    <div
      style={{
        backgroundColor: '#0f172a',
        border: `1px solid ${borderColors[variant]}`,
        borderRadius: '12px',
        padding: '20px 24px',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.2)',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
        <span style={{ fontSize: '0.875rem', fontWeight: 500, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          {title}
        </span>
        {icon && (
          <div style={{ color: '#64748b', display: 'flex', alignItems: 'center' }}>
            {icon}
          </div>
        )}
      </div>

      <div style={{ fontSize: '1.875rem', fontWeight: 700, color: '#f8fafc', letterSpacing: '-0.025em', marginBottom: '4px' }}>
        {value}
      </div>

      {(subtitle || trend) && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.8125rem', color: '#64748b' }}>
          {trend && <span style={{ fontWeight: 600, color: '#38bdf8' }}>{trend}</span>}
          {subtitle && <span>{subtitle}</span>}
        </div>
      )}
    </div>
  );
};
