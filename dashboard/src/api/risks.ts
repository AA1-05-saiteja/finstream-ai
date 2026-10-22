/**
 * FinStream AI - Risks & SHAP API Client
 */

import { buildQueryString, request } from './client';
import { PaginatedResponse, RiskAssessment, SHAPExplanation } from '../types/api';

export interface GetRisksParams {
  limit?: number;
  offset?: number;
  risk_level?: 'LOW' | 'MEDIUM' | 'HIGH' | string;
  account_id?: string;
  start_time?: string;
  end_time?: string;
}

export async function getRisks(
  params: GetRisksParams = {}
): Promise<PaginatedResponse<RiskAssessment>> {
  const query = buildQueryString(params);
  return request<PaginatedResponse<RiskAssessment>>(`/risks${query}`);
}

export async function getRisk(id: string): Promise<RiskAssessment> {
  return request<RiskAssessment>(`/risks/${encodeURIComponent(id)}`);
}

export async function getShapExplanations(id: string): Promise<SHAPExplanation[]> {
  return request<SHAPExplanation[]>(`/risks/${encodeURIComponent(id)}/explanations`);
}
