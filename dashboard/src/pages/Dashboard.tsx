import React, { useEffect, useState } from 'react';
import { getDependenciesHealth } from '../api/health';
import { getTransactions } from '../api/transactions';
import { DependencyHealthResponse, Transaction } from '../types/api';
import { TransactionRiskAssessedPayload, WebSocketConnectionState } from '../websocket/websocketTypes';
import { wsClient } from '../websocket/websocketClient';
import { StatusCard } from '../components/StatusCard';
import { HealthStatus } from '../components/HealthStatus';
import { RiskSummary } from '../components/RiskSummary';
import { LiveEventFeed } from '../components/LiveEventFeed';
import { TransactionTable } from '../components/TransactionTable';
import { LoadingState } from '../components/LoadingState';
import { ErrorState } from '../components/ErrorState';

interface DashboardProps {
  wsState: WebSocketConnectionState;
}

export const Dashboard: React.FC<DashboardProps> = ({ wsState }) => {
  const [dependencies, setDependencies] = useState<DependencyHealthResponse | null>(null);
  const [liveEvents, setLiveEvents] = useState<TransactionRiskAssessedPayload[]>([]);
  const [recentTransactions, setRecentTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Session Risk Counters
  const [sessionLow, setSessionLow] = useState(0);
  const [sessionMed, setSessionMed] = useState(0);
  const [sessionHigh, setSessionHigh] = useState(0);

  // Fetch initial REST data
  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);

      const [depRes, txRes] = await Promise.all([
        getDependenciesHealth().catch(() => null),
        getTransactions({ limit: 10 }).catch(() => ({ items: [], total: 0, limit: 10, offset: 0 })),
      ]);

      if (depRes) setDependencies(depRes);
      if (txRes) setRecentTransactions(txRes.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  // Listen for live WebSocket streaming events
  useEffect(() => {
    const unsubscribe = wsClient.subscribe((event) => {
      if (event.event === 'transaction_risk_assessed') {
        const payload = event.data as TransactionRiskAssessedPayload;
        
        // Update in-memory event feed (newest first, max 100)
        setLiveEvents((prev) => [payload, ...prev.slice(0, 99)]);

        // Update session counters
        if (payload.risk_level === 'HIGH') setSessionHigh((c) => c + 1);
        else if (payload.risk_level === 'MEDIUM') setSessionMed((c) => c + 1);
        else setSessionLow((c) => c + 1);
      }
    });

    return () => unsubscribe();
  }, []);

  const totalSessionEvents = sessionLow + sessionMed + sessionHigh;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', padding: '28px 32px' }}>
      {/* Top Banner / Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h1 style={{ fontSize: '1.75rem', fontWeight: 800, color: '#f8fafc', letterSpacing: '-0.025em' }}>
            Real-Time Financial Intelligence
          </h1>
          <p style={{ color: '#94a3b8', fontSize: '0.875rem', marginTop: '4px' }}>
            Continuous stream monitoring, dual-model anomaly detection (XGBoost + Isolation Forest), and risk scoring.
          </p>
        </div>
      </div>

      {error && <ErrorState message={error} onRetry={fetchData} />}

      {/* KPI Cards Row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px' }}>
        <StatusCard
          title="Stream Events (Session)"
          value={totalSessionEvents}
          subtitle="Real-time events processed"
          variant="primary"
        />
        <StatusCard
          title="High Risk Alerts"
          value={sessionHigh}
          subtitle="Requires investigation"
          variant="danger"
        />
        <StatusCard
          title="Medium Risk Warnings"
          value={sessionMed}
          subtitle="Elevated deviation"
          variant="warning"
        />
        <StatusCard
          title="Normal Transactions"
          value={sessionLow}
          subtitle="Baseline behavior"
          variant="success"
        />
      </div>

      {/* Health & Risk Distribution Row */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
        <HealthStatus dependencies={dependencies} wsState={wsState} loading={loading} />
        <RiskSummary
          lowCount={sessionLow}
          mediumCount={sessionMed}
          highCount={sessionHigh}
          total={totalSessionEvents}
        />
      </div>

      {/* Live Stream & Historical Activity Row */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.1fr 1.3fr', gap: '20px' }}>
        <LiveEventFeed events={liveEvents} />

        <div
          style={{
            backgroundColor: '#0f172a',
            border: '1px solid #1e293b',
            borderRadius: '12px',
            padding: '20px 24px',
            boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.2)',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h3 style={{ fontSize: '0.875rem', fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Persisted Transaction History
            </h3>
            <span style={{ fontSize: '0.75rem', color: '#64748b' }}>Latest from PostgreSQL</span>
          </div>

          {loading && recentTransactions.length === 0 ? (
            <LoadingState message="Loading persisted transactions..." />
          ) : (
            <TransactionTable transactions={recentTransactions} />
          )}
        </div>
      </div>
    </div>
  );
};
