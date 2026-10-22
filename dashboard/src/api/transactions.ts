/**
 * FinStream AI - Transactions API Client
 */

import { buildQueryString, request } from './client';
import { PaginatedResponse, Transaction, TransactionDetail } from '../types/api';

export interface GetTransactionsParams {
  limit?: number;
  offset?: number;
  account_id?: string;
  start_time?: string;
  end_time?: string;
}

export async function getTransactions(
  params: GetTransactionsParams = {}
): Promise<PaginatedResponse<Transaction>> {
  const query = buildQueryString(params);
  return request<PaginatedResponse<Transaction>>(`/transactions${query}`);
}

export async function getTransaction(id: string): Promise<TransactionDetail> {
  return request<TransactionDetail>(`/transactions/${encodeURIComponent(id)}`);
}
