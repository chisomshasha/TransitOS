/**
 * Sprint D — settlement query hooks.
 *
 * Settlements are the financial close: a branch's revenue minus its
 * expenses for a period, with crew payroll on top.
 *
 *   draft → submitted → approved → paid
 *
 * Once approved the settlement is locked — the API refuses edits. The
 * UI mirrors that: the edit controls only appear while it is editable.
 */

import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseMutationResult,
  type UseQueryResult,
} from '@tanstack/react-query';
import { getPage, getSingle, patchSingle, postSingle } from '@/lib/api';
import type { Page } from '@/lib/types';

export type SettlementStatus =
  | 'draft'
  | 'submitted'
  | 'approved'
  | 'paid'
  | 'rejected';

export interface SettlementLine {
  trip_id: string;
  trip_date?: string | null;
  status?: string | null;
  route_name?: string | null;
  gross_revenue: number;
  trip_expenses: number;
  net: number;
  driver_id?: string | null;
  driver_name?: string | null;
  driver_pay: number;
  conductor_id?: string | null;
  conductor_name?: string | null;
  conductor_pay: number;
  cash_up_id?: string | null;
  cash_up_variance?: number | null;
}

export interface Settlement {
  id: string;
  branch_id: string;
  branch_name?: string | null;
  period_start: string;
  period_end: string;
  driver_rate: number;
  conductor_rate: number;
  notes?: string | null;
  status: SettlementStatus;
  lines: SettlementLine[];
  gross_revenue: number;
  trip_expenses: number;
  standalone_expenses: number;
  net_payable: number;
  driver_payroll: number;
  conductor_payroll: number;
  trip_count: number;
  submitted_at?: string | null;
  approved_at?: string | null;
  paid_at?: string | null;
  payment_reference?: string | null;
  rejection_reason?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface SettlementSummary {
  by_status: Record<string, { count: number; net_payable: number }>;
  totals: {
    gross_revenue: number;
    trip_expenses: number;
    standalone_expenses: number;
    net_payable: number;
    driver_payroll: number;
    conductor_payroll: number;
  };
  outstanding: number;
}

export function useSettlements(
  params?: Record<string, unknown>
): UseQueryResult<Page<Settlement>> {
  return useQuery({
    queryKey: ['settlements', params ?? {}],
    queryFn: () => getPage<Settlement>('/settlements', params),
    staleTime: 15_000,
  });
}

export function useSettlement(id: string): UseQueryResult<Settlement> {
  return useQuery({
    queryKey: ['settlements', id],
    queryFn: () => getSingle<Settlement>(`/settlements/${id}`),
    enabled: !!id,
  });
}

export function useSettlementSummary(
  params?: Record<string, unknown>
): UseQueryResult<SettlementSummary> {
  return useQuery({
    queryKey: ['settlements', 'summary', params ?? {}],
    queryFn: () => getSingle<SettlementSummary>('/settlements/summary', params),
    staleTime: 15_000,
  });
}

export interface GenerateSettlementBody {
  branch_id: string;
  period_start: string;
  period_end: string;
  driver_rate?: number;
  conductor_rate?: number;
  notes?: string | null;
}

export function useGenerateSettlement(): UseMutationResult<
  Settlement,
  unknown,
  GenerateSettlementBody
> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body) =>
      postSingle<Settlement, GenerateSettlementBody>('/settlements/generate', body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['settlements'] });
    },
  });
}

export function useUpdateSettlement(id: string): UseMutationResult<
  Settlement,
  unknown,
  Record<string, unknown>
> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body) => patchSingle<Settlement>(`/settlements/${id}`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['settlements'] });
    },
  });
}

export function useSettlementAction(id: string): UseMutationResult<
  Settlement,
  unknown,
  { action: 'submit' | 'approve' | 'reject' | 'pay'; body?: Record<string, unknown> }
> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ action, body }) =>
      postSingle<Settlement>(`/settlements/${id}/${action}`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['settlements'] });
    },
  });
}

/** True while the settlement can still be edited or resubmitted. */
export function isSettlementEditable(status: SettlementStatus): boolean {
  return status === 'draft' || status === 'submitted' || status === 'rejected';
}

export const SETTLEMENT_STATUS_LABELS: Record<SettlementStatus, string> = {
  draft: 'Draft',
  submitted: 'Submitted',
  approved: 'Approved',
  paid: 'Paid',
  rejected: 'Rejected',
};
