import React from 'react';
import { NavLink } from 'react-router-dom';

export const Sidebar: React.FC = () => {
  const navItems = [
    { label: 'Live Dashboard', path: '/' },
    { label: 'Transactions', path: '/transactions' },
    { label: 'Risk Monitor', path: '/risks' },
  ];

  return (
    <aside
      style={{
        width: '220px',
        backgroundColor: '#0b1120',
        borderRight: '1px solid #1e293b',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        padding: '24px 16px',
        minHeight: 'calc(100vh - 64px)',
      }}
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
        <div style={{ fontSize: '0.6875rem', fontWeight: 700, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.08em', padding: '0 12px 8px 12px' }}>
          Navigation
        </div>
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            style={({ isActive }) => ({
              display: 'flex',
              alignItems: 'center',
              padding: '10px 14px',
              borderRadius: '8px',
              fontSize: '0.875rem',
              fontWeight: 600,
              textDecoration: 'none',
              transition: 'all 0.15s ease',
              backgroundColor: isActive ? 'rgba(59, 130, 246, 0.15)' : 'transparent',
              color: isActive ? '#38bdf8' : '#94a3b8',
              border: isActive ? '1px solid rgba(59, 130, 246, 0.3)' : '1px solid transparent',
            })}
          >
            {item.label}
          </NavLink>
        ))}
      </div>

      <div style={{ padding: '16px 12px', backgroundColor: '#090d16', borderRadius: '8px', border: '1px solid #1e293b', fontSize: '0.75rem', color: '#64748b' }}>
        <div style={{ fontWeight: 600, color: '#94a3b8', marginBottom: '4px' }}>Decision Support</div>
        <div>Final Year Project</div>
        <div style={{ color: '#475569', fontSize: '0.6875rem', marginTop: '4px' }}>v1.0.0 Production Prototype</div>
      </div>
    </aside>
  );
};
