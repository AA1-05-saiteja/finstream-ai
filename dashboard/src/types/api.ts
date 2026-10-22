/**
 * FinStream AI - Frontend Type Definitions
 * Typed contracts matching FastAPI schemas and WebSocket event payloads.
 */

export interface Transaction {
  transaction_id: string;
  timestamp: string;
  account_id: string;
  amount: number;
  currency: string;
  merchant_id: string;
  merchant_category: string;
  city: string;
  device_id: string;
  channel: string;
  card_present: boolean;
  transaction_type: string;
  scenario_label: string;
  created_at?: string | null;
}

export interface SHAPExplanation {
  id?: number;
  feature: string;
  feature_value: number;
  shap_value: number;
  absolute_shap_value: number;
  direction: 'increases_anomaly' | 'decreases_anomaly' | 'neutral';
  rank: number;
}

export interface RiskAssessment {
  id?: number;
  transaction_id: string;
  xgboost_probability: number;
  isolation_forest_score: number;
  isolation_forest_normalized: number;
  hybrid_risk_score: number;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH';
  created_at?: string | null;
  top_shap_features?: SHAPExplanation[];
}

export interface TransactionDetail {
  transaction: Transaction;
  risk?: RiskAssessment | null;
  explanations: SHAPExplanation[];
}

export interface AccountRisk {
  account_id: string;
  transaction_id?: string | null;
  amount?: number | null;
  hybrid_risk_score: number;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH';
  xgboost_probability?: number | null;
  isolation_forest_normalized?: number | null;
  source: string;
  timestamp?: string | null;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
  timestamp: string;
}

export interface DependencyHealthResponse {
  api: string;
  postgresql: 'available' | 'unavailable';
  redis: 'available' | 'unavailable';
  details: {
    postgresql_connected: boolean;
    redis_connected: boolean;
  };
}

export interface ApiError {
  error: string;
  message: string;
  detail?: string | null;
}
