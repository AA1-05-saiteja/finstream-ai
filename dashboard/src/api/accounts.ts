/**
 * FinStream AI - Accounts API Client
 */

import { buildQueryString, request } from './client';
import { AccountRisk, PaginatedResponse, Transaction } from '../types/api';

export interface GetAccountTransactionsParams {
  limit?: number;
  offset?: number;
  start_time?: string;
  end_time?: string;
}

export async function getAccountRisk(accountId: string): Promise<AccountRisk> {
  return request<AccountRisk>(`/accounts/${encodeURIComponent(accountId)}/risk`);
}

export async function getAccountTransactions(
  accountId: string,
  params: GetAccountTransactionsParams = {}
): Promise<PaginatedResponse<Transaction>> {
  const query = buildQueryString(params);
  return request<PaginatedResponse<Transaction>>(
    `/accounts/${encodeURIComponent(accountId)}/transactions${query}`
  );
}
