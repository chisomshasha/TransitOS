import React from 'react';
import { Modal as RNModal, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { X } from 'lucide-react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

export interface ModalProps {
  visible: boolean;
  onClose: () => void;
  title?: string;
  children: React.ReactNode;
  variant?: 'sheet' | 'dialog';
  testID?: string;
}

export function Modal({ visible, onClose, title, children, variant = 'dialog', testID }: ModalProps) {
  const insets = useSafeAreaInsets();
  const isSheet = variant === 'sheet';
  const close = () => onClose?.();

  return (
    <RNModal visible={visible} transparent animationType={isSheet ? 'slide' : 'fade'} onRequestClose={close}>
      <View style={s.root}>
        <Pressable style={StyleSheet.absoluteFill} onPress={close} accessibilityLabel="Close modal" />
        <View style={isSheet ? [s.wrap, s.wrapSheet] : [s.wrap, s.wrapDialog]}>
          <View
            style={
              isSheet
                ? [s.card, s.cardSheet, { paddingBottom: Math.max(insets.bottom, 16) }]
                : [s.card, s.cardDialog]
            }
          >
            {isSheet ? <View style={s.handle} /> : null}
            {title ? (
              <View style={s.header}>
                <Text style={s.title} numberOfLines={1}>{title}</Text>
                <Pressable onPress={close} accessibilityLabel="Close" hitSlop={12}>
                  <X size={22} color="#475569" />
                </Pressable>
              </View>
            ) : null}
            <ScrollView
              style={s.body}
              keyboardShouldPersistTaps="handled"
              showsVerticalScrollIndicator
              bounces={false}
            >
              {children}
            </ScrollView>
          </View>
        </View>
      </View>
    </RNModal>
  );
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)' },
  wrap: { flex: 1 },
  wrapDialog: { justifyContent: 'center', alignItems: 'center', paddingHorizontal: 16, paddingVertical: 24 },
  wrapSheet: { justifyContent: 'flex-end' },
  card: { backgroundColor: '#FFFFFF', width: '100%', maxHeight: '85%' },
  cardDialog: { borderRadius: 12, padding: 24, maxWidth: 448 },
  cardSheet: { borderTopLeftRadius: 16, borderTopRightRadius: 16, paddingTop: 8, paddingHorizontal: 16 },
  handle: { width: 40, height: 4, borderRadius: 2, backgroundColor: '#CBD5E1', alignSelf: 'center', marginBottom: 10 },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 },
  title: { flex: 1, fontSize: 18, fontWeight: '600', color: '#0F172A', marginRight: 8 },
  body: { flexShrink: 1 },
});
