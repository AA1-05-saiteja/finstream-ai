import React, { useEffect, useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { wsClient } from './websocket/websocketClient';
import { WebSocketConnectionState } from './websocket/websocketTypes';
import { Navbar } from './components/Navbar';
import { Sidebar } from './components/Sidebar';
import { Dashboard } from './pages/Dashboard';
import { Transactions } from './pages/Transactions';
import { TransactionDetails } from './pages/TransactionDetails';
import { Risks } from './pages/Risks';
import { RiskDetails } from './pages/RiskDetails';
import { AccountDetails } from './pages/AccountDetails';

export const App: React.FC = () => {
  const [wsState, setWsState] = useState<WebSocketConnectionState>('DISCONNECTED');

  useEffect(() => {
    // 1. Subscribe to WebSocket connection state changes
    const unsubState = wsClient.onStateChange((state) => {
      setWsState(state);
    });

    // 2. Initiate WebSocket connection to backend stream
    wsClient.connect();

    return () => {
      unsubState();
      wsClient.disconnect();
    };
  }, []);

  return (
    <BrowserRouter>
      <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh', backgroundColor: '#090d16' }}>
        <Navbar wsState={wsState} />

        <div style={{ display: 'flex', flex: 1 }}>
          <Sidebar />

          <main style={{ flex: 1, backgroundColor: '#090d16', minHeight: 'calc(100vh - 64px)', overflowY: 'auto' }}>
            <Routes>
              <Route path="/" element={<Dashboard wsState={wsState} />} />
              <Route path="/dashboard" element={<Navigate to="/" replace />} />
              <Route path="/transactions" element={<Transactions />} />
              <Route path="/transactions/:id" element={<TransactionDetails />} />
              <Route path="/risks" element={<Risks />} />
              <Route path="/risks/:id" element={<RiskDetails />} />
              <Route path="/accounts/:id" element={<AccountDetails />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </main>
        </div>
      </div>
    </BrowserRouter>
  );
};

export default App;
