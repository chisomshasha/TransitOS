import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { Plus } from 'lucide-react-native';
import { Button } from './Button';

export interface PageHeaderProps {
  title: string;
  subtitle?: string;
  primaryActionLabel?: string;
  onPrimaryAction?: () => void;
  rightSlot?: React.ReactNode;
  className?: string;
}

export function PageHeader({
  title,
  subtitle,
  primaryActionLabel,
  onPrimaryAction,
  rightSlot,
}: PageHeaderProps) {
  return (
    <View style={styles.wrap}>
      <View style={styles.row}>
        <View style={styles.left}>
          <Text style={styles.title}>{title}</Text>
          {subtitle ? <Text style={styles.subtitle}>{subtitle}</Text> : null}
        </View>
        <View style={styles.right}>
          {rightSlot}
          {primaryActionLabel && onPrimaryAction ? (
            <View style={styles.buttonWrap}>
              <Button
                label={primaryActionLabel}
                onPress={onPrimaryAction}
                size="sm"
                icon={<Plus size={16} color="#FFFFFF" />}
              />
            </View>
          ) : null}
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { paddingBottom: 12 },
  row: { flexDirection: 'row', alignItems: 'flex-end', justifyContent: 'space-between' },
  left: { flex: 1, paddingRight: 12 },
  title: { fontSize: 24, fontWeight: '700', color: '#0F172A' },
  subtitle: { fontSize: 14, color: '#64748B', marginTop: 2 },
  right: { flexDirection: 'row', alignItems: 'center' },
  buttonWrap: { marginLeft: 8 },
});
