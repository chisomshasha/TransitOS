/**
 * AuthProvider + useAuth().
 *
 * On mount, kicks off the hydration flow described in
 * sprint-a-tasks.md §3.7 + §5.3:
 *
 *   1. Read `access_token` from secure store.
 *   2. If present, call `GET /auth/me`. On 200 → populate store +
 *      mark `isAuthenticated=true`.
 *   3. On 401, attempt `POST /auth/refresh`. On 200 → retry `/me`.
 *   4. On any failure or no token → leave `user=null` and route to
 *      `/(auth)/login`.
 *
 * The `index.tsx` hydration gate calls `hydrate()` once on mount
 * and renders a Spinner until `isLoading` flips to false.
 */

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import axios from 'axios';
import { useAuthStore } from '@/stores/authStore';
import { storage } from '@/lib/storage';
import {
  getSingle,
  postNoContent,
  getErrorMessage,
  getErrorType,
  scheduleSilentRefresh,
  cancelSilentRefresh,
} from '@/lib/api';
import { queryClient } from '@/lib/queryClient';
import { resolveBaseURL } from '@/lib/api';
import { registerForPush, unregisterFromPush } from '@/lib/push';
import type { SingleResponse, User } from '@/lib/types';

interface AuthContextValue {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
  hydrate: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

interface LoginRaw {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [isLoading, setIsLoading] = useState(true);
  // Guard against double-hydration in StrictMode / fast-refresh.
  const didHydrate = useRef(false);

  const user = useAuthStore((s) => s.user);
  const setSession = useAuthStore((s) => s.setSession);
  const setTokens = useAuthStore((s) => s.setTokens);
  const clearStore = useAuthStore((s) => s.clear);

  const hydrate = useCallback(async () => {
    setIsLoading(true);
    try {
      const access = await storage.getAccessToken();
      if (!access) {
        clearStore();
        return;
      }
      // Seed the store with the token we have on hand so the
      // very first /auth/me call carries it (the interceptor reads
      // from the store on every request).
      useAuthStore.setState({ accessToken: access, refreshToken: await storage.getRefreshToken() });
      try {
        const me = await getSingle<User>('/auth/me');
        setSession(me, access, (await storage.getRefreshToken()) ?? '');
        scheduleSilentRefresh(access);
        // Register this device for push notifications. Fire-and-forget:
        // a push failure must never block the app from starting.
        void registerForPush();
      } catch (err) {
        if (axios.isAxiosError(err) && err.response?.status === 401) {
          // Try refresh once.
          const rt = await storage.getRefreshToken();
          if (rt) {
            try {
              const resp = await axios.post<SingleResponse<LoginRaw>>(
                `${resolveBaseURL()}/auth/refresh`,
                {},
                { headers: { Authorization: `Bearer ${rt}` } },
              );
              const tokens = resp.data.data;
              await storage.setTokens(tokens.access_token, tokens.refresh_token);
              setTokens(tokens.access_token, tokens.refresh_token);
              const me = await getSingle<User>('/auth/me');
              setSession(me, tokens.access_token, tokens.refresh_token);
              scheduleSilentRefresh(tokens.access_token);
              void registerForPush();
            } catch {
              cancelSilentRefresh();
              await storage.clear();
              clearStore();
            }
          } else {
            await storage.clear();
            clearStore();
          }
        } else {
          // Network or 5xx — keep the token in storage; the user can
          // still use the offline experience. We just don't mark them
          // as authenticated yet, so the UI shows a spinner instead of
          // a hard redirect to login. Next focus/foreground will retry
          // hydrate() and pick up the session.
          // NOTE: deliberately do NOT call clearStore() here — that
          // would wipe the token and force a re-login on any transient
          // network glitch.
        }
      }
    } finally {
      setIsLoading(false);
    }
  }, [clearStore, setSession, setTokens]);

  useEffect(() => {
    if (didHydrate.current) return;
    didHydrate.current = true;
    void hydrate();
  }, [hydrate]);

  const login = useCallback(
    async (email: string, password: string) => {
      const resp = await axios.post<SingleResponse<LoginRaw>>(
        `${resolveBaseURL()}/auth/login`,
        { email, password },
      );
      const { access_token, refresh_token } = resp.data.data;
      await storage.setTokens(access_token, refresh_token);
      // Set the access token BEFORE fetching /me so the axios
      // interceptor can attach it.
      useAuthStore.setState({ accessToken: access_token, refreshToken: refresh_token });
      const me = await getSingle<User>('/auth/me');
      setSession(me, access_token, refresh_token);
      scheduleSilentRefresh(access_token);
      // Register this device for push notifications (fire-and-forget).
      void registerForPush();
    },
    [setSession],
  );

  const logout = useCallback(async () => {
    try {
      const { refreshToken } = useAuthStore.getState();
      await postNoContent('/auth/logout', refreshToken ? { refresh_token: refreshToken } : {});
    } catch {
      // Network failure is NOT a blocker — the backend is idempotent
      // and the token will simply expire naturally.
    } finally {
      // Deactivate this device's push token before dropping the session.
      // Must run while the access token is still attached to the
      // axios instance, so it goes before clearStore().
      await unregisterFromPush();
      cancelSilentRefresh();
      await storage.clear();
      clearStore();
      queryClient.clear();
    }
  }, [clearStore]);

  const refresh = useCallback(async () => {
    await hydrate();
  }, [hydrate]);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      isLoading,
      isAuthenticated: !!user,
      login,
      logout,
      refresh,
      hydrate,
    }),
    [user, isLoading, login, logout, refresh, hydrate],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used inside <AuthProvider>');
  }
  return ctx;
}

export { getErrorMessage, getErrorType };
// Re-export the SingleResponse type so screens can type their hooks.
export type { SingleResponse };
