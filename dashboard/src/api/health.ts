/**
 * FinStream AI - Health API Client
 */

import { request } from './client';
import { DependencyHealthResponse, HealthResponse } from '../types/api';

export async function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>('/health');
}

export async function getDependenciesHealth(): Promise<DependencyHealthResponse> {
  return request<DependencyHealthResponse>('/health/dependencies');
}
