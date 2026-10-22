/**
 * FinStream AI - HTTP REST Client
 * Fetch abstraction with query string serialization and standard error handling.
 */

import { ApiError } from '../types/api';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

export class ApiClientError extends Error {
  public status: number;
  public apiError?: ApiError;

  constructor(message: string, status: number, apiError?: ApiError) {
    super(message);
    this.name = 'ApiClientError';
    this.status = status;
    this.apiError = apiError;
  }
}

export async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };

  try {
    const response = await fetch(url, { ...options, headers });
    
    if (!response.ok) {
      let errorBody: ApiError | undefined;
      try {
        errorBody = await response.json();
      } catch {
        // Ignored if response is not json
      }
      
      const errorMsg = errorBody?.message || `Request failed with status ${response.status}`;
      throw new ApiClientError(errorMsg, response.status, errorBody);
    }

    return (await response.json()) as T;
  } catch (err) {
    if (err instanceof ApiClientError) {
      throw err;
    }
    throw new ApiClientError(
      err instanceof Error ? err.message : 'Network connection failed',
      0
    );
  }
}

export function buildQueryString(params: Record<string, any>): string {
  const query = new URLSearchParams();
  for (const [key, val] of Object.entries(params)) {
    if (val !== undefined && val !== null && val !== '') {
      query.append(key, String(val));
    }
  }
  const str = query.toString();
  return str ? `?${str}` : '';
}
