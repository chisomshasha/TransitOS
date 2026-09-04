import React from 'react';
import { View } from 'react-native';
import { Redirect, Stack, usePathname } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useAuth } from '@/lib/auth-context';
import {
  BottomTabs,
  BOTTOM_TABS_CONTENT_HEIGHT,
  BOTTOM_TABS_BASE_BOTTOM_PADDING,
} from '@/components/ui/BottomTabs';
import { ErrorBoundary } from '@/components/ui/ErrorBoundary';
import { SyncStatusIndicator } from '@/components/ui/SyncStatusIndicator';
import { canAccessScreen, defaultHomeForRole } from '@/lib/rbac';
import type { Role } from '@/lib/types';

export default function AppLayout() {
  const { isAuthenticated, isLoading, user } = useAuth();
  const pathname = usePathname();
  const insets = useSafeAreaInsets();
  const contentPaddingBottom =
    BOTTOM_TABS_CONTENT_HEIGHT +
    BOTTOM_TABS_BASE_BOTTOM_PADDING +
    Math.max(insets.bottom, 0);

  if (isLoading) return null;
  if (!isAuthenticated) return <Redirect href="/(auth)/login" />;

  const role = (user?.role ?? null) as Role | null;
  if (role && pathname && !canAccessScreen(role, pathname)) {
    return <Redirect href={defaultHomeForRole(role) as never} />;
  }

  return (
    <ErrorBoundary scope="app">
      <View style={{ flex: 1, backgroundColor: '#F8F7F4' }}>
        <Stack
          screenOptions={{
            headerStyle: { backgroundColor: '#0B3D91' },
            headerTitleStyle: {
              fontWeight: '700',
              color: '#FFFFFF',
              fontSize: 18,
            },
            headerTintColor: '#FFCC00',
            headerShadowVisible: false,
            contentStyle: {
              backgroundColor: '#F8F7F4',
              paddingBottom: contentPaddingBottom,
            },
            headerRight: () => <SyncStatusIndicator />,
          }}
        >
          <Stack.Screen name="index" options={{ title: 'Dashboard', headerShown: false }} />
          <Stack.Screen name="branches/index" options={{ title: 'Branches' }} />
          <Stack.Screen name="branches/[id]" options={{ title: 'Branch' }} />
          <Stack.Screen name="users/index" options={{ title: 'Users' }} />
          <Stack.Screen name="users/[id]" options={{ title: 'User' }} />
          <Stack.Screen name="vehicles/index" options={{ title: 'Vehicles' }} />
          <Stack.Screen name="vehicles/[id]" options={{ title: 'Vehicle' }} />
          <Stack.Screen name="drivers/index" options={{ title: 'Drivers' }} />
          <Stack.Screen name="drivers/[id]" options={{ title: 'Driver' }} />
          <Stack.Screen name="conductors/index" options={{ title: 'Conductors' }} />
          <Stack.Screen name="conductors/[id]" options={{ title: 'Conductor' }} />
          <Stack.Screen name="routes/index" options={{ title: 'Routes' }} />
          <Stack.Screen name="routes/[id]" options={{ title: 'Route' }} />
          <Stack.Screen name="trips/index" options={{ title: 'Trips' }} />
          <Stack.Screen name="trips/[id]" options={{ title: 'Trip' }} />
          <Stack.Screen name="fuel" options={{ title: 'Fuel' }} />
          <Stack.Screen name="maintenance" options={{ title: 'Maintenance' }} />
          <Stack.Screen name="expenses" options={{ title: 'Expenses' }} />
          <Stack.Screen name="cash-ups" options={{ title: 'Cash-ups' }} />
          <Stack.Screen name="reports" options={{ title: 'Reports' }} />
          <Stack.Screen name="profile" options={{ title: 'My Profile' }} />

          {/* Phase 0 */}
          <Stack.Screen name="more" options={{ title: 'More' }} />
          <Stack.Screen name="sync" options={{ title: 'Sync' }} />

          {/* Phase 1 */}
          <Stack.Screen name="notifications" options={{ title: 'Notifications' }} />

          {/* Phase 3 */}
          <Stack.Screen name="audit-log" options={{ title: 'Audit log' }} />
          <Stack.Screen name="role-permissions" options={{ title: 'Role permissions' }} />

          {/* Phase 4 */}
          <Stack.Screen name="incidents" options={{ title: 'Incidents' }} />
          <Stack.Screen name="report-incident" options={{ title: 'Report incident' }} />
          <Stack.Screen name="pre-trip-checklist" options={{ title: 'Pre-trip checklist' }} />

          {/* Phase 5 */}
          <Stack.Screen name="map" options={{ title: 'Live fleet map' }} />
          <Stack.Screen name="transfers/index" options={{ title: 'Vehicle transfers' }} />
          <Stack.Screen name="transfers/[id]" options={{ title: 'Transfer' }} />

          {/* Phase 8 */}
          <Stack.Screen name="scan" options={{ title: 'Scan', headerShown: false }} />
        </Stack>
        <BottomTabs />
      </View>
    </ErrorBoundary>
  );
}
