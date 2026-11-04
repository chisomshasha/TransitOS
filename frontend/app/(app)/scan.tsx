/**
 * Scanner screen — full-screen camera view that resolves scanned
 * QR tokens to entity detail screens via the /qr/lookup endpoint.
 *
 * Supports vehicle, driver, conductor, and branch QR codes.
 */
import React, { useState } from 'react';
import { Stack, useRouter } from 'expo-router';
import { View, Text, StyleSheet, Pressable } from 'react-native';
import { AlertTriangle, Bus, Building2, UserCog, Users } from 'lucide-react-native';
import { BarcodeScanner } from '@/components/ui/BarcodeScanner';
import { useQrLookup } from '@/lib/queries-p8';
import { Spinner } from '@/components/ui/Spinner';
import { brand } from '@/lib/theme';

const ENTITY_ICONS: Record<string, React.ReactNode> = {
  vehicle: <Bus size={20} color={brand.navy} />,
  driver: <UserCog size={20} color={brand.navy} />,
  conductor: <Users size={20} color={brand.navy} />,
  branch: <Building2 size={20} color={brand.navy} />,
};

const ENTITY_ROUTES: Record<string, string> = {
  vehicle: '/vehicles/',
  driver: '/drivers/',
  conductor: '/conductors/',
  branch: '/branches/',
};

export default function ScanScreen() {
  const router = useRouter();
  const lookup = useQrLookup();
  const [error, setError] = useState<string | null>(null);
  const [resolving, setResolving] = useState(false);

  const handleScan = async (data: string) => {
    setError(null);
    setResolving(true);

    // If the scanned data is already a transitos:// deeplink, parse it directly
    if (data.startsWith('transitos://')) {
      const match = data.match(/transitos:\/\/(\w+)\/(.+)/);
      if (match) {
        const [, entityType, entityId] = match;
        const route = ENTITY_ROUTES[entityType];
        if (route) {
          setTimeout(() => router.push(`${route}${entityId}` as never), 300);
          return;
        }
      }
    }

    // Otherwise, treat it as a signed token and look it up
    try {
      const result = await lookup.mutateAsync(data);
      const route = ENTITY_ROUTES[result.entity_type];
      if (!route) {
        setError(`Unknown entity type: ${result.entity_type}`);
        setResolving(false);
        return;
      }
      // Small delay so the user sees the success state before navigation
      setTimeout(() => router.push(`${route}${result.entity_id}` as never), 300);
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? 'Could not read this QR code');
      setResolving(false);
    }
  };

  return (
    <>
      <Stack.Screen options={{ title: 'Scan', headerShown: false }} />
      <View style={{ flex: 1 }}>
        <BarcodeScanner
          onScan={handleScan}
          onClose={() => router.back()}
          hint="Point at a vehicle, driver, or branch QR code"
        />

        {/* Resolving overlay */}
        {resolving ? (
          <View style={s.overlay}>
            <View style={s.resolvingCard}>
              <Spinner label="Looking up…" />
            </View>
          </View>
        ) : null}

        {/* Error overlay */}
        {error ? (
          <View style={s.errorOverlay}>
            <View style={s.errorCard}>
              <AlertTriangle size={20} color="#B91C1C" />
              <Text style={s.errorText}>{error}</Text>
              <Pressable
                style={s.errorDismiss}
                onPress={() => setError(null)}
              >
                <Text style={s.errorDismissText}>Dismiss</Text>
              </Pressable>
            </View>
          </View>
        ) : null}
      </View>
    </>
  );
}

const s = StyleSheet.create({
  overlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0,0,0,0.6)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  resolvingCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 16,
    padding: 24,
    alignItems: 'center',
  },
  errorOverlay: {
    position: 'absolute',
    bottom: 100,
    left: 16,
    right: 16,
  },
  errorCard: {
    backgroundColor: '#FEF2F2',
    borderRadius: 14,
    padding: 16,
    borderWidth: 1,
    borderColor: '#FECACA',
    flexDirection: 'row',
    alignItems: 'center',
  },
  errorText: {
    flex: 1,
    fontSize: 13,
    color: '#B91C1C',
    marginLeft: 10,
    fontWeight: '600',
  },
  errorDismiss: {
    backgroundColor: '#B91C1C',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 8,
    marginLeft: 10,
  },
  errorDismissText: { color: '#FFFFFF', fontWeight: '700', fontSize: 12 },
});
