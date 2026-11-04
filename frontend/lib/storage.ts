/**
 * Token storage.
 *
 * - Native (iOS / Android): expo-secure-store (encrypted keychain / Keystore).
 * - Web: sessionStorage only (cleared when the tab/window closes).
 *   We deliberately avoid localStorage so a shared or abandoned browser
 *   session does not leave long-lived refresh tokens on disk.
 */

import { Platform } from 'react-native';
import * as SecureStore from 'expo-secure-store';

const ACCESS_KEY = 'transitos.accessToken';
const REFRESH_KEY = 'transitos.refreshToken';

const isWeb = Platform.OS === 'web';

function webGet(key: string): string | null {
  try {
    if (typeof sessionStorage === 'undefined') return null;
    return sessionStorage.getItem(key);
  } catch {
    return null;
  }
}

function webSet(key: string, value: string): void {
  try {
    if (typeof sessionStorage === 'undefined') return;
    sessionStorage.setItem(key, value);
  } catch {
    // Quota / private mode — swallow; caller still has in-memory store.
  }
}

function webDelete(key: string): void {
  try {
    if (typeof sessionStorage === 'undefined') return;
    sessionStorage.removeItem(key);
  } catch {
    // ignore
  }
}

export const storage = {
  async getAccessToken(): Promise<string | null> {
    if (isWeb) {
      return webGet(ACCESS_KEY);
    }
    try {
      return await SecureStore.getItemAsync(ACCESS_KEY);
    } catch {
      return null;
    }
  },

  async getRefreshToken(): Promise<string | null> {
    if (isWeb) {
      return webGet(REFRESH_KEY);
    }
    try {
      return await SecureStore.getItemAsync(REFRESH_KEY);
    } catch {
      return null;
    }
  },

  async setTokens(access: string, refresh: string): Promise<void> {
    if (isWeb) {
      webSet(ACCESS_KEY, access);
      webSet(REFRESH_KEY, refresh);
      return;
    }
    await SecureStore.setItemAsync(ACCESS_KEY, access);
    await SecureStore.setItemAsync(REFRESH_KEY, refresh);
  },

  async clear(): Promise<void> {
    if (isWeb) {
      webDelete(ACCESS_KEY);
      webDelete(REFRESH_KEY);
      return;
    }
    await Promise.all([
      SecureStore.deleteItemAsync(ACCESS_KEY),
      SecureStore.deleteItemAsync(REFRESH_KEY),
    ]);
  },
};
