/**
 * Root layout — wraps the whole app in providers.
 * Uses the shared queryClient from lib/queryClient.ts so the
 * sync helpers can update the cache.
 */
import React, { useEffect } from 'react';
import { Slot } from 'expo-router';
import { QueryClientProvider } from '@tanstack/react-query';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import Toast from 'react-native-toast-message';
import { AuthProvider } from '@/lib/auth-context';
import { queryClient } from '@/lib/queryClient';

export default function RootLayout() {
  return (
    <SafeAreaProvider>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <Slot />
          <Toast />
        </AuthProvider>
      </QueryClientProvider>
    </SafeAreaProvider>
  );
}
