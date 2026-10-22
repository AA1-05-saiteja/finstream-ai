/**
 * FinStream AI - WebSocket Streaming Types
 */

import { SHAPExplanation } from '../types/api';

export type WebSocketConnectionState =
  | 'CONNECTING'
  | 'CONNECTED'
  | 'DISCONNECTED'
  | 'RECONNECTING'
  | 'ERROR';

export interface TransactionRiskAssessedPayload {
  transaction_id: string;
  account_id: string;
  amount: number;
  currency: string;
  merchant_category?: string;
  city?: string;
  channel?: string;
  hybrid_risk_score: number;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH';
  xgboost_probability: number;
  isolation_forest_normalized: number;
  top_shap_features?: SHAPExplanation[];
}

export interface WebSocketEvent<T = any> {
  event: 'connection_established' | 'transaction_risk_assessed' | 'heartbeat' | string;
  version: string;
  timestamp: string;
  data: T;
}

export type WebSocketEventHandler = (event: WebSocketEvent) => void;
export type ConnectionStateChangeHandler = (state: WebSocketConnectionState) => void;
