/**
 * The screen the password-reset email links to.
 *
 * The emailed link is `<FRONTEND_URL>/reset-password?token=…`. Expo
 * Router strips the `(auth)` group from the URL, so the path is
 * `/reset-password` — this file.
 *
 * There was no such route: the email pointed at `/(auth)/reset-password`
 * and nothing served it, so every reset link 404'd. The app's
 * "forgot password" screen could still complete the flow by pasting the
 * code by hand, but the link in the email was dead.
 *
 * This route reads `?token=` and opens the same "set a new password"
 * form with the code already filled in.
 */
import React from 'react';
import { useLocalSearchParams } from 'expo-router';

import ForgotPasswordScreen from './forgot-password';

export default function ResetPasswordScreen() {
  const params = useLocalSearchParams<{ token?: string | string[] }>();
  const raw = params.token;
  const token = Array.isArray(raw) ? (raw[0] ?? '') : (raw ?? '');

  return <ForgotPasswordScreen initialMode="reset" initialToken={token} />;
}
