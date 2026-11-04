import React from 'react';
import { Redirect } from 'expo-router';
import { View } from 'react-native';
import { useAuth } from '@/lib/auth-context';
import { Spinner } from '@/components/ui/Spinner';

export default function Index() {
  const { isLoading, isAuthenticated } = useAuth();
  if (isLoading) {
    return (
      <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: '#FFFFFF' }}>
        <Spinner size="large" label="Loading…" />
      </View>
    );
  }
  return isAuthenticated ? (
    <Redirect href="/(app)" />
  ) : (
    <Redirect href="/(auth)/login" />
  );
}
