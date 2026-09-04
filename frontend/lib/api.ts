/**
 * axios instance + interceptors.
 *
 * - Request interceptor: read `accessToken` from auth store, attach
 *   `Authorization: Bearer <token>` if present.
 * - Response interceptor on 401: attempt /auth/refresh once with
 *   the refresh token, retry the original request, and only then
 *   log the user out.
 * - A request-dedupe lock (`refreshInFlight`) prevents parallel
 *   401s from triggering multiple refresh calls.
 */

import axios, {
  AxiosError,
  AxiosHeaders,
  type AxiosRequestConfig,
  type InternalAxiosRequestConfig,
} from 'axios';
import Constants from 'expo-constants';
import { useAuthStore } from '@/stores/authStore';
import { storage } from '@/lib/storage';
import type { ApiError, SingleResponse, Page } from '@/lib/types';

// Build a base URL from app.json `extra.apiUrl` (the only knob the
// owner turns when promoting the API to Railway). The fallback chain is:
//   1. ``extra.apiUrl`` from app.json (production URL)
//   2. ``process.env.EXPO_PUBLIC_API_URL`` (for ad-hoc overrides)
//   3. ``http://localhost:8000`` for the iOS simulator / dev web
//
// We log the resolved URL once on first request so misconfiguration is
// easy to spot in the Metro logs.
function resolveBaseURL(): string {
  const extra = (Constants.expoConfig?.extra ?? {}) as { apiUrl?: string };
  const fromExtra = extra.apiUrl;
  const fromEnv = process.env.EXPO_PUBLIC_API_URL;
  const fallback = 'http://localhost:8000';
  const resolved = (fromExtra || fromEnv || fallback).replace(/\/+$/, '');
  // Read/write the dedupe flag off `globalThis` so Hermes doesn't throw
  // a ReferenceError on the bare identifier in release builds.
  const g = globalThis as { __API_URL_LOGGED__?: boolean };
  if (!g.__API_URL_LOGGED__) {
    // eslint-disable-next-line no-console
    console.log('[TransitOS] API base URL =', resolved);
    g.__API_URL_LOGGED__ = true;
  }
  return resolved;
}

export const api = axios.create({
  baseURL: resolveBaseURL(),
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
});

// ---- request interceptor ----

api.interceptors.request.use((cfg: InternalAxiosRequestConfig) => {
  const token = useAuthStore.getState().accessToken;
  if (token) {
    if (cfg.headers instanceof AxiosHeaders) {
      cfg.headers.set('Authorization', `Bearer ${token}`);
    } else {
      const h: Record<string, string> = { ...((cfg.headers as Record<string, string> | undefined) || {}) };
      h.Authorization = `Bearer ${token}`;
      cfg.headers = h as unknown as InternalAxiosRequestConfig['headers'];
    }
  }
  return cfg;
});

// ---- 401 handling: dedupe + refresh + retry ----

type FailedRequest = {
  resolve: (token: string) => void;
  reject: (err: unknown) => void;
};

let refreshInFlight: Promise<string> | null = null;
const waiters: FailedRequest[] = [];

/** Proactive silent-refresh timer handle (cleared on logout / re-schedule). */
let silentRefreshTimer: ReturnType<typeof setTimeout> | null = null;

/**
 * Decode JWT payload without verifying the signature.
 * Used only to read `exp` for proactive refresh scheduling — never for auth.
 */
function decodeJwtExp(token: string): number | null {
  try {
    const parts = token.split('.');
    if (parts.length < 2) return null;
    // base64url → base64
    const b64 = parts[1].replace(/-/g, '+').replace(/_/g, '/');
    const padded = b64 + '='.repeat((4 - (b64.length % 4)) % 4);
    // atob is available in RN Hermes + web; Buffer is not guaranteed.
    const json =
      typeof atob === 'function'
        ? atob(padded)
        : // eslint-disable-next-line @typescript-eslint/no-explicit-any
          (globalThis as any).Buffer
            ? // eslint-disable-next-line @typescript-eslint/no-explicit-any
              (globalThis as any).Buffer.from(padded, 'base64').toString('utf8')
            : null;
    if (!json) return null;
    const payload = JSON.parse(json) as { exp?: number };
    return typeof payload.exp === 'number' ? payload.exp : null;
  } catch {
    return null;
  }
}

/**
 * Schedule a silent access-token refresh ~60s before JWT expiry.
 * No-ops if the token is already expired or has no exp claim.
 * Call after every successful login / refresh / hydrate.
 */
export function scheduleSilentRefresh(accessToken: string | null | undefined): void {
  if (silentRefreshTimer) {
    clearTimeout(silentRefreshTimer);
    silentRefreshTimer = null;
  }
  if (!accessToken) return;

  const exp = decodeJwtExp(accessToken);
  if (!exp) return;

  const nowSec = Math.floor(Date.now() / 1000);
  // Refresh 60s before expiry, but never sooner than 5s from now.
  const delayMs = Math.max((exp - nowSec - 60) * 1000, 5_000);
  // If already past the soft window, refresh almost immediately.
  const effectiveDelay = exp - nowSec <= 60 ? 1_000 : delayMs;

  silentRefreshTimer = setTimeout(() => {
    silentRefreshTimer = null;
    // Fire-and-forget; interceptor + forceLogout handle failures.
    void ensureFreshAccessToken().catch(() => {
      /* forceLogout already ran inside doRefresh path on hard failure */
    });
  }, effectiveDelay);
}

/** Cancel any pending silent refresh (e.g. on logout). */
export function cancelSilentRefresh(): void {
  if (silentRefreshTimer) {
    clearTimeout(silentRefreshTimer);
    silentRefreshTimer = null;
  }
}

async function doRefresh(): Promise<string> {
  const { refreshToken, setTokens, clear } = useAuthStore.getState();
  if (!refreshToken) {
    throw new Error('no_refresh_token');
  }
  // Try the refresh once; if it fails with a network error (not a 401),
  // wait briefly and retry once before giving up. This avoids kicking
  // the user to login over a transient blip (poor signal, DNS hiccup,
  // backend rolling restart, etc).
  let lastErr: unknown;
  for (let attempt = 0; attempt < 2; attempt++) {
    try {
      // Hit the refresh endpoint directly with the refresh token in the
      // Authorization header (per api-contract.md §1.2).
      const resp = await axios.post<{
        data: {
          access_token: string;
          refresh_token: string;
          token_type: string;
          expires_in: number;
        };
      }>(
        `${resolveBaseURL()}/auth/refresh`,
        {},
        { headers: { Authorization: `Bearer ${refreshToken}` } },
      );
      const at = resp.data.data.access_token;
      const rt = resp.data.data.refresh_token;
      setTokens(at, rt);
      // Persist so the next cold start hydrates the rotated pair, not the
      // revoked refresh token still sitting in SecureStore / sessionStorage.
      await storage.setTokens(at, rt);
      return at;
    } catch (e) {
      lastErr = e;
      // If the backend explicitly says the refresh token is bad
      // (401/403), retrying won't help — bail immediately.
      if (axios.isAxiosError(e) && e.response && (e.response.status === 401 || e.response.status === 403)) {
        break;
      }
      // Otherwise it's a network/5xx — wait a beat and try again.
      if (attempt === 0) {
        await new Promise((r) => setTimeout(r, 400));
      }
    }
  }
  // Genuinely failed after retry — treat as logged out.
  // Touch `clear` to satisfy the linter (we don't actually call it
  // here; the interceptor's catch does the forceLogout).
  void clear;
  throw lastErr instanceof Error ? lastErr : new Error('refresh_failed');
}

function forceLogout() {
  cancelSilentRefresh();
  const { clear } = useAuthStore.getState();
  clear();
  // Also wipe durable storage so a cold start cannot resurrect a
  // revoked session. Fire-and-forget; storage failures must not block.
  void storage.clear();
}

/**
 * Ensure we have a fresh access token. If one is already in flight,
 * wait for it; otherwise start a refresh. Used by the silent timer
 * and by the 401 interceptor.
 */
async function ensureFreshAccessToken(): Promise<string> {
  if (refreshInFlight) return refreshInFlight;
  refreshInFlight = doRefresh()
    .then((token) => {
      waiters.splice(0).forEach((w) => w.resolve(token));
      scheduleSilentRefresh(token);
      return token;
    })
    .catch((refreshErr) => {
      waiters.splice(0).forEach((w) => w.reject(refreshErr));
      forceLogout();
      throw refreshErr;
    })
    .finally(() => {
      refreshInFlight = null;
    });
  return refreshInFlight;
}

api.interceptors.response.use(
  (r) => r,
  async (err: AxiosError<ApiError>) => {
    const original = err.config as (AxiosRequestConfig & { _retry?: boolean }) | undefined;
    const status = err.response?.status;

    // Skip 401 handling for the refresh + login endpoints themselves.
    const url = original?.url ?? '';
    const isAuthEndpoint =
      url.includes('/auth/refresh') || url.includes('/auth/login');

    if (status !== 401 || !original || original._retry || isAuthEndpoint) {
      throw err;
    }
    original._retry = true;

    try {
      // Park this request on the waiter list, then kick off (or join) a refresh.
      const tokenPromise = new Promise<string>((resolve, reject) => {
        waiters.push({ resolve, reject });
      });
      // Start the shared refresh if not already running.
      void ensureFreshAccessToken();
      const newToken = await tokenPromise;
      // Retry the original request with the new token.
      const headers = new AxiosHeaders(original.headers as Record<string, string> | undefined);
      headers.set('Authorization', `Bearer ${newToken}`);
      original.headers = headers;
      return api.request(original);
    } catch (refreshErr) {
      throw refreshErr;
    }
  },
);

// ---- Response helpers ----
// Unwrap the standard `{ data: ... }` / `{ items, total, ... }`
// shapes so screens deal in entities, not envelopes.

export async function getSingle<T>(path: string, params?: Record<string, unknown>): Promise<T> {
  const resp = await api.get<SingleResponse<T>>(path, { params });
  return resp.data.data;
}

export async function getPage<T>(path: string, params?: Record<string, unknown>): Promise<Page<T>> {
  const resp = await api.get<Page<T>>(path, { params });
  return resp.data;
}

export async function postSingle<T, B = unknown>(path: string, body?: B): Promise<T> {
  const resp = await api.post<SingleResponse<T>>(path, body);
  return resp.data.data;
}

export async function patchSingle<T, B = unknown>(path: string, body?: B): Promise<T> {
  const resp = await api.patch<SingleResponse<T>>(path, body);
  return resp.data.data;
}

export async function postAction<T>(path: string): Promise<T> {
  const resp = await api.post<SingleResponse<T>>(path);
  return resp.data.data;
}

export async function postNoContent(path: string, body?: unknown): Promise<void> {
  await api.post(path, body);
}

export async function patchNoContent(path: string, body?: unknown): Promise<void> {
  await api.patch(path, body);
}

export async function deleteNoContent(path: string): Promise<void> {
  await api.delete(path);
}

export async function postJson<T>(path: string, body?: unknown): Promise<T> {
  const resp = await api.post<T>(path, body);
  return (resp.data as any).data ?? resp.data;
}

export async function patchJson<T>(path: string, body: unknown): Promise<T> {
  const resp = await api.patch<T>(path, body);
  return (resp.data as any).data ?? resp.data;
}

export async function deleteJson<T>(path: string, body: unknown): Promise<T> {
  const resp = await api.delete<T>(path, { data: body });
  return (resp.data as any).data ?? resp.data;
}

export function getErrorMessage(err: unknown, fallback = 'Something went wrong.'): string {
  if (axios.isAxiosError<ApiError>(err)) {
    const detail = err.response?.data?.detail;
    if (detail) return detail;
    if (err.message) return err.message;
  }
  if (err instanceof Error) return err.message;
  return fallback;
}

export function getErrorType(err: unknown): string | undefined {
  if (axios.isAxiosError<ApiError>(err)) {
    return err.response?.data?.type;
  }
  return undefined;
}
