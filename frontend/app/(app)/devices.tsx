import React from 'react';
import {
  Alert,
  FlatList,
  RefreshControl,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { Stack } from 'expo-router';
import { BellRing, Smartphone, Trash2 } from 'lucide-react-native';
import { usePushTokens, useUnregisterPushToken } from '@/lib/queries-ops';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Spinner } from '@/components/ui/Spinner';
import { EmptyState } from '@/components/ui/EmptyState';
import { Button } from '@/components/ui/Button';
import { useToast } from '@/components/ui/Toast';

const PLATFORM_LABEL: Record<string, string> = {
  ios: 'iOS',
  android: 'Android',
  web: 'Web',
};

export default function DevicesScreen() {
  const toast = useToast();
  const devicesQ = usePushTokens();
  const unregister = useUnregisterPushToken();

  const devices = devicesQ.data ?? [];

  const onRemove = (token: string, platform: 'ios' | 'android' | 'web') => {
    Alert.alert(
      'Remove this device?',
      'This device will stop receiving push notifications. Sign in again on it to re-register.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Remove',
          style: 'destructive',
          onPress: async () => {
            try {
              await unregister.mutateAsync({ token, platform });
              toast.success('Device removed');
            } catch (e: any) {
              toast.error(
                e?.response?.data?.detail ?? 'Could not remove the device'
              );
            }
          },
        },
      ],
    );
  };

  return (
    <>
      <Stack.Screen options={{ title: 'My devices' }} />
      <View style={s.root}>
        {devicesQ.isLoading ? (
          <View style={s.loading}><Spinner label="Loading devices…" /></View>
        ) : devices.length === 0 ? (
          <EmptyState
            icon={<BellRing size={28} color="#94A3B8" />}
            title="No registered devices"
            description="Devices appear here once this app registers for push notifications. Sign in again to re-register a device."
          />
        ) : (
          <FlatList
            data={devices}
            keyExtractor={(d) => d.id}
            contentContainerStyle={{ padding: 16 }}
            ItemSeparatorComponent={() => <View style={{ height: 12 }} />}
            refreshControl={
              <RefreshControl
                refreshing={devicesQ.isRefetching}
                onRefresh={() => devicesQ.refetch()}
              />
            }
            renderItem={({ item }) => (
              <Card padding="sm">
                <View style={s.row}>
                  <View style={s.iconBox}>
                    <Smartphone size={18} color="#0B3D91" />
                  </View>
                  <View style={s.body}>
                    <Text style={s.name}>
                      {PLATFORM_LABEL[item.platform] ?? item.platform}
                    </Text>
                    <Text style={s.sub} numberOfLines={1}>
                      {item.device_id ?? 'Unknown device'}
                    </Text>
                    {item.app_version ? (
                      <Text style={s.sub}>App v{item.app_version}</Text>
                    ) : null}
                  </View>
                  <View style={s.right}>
                    <Badge
                      label={item.is_active ? 'Active' : 'Inactive'}
                      tone={item.is_active ? 'success' : 'neutral'}
                      size="sm"
                    />
                    {item.is_active ? (
                      <Button
                        label="Remove"
                        variant="ghost"
                        size="sm"
                        icon={<Trash2 size={14} color="#B91C1C" />}
                        onPress={() =>
                          onRemove(item.token, item.platform as 'ios' | 'android' | 'web')
                        }
                      />
                    ) : null}
                  </View>
                </View>
              </Card>
            )}
          />
        )}
      </View>
    </>
  );
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#F4F4F2' },
  loading: { paddingVertical: 40, alignItems: 'center' },
  row: { flexDirection: 'row', alignItems: 'center' },
  iconBox: { width: 40, height: 40, borderRadius: 8, backgroundColor: '#DBEAFE', alignItems: 'center', justifyContent: 'center', marginRight: 12 },
  body: { flex: 1 },
  right: { alignItems: 'flex-end', gap: 6 },
  name: { fontSize: 14, fontWeight: '600', color: '#171717' },
  sub: { fontSize: 12, color: '#737373', marginTop: 2 },
});
