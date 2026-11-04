/**
 * Audit-log query hooks (SA / OWNER / GM only) — mirrors
 * backend `app/routers/audit_log.py`.
 */

import { useQuery } from '@tanstack/react-query';
import { getPage, getSingle } from '@/lib/api';
import type { Page } from '@/lib/types';

export interface AuditLogEntry {
  id: string;
  ts: string;
  action: string;
  entity_type?: string | null;
  entity_id?: string | null;
  actor_id?: string | null;
  actor_email?: string | null;
  actor_role?: string | null;
  branch_id?: string | null;
  before?: Record<string, unknown> | null;
  after?: Record<string, unknown> | null;
  reason?: string | null;
  ip?: string | null;
  user_agent?: string | null;
}

export interface AuditLogSummary {
  total: number;
  by_action: Record<string, number>;
}

export interface AuditLogParams {
  page?: number;
  page_size?: number;
  action?: string;
  entity_type?: string;
  entity_id?: string;
  actor_id?: string;
  actor_email?: string;
  from_ts?: string;
  to_ts?: string;
}

export function useAuditLog(params?: AuditLogParams) {
  return useQuery<Page<AuditLogEntry>>({
    queryKey: ['audit-log', params ?? {}],
    queryFn: () => getPage<AuditLogEntry>('/audit-log', params as Record<string, unknown>),
  });
}

export function useAuditLogSummary(params?: { from_ts?: string; to_ts?: string }) {
  return useQuery<AuditLogSummary>({
    queryKey: ['audit-log', 'summary', params ?? {}],
    queryFn: () => getSingle<AuditLogSummary>('/audit-log/summary', params as Record<string, unknown>),
  });
}
