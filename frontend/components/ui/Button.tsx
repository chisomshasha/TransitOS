import React from 'react';
import { Pressable, Text, View, ActivityIndicator } from 'react-native';

export type ButtonVariant = 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger';
export type ButtonSize = 'sm' | 'md' | 'lg';

export interface ButtonProps {
  label: string;
  onPress: () => void;
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  disabled?: boolean;
  icon?: React.ReactNode;
  iconPosition?: 'left' | 'right';
  fullWidth?: boolean;
  testID?: string;
  accessibilityLabel?: string;
}

// Inline styles — variant colors live in JS objects, invisible to the
// NativeWind static scanner, so they must be inline styles rather than
// className strings or they get purged from the CSS bundle at build time.
const VARIANT_BG: Record<ButtonVariant, string> = {
  primary: '#FFCC00', secondary: '#FFCC00', outline: '#FFFFFF', ghost: 'transparent', danger: '#EF4444',
};
const VARIANT_BG_PRESSED: Record<ButtonVariant, string> = {
  primary: '#E5B800', secondary: '#D97706', outline: '#F1F5F9', ghost: '#ECFEFF', danger: '#B91C1C',
};
const VARIANT_TEXT_COLOR: Record<ButtonVariant, string> = {
  primary: '#0B3D91', secondary: '#0B3D91', outline: '#0B3D91', ghost: '#0B3D91', danger: '#FFFFFF',
};
const VARIANT_BORDER: Record<ButtonVariant, string | undefined> = {
  primary: undefined, secondary: undefined, outline: '#CBD5E1', ghost: undefined, danger: undefined,
};
const LOADER_COLOR: Record<ButtonVariant, string> = {
  primary: '#0B3D91', secondary: '#0B3D91', outline: '#0B3D91', ghost: '#0B3D91', danger: '#FFFFFF',
};
const SIZE_HEIGHT: Record<ButtonSize, number> = { sm: 36, md: 48, lg: 56 };
const SIZE_PX: Record<ButtonSize, number> = { sm: 12, md: 16, lg: 24 };
const SIZE_FONT: Record<ButtonSize, number> = { sm: 14, md: 16, lg: 16 };

export function Button({
  label, onPress, variant = 'primary', size = 'md', loading = false, disabled = false,
  icon, iconPosition = 'left', fullWidth = false, testID, accessibilityLabel,
}: ButtonProps) {
  const isDisabled = disabled || loading;
  return (
    <Pressable
      testID={testID}
      accessibilityRole="button"
      accessibilityLabel={accessibilityLabel ?? label}
      accessibilityState={{ disabled: isDisabled, busy: loading }}
      onPress={onPress}
      disabled={isDisabled}
      style={({ pressed }) => ({
        height: SIZE_HEIGHT[size],
        paddingHorizontal: SIZE_PX[size],
        backgroundColor: pressed && !isDisabled ? VARIANT_BG_PRESSED[variant] : VARIANT_BG[variant],
        borderRadius: 10,
        borderWidth: VARIANT_BORDER[variant] ? 1 : 0,
        borderColor: VARIANT_BORDER[variant],
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'center',
        opacity: isDisabled ? 0.4 : 1,
        width: fullWidth ? '100%' : undefined,
      })}
    >
      {loading ? (
        <ActivityIndicator size="small" color={LOADER_COLOR[variant]} />
      ) : (
        <View style={{ flexDirection: 'row', alignItems: 'center' }}>
          {icon && iconPosition === 'left' ? <View style={{ marginRight: 8 }}>{icon}</View> : null}
          <Text style={{ color: VARIANT_TEXT_COLOR[variant], fontSize: SIZE_FONT[size], fontWeight: '600' }}>
            {label}
          </Text>
          {icon && iconPosition === 'right' ? <View style={{ marginLeft: 8 }}>{icon}</View> : null}
        </View>
      )}
    </Pressable>
  );
}
