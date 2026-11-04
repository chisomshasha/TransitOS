/**
 * Push notification registration.
 *
 * The backend already exposes the full device-token lifecycle:
 *   POST /push/register     — upsert the token for the signed-in user
 *   POST /push/unregister   — deactivate it (soft delete)
 *   GET  /push              — list the caller's active tokens
 *
 * …but the app never called any of them, so `expo-notifications` was
 * installed, unused, and NO device could ever receive a push. The
 * backend had a full, tested push-token store with nothing feeding it.
 *
 * This module closes that loop:
 *   registerForPush()   — called after login / hydration
 *   unregisterFromPush()— called on logout
 *
 * Everything is best-effort: a push failure (no FCM credentials, an
 * emulator without Play Services, a denied permission) must never
 * break login. All errors are swallowed after a console warning.
 */

import { Platform } from 'react-native';
import Constants from 'expo-constants';
import { postNoContent } from '@/lib/api';

const API_VERSION = '1.2.0';

function expoProjectId(): string | undefined {
  const extra = (Constants.expoConfig?.extra ?? {}) as {
    eas?: { projectId?: string };
  };
  return extra.eas?.projectId;
}

/** Stable per-install device identifier (no PII, no hardware IDs). */
function deviceId(): string {
  const existing = Constants.sessionId;
  return existing ?? 'transitos-device';
}

function currentPlatform(): 'ios' | 'android' | 'web' {
  if (Platform.OS === 'ios') return 'ios';
  if (Platform.OS === 'android') return 'android';
  return 'web';
}

/**
 * Ask the OS for an Expo push token and register it with the backend.
 * Resolves to `true` when the token was registered.
 */
export async function registerForPush(): Promise<boolean> {
  // Expo push tokens are not available on web.
  if (currentPlatform() === 'web') return false;

  try {
    // Dynamic import keeps `expo-notifications` out of the web bundle
    // and avoids a hard module dependency at startup.
    const Notifications = await import('expo-notifications');

    // Show banners even when the app is in the foreground — a driver
    // needs to see a dispatch alert while the app is open.
    Notifications.setNotificationHandler({
      handleNotification: async () => ({
        shouldShowBanner: true,
        shouldShowList: true,
        shouldPlaySound: true,
        shouldSetBadge: true,
      }),
    });

    const projectId = expoProjectId();

    // Ask for permission first (required on iOS, and on Android 13+).
    const existing = await Notifications.getPermissionsAsync();
    let granted = existing.granted;
    if (!granted && existing.canAskAgain !== false) {
      const requested = await Notifications.requestPermissionsAsync();
      granted = requested.granted;
    }
    if (!granted) {
      console.log('[TransitOS] push permission not granted — skipping registration');
      return false;
    }

    const tokenResponse = await Notifications.getExpoPushTokenAsync(
      projectId ? { projectId } : undefined,
    );
    const token = tokenResponse?.data;
    if (!token) return false;

    await postNoContent('/push/register', {
      token,
      platform: currentPlatform(),
      device_id: deviceId(),
      app_version: API_VERSION,
    });

    console.log('[TransitOS] push token registered');
    return true;
  } catch (err) {
    // Never let a push problem break the sign-in flow.
    console.log('[TransitOS] push registration skipped:', (err as Error)?.message ?? err);
    return false;
  }
}

/**
 * Deactivate the device's push token on logout.
 *
 * The backend needs the *same* token to find the row, so we re-read it
 * from the OS. If the user denies or the OS no longer has it, the
 * backend's 404 is ignored — the token will expire on its own.
 */
export async function unregisterFromPush(): Promise<void> {
  if (currentPlatform() === 'web') return;

  try {
    const Notifications = await import('expo-notifications');
    const projectId = expoProjectId();
    const tokenResponse = await Notifications.getExpoPushTokenAsync(
      projectId ? { projectId } : undefined,
    );
    const token = tokenResponse?.data;
    if (!token) return;

    await postNoContent('/push/unregister', {
      token,
      platform: currentPlatform(),
      device_id: deviceId(),
      app_version: API_VERSION,
    });
  } catch (err) {
    console.log('[TransitOS] push unregister skipped:', (err as Error)?.message ?? err);
  }
}
