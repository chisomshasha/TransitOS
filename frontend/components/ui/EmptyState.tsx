import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { Inbox } from 'lucide-react-native';
import { Button } from './Button';

export interface EmptyStateProps {
  title: string;
  description?: string;
  icon?: React.ReactNode;
  actionLabel?: string;
  onAction?: () => void;
  className?: string;
}

export function EmptyState({ title, description, icon, actionLabel, onAction }: EmptyStateProps) {
  return (
    <View style={styles.wrap}>
      <View style={styles.iconCircle}>{icon ?? <Inbox size={28} color="#94A3B8" />}</View>
      <Text style={styles.title}>{title}</Text>
      {description ? <Text style={styles.description}>{description}</Text> : null}
      {actionLabel && onAction ? (
        <View style={styles.action}>
          <Button label={actionLabel} onPress={onAction} variant="primary" />
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { alignItems: 'center', justifyContent: 'center', paddingVertical: 48, paddingHorizontal: 24 },
  iconCircle: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: '#F1F5F9',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 16,
  },
  title: { fontSize: 16, fontWeight: '600', color: '#1E293B', textAlign: 'center' },
  description: { fontSize: 14, color: '#64748B', textAlign: 'center', marginTop: 4 },
  action: { marginTop: 16 },
});
