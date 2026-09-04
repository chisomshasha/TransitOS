/**
 * Minimal Zustand auth store — session tokens + user object.
 * **No fetch logic lives here.** Server state lives in TanStack
 * Query, not Zustand. This is the architectural rule that
 * separates us from the original TransHub's sprawl.
 */

import { create } from 'zustand';
import type { User } from '@/lib/types';

interface AuthStore {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;

  setSession: (u: User, at: string, rt: string) => void;
  updateUser: (u: User) => void;
  setTokens: (at: string, rt: string) => void;
  clear: () => void;
}

export const useAuthStore = create<AuthStore>((set) => ({
  user: null,
  accessToken: null,
  refreshToken: null,

  setSession: (u, at, rt) => set({ user: u, accessToken: at, refreshToken: rt }),
  updateUser: (u) => set({ user: u }),
  setTokens: (at, rt) => set({ accessToken: at, refreshToken: rt }),
  clear: () => set({ user: null, accessToken: null, refreshToken: null }),
}));
