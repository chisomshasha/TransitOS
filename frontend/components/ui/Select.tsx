import React, { useState } from 'react';
import { Pressable, StyleSheet, Text } from 'react-native';
import { Check, ChevronDown } from 'lucide-react-native';
import { Modal } from './Modal';

export interface SelectOption<T extends string> {
  label: string;
  value: T;
}

export interface SelectProps<T extends string> {
  value: T | null;
  onChange: (v: T) => void;
  options: SelectOption<T>[];
  placeholder?: string;
  disabled?: boolean;
  error?: string;
  testID?: string;
  accessibilityLabel?: string;
}

export function Select<T extends string>({
  value,
  onChange,
  options,
  placeholder = 'Select…',
  disabled,
  error,
  testID,
  accessibilityLabel,
}: SelectProps<T>) {
  const [open, setOpen] = useState(false);
  const current = options.find((o) => o.value === value);

  return (
    <>
      <Pressable
        testID={testID}
        accessibilityRole="button"
        accessibilityLabel={accessibilityLabel ?? placeholder}
        onPress={() => !disabled && setOpen(true)}
        disabled={disabled}
        style={({ pressed }) => [
          styles.trigger,
          error ? styles.triggerError : styles.triggerNormal,
          disabled ? styles.triggerDisabled : null,
          pressed && !disabled ? { opacity: 0.8 } : null,
        ]}
      >
        <Text
          style={[styles.triggerText, { color: current && !disabled ? '#1E293B' : '#94A3B8' }]}
          numberOfLines={1}
        >
          {current ? current.label : placeholder}
        </Text>
        <ChevronDown size={18} color={disabled ? '#94A3B8' : '#64748B'} />
      </Pressable>
      {error ? <Text style={styles.error}>{error}</Text> : null}
      <Modal visible={open} onClose={() => setOpen(false)} title="Select">
        {options.map((opt) => {
          const selected = opt.value === value;
          return (
            <Pressable
              key={opt.value}
              onPress={() => {
                onChange(opt.value);
                setOpen(false);
              }}
              style={({ pressed }) => [
                styles.option,
                selected ? styles.optionSelected : null,
                pressed && !selected ? { backgroundColor: '#F1F5F9' } : null,
              ]}
            >
              <Text style={[styles.optionText, selected ? styles.optionTextSelected : null]}>
                {opt.label}
              </Text>
              {selected ? <Check size={18} color="#0E7490" /> : null}
            </Pressable>
          );
        })}
      </Modal>
    </>
  );
}

const styles = StyleSheet.create({
  trigger: {
    height: 44,
    paddingHorizontal: 12,
    borderRadius: 12,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    borderWidth: 1,
    backgroundColor: '#FFFFFF',
  },
  triggerNormal: { borderColor: '#CBD5E1' },
  triggerError: { borderColor: '#EF4444', backgroundColor: '#FEF2F2' },
  triggerDisabled: { backgroundColor: '#F1F5F9' },
  triggerText: { fontSize: 16, flex: 1 },
  error: { fontSize: 12, color: '#B91C1C', marginTop: 4 },
  option: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 12,
    paddingHorizontal: 8,
    borderRadius: 12,
  },
  optionSelected: { backgroundColor: '#ECFEFF' },
  optionText: { fontSize: 16, color: '#1E293B' },
  optionTextSelected: { color: '#0E7490', fontWeight: '600' },
});
