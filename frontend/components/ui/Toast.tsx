import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from 'react';
import { Animated, Pressable, StyleSheet, Text, View } from 'react-native';
import { CheckCircle2, AlertCircle, Info, XCircle, X } from 'lucide-react-native';

type ToastTone = 'success' | 'error' | 'info' | 'warning';

interface ToastItem {
  id: string;
  message: string;
  tone: ToastTone;
}

interface ToastContextValue {
  show: (message: string, tone?: ToastTone) => void;
  success: (m: string) => void;
  error: (m: string) => void;
  info: (m: string) => void;
  warning: (m: string) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used inside <ToastProvider>');
  return ctx;
}

const ICONS: Record<ToastTone, React.ReactNode> = {
  success: <CheckCircle2 size={20} color="#047857" />,
  error: <XCircle size={20} color="#B91C1C" />,
  info: <Info size={20} color="#1D4ED8" />,
  warning: <AlertCircle size={20} color="#B45309" />,
};

const TONE: Record<ToastTone, { bg: string; border: string; text: string }> = {
  success: { bg: '#ECFDF5', border: '#D1FAE5', text: '#047857' },
  error: { bg: '#FEF2F2', border: '#FEE2E2', text: '#B91C1C' },
  info: { bg: '#EFF6FF', border: 'rgba(59,130,246,0.2)', text: '#1D4ED8' },
  warning: { bg: '#FFFBEB', border: '#FEF3C7', text: '#B45309' },
};

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const counter = useRef(0);

  const show = useCallback((message: string, tone: ToastTone = 'info') => {
    const id = `t-${++counter.current}`;
    setToasts((prev) => [...prev, { id, message, tone }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4000);
  }, []);

  const value: ToastContextValue = {
    show,
    success: (m) => show(m, 'success'),
    error: (m) => show(m, 'error'),
    info: (m) => show(m, 'info'),
    warning: (m) => show(m, 'warning'),
  };

  return (
    <ToastContext.Provider value={value}>
      {children}
      <View pointerEvents="box-none" style={[styles.container, { zIndex: 9999 }]}>
        {toasts.map((t) => (
          <ToastView
            key={t.id}
            item={t}
            onDismiss={() => setToasts((p) => p.filter((x) => x.id !== t.id))}
          />
        ))}
      </View>
    </ToastContext.Provider>
  );
}

function ToastView({ item, onDismiss }: { item: ToastItem; onDismiss: () => void }) {
  const opacity = useRef(new Animated.Value(0)).current;
  const tone = TONE[item.tone];

  useEffect(() => {
    Animated.timing(opacity, { toValue: 1, duration: 180, useNativeDriver: true }).start();
  }, [opacity]);

  return (
    <Animated.View
      style={[
        styles.card,
        {
          backgroundColor: tone.bg,
          borderColor: tone.border,
          opacity,
          transform: [
            {
              translateY: opacity.interpolate({
                inputRange: [0, 1],
                outputRange: [20, 0],
              }),
            },
          ],
        },
      ]}
    >
      <View style={styles.iconWrap}>{ICONS[item.tone]}</View>
      <Text style={[styles.message, { color: tone.text }]}>{item.message}</Text>
      <Pressable onPress={onDismiss} hitSlop={10} accessibilityLabel="Dismiss">
        <X size={16} color="#64748B" />
      </Pressable>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  container: {
    position: 'absolute',
    left: 0,
    right: 0,
    bottom: 16,
    alignItems: 'center',
    paddingHorizontal: 16,
  },
  card: {
    flexDirection: 'row',
    alignItems: 'center',
    width: '100%',
    maxWidth: 448,
    borderRadius: 8,
    borderWidth: 1,
    paddingHorizontal: 12,
    paddingVertical: 10,
    marginBottom: 8,
  },
  iconWrap: { marginRight: 8 },
  message: { flex: 1, fontSize: 14, fontWeight: '500' },
});
