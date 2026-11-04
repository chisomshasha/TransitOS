import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import * as Updates from 'expo-updates';
import { brand } from '@/lib/theme';

/**
 * Says which update channel this build is listening to.
 *
 * The channels are the whole point of EAS Update: a *preview* build
 * listens on the `preview` channel and a *production* build listens on
 * `production`, so a fix published to one never reaches the other. That
 * protection only works if everybody can tell which one a phone is on.
 *
 * A production build shows nothing — the strip appears only on a build
 * that is explicitly not production, so nobody in the field ever sees
 * it and a tester cannot accidentally show a preview build to the
 * client.
 */
export function UpdateChannelBanner() {
  const channel = Updates.channel ?? null;
  const enabled = Updates.isEnabled ?? false;

  if (!enabled || !channel || channel === 'production') return null;

  return (
    <View style={s.banner} accessibilityRole="alert">
      <Text style={s.title}>
        {channel === 'development' ? 'Development build' : 'Preview build'}
      </Text>
      <Text style={s.body}>
        This phone is on the <Text style={s.strong}>{channel}</Text> update channel, not
        production. It receives test updates, and it must not be used for live operations.
      </Text>
    </View>
  );
}

const s = StyleSheet.create({
  banner: {
    backgroundColor: brand.yellowSoft,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: brand.yellow,
    paddingHorizontal: 14,
    paddingVertical: 10,
    marginBottom: 14,
  },
  title: {
    fontSize: 12,
    fontWeight: '800',
    color: brand.navy,
    textTransform: 'uppercase',
    letterSpacing: 0.6,
    marginBottom: 2,
  },
  body: { fontSize: 12, color: brand.navy, lineHeight: 17 },
  strong: { fontWeight: '800' },
});
