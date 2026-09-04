import React from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { AlertTriangle, RefreshCw } from 'lucide-react-native';

interface State {
  error: Error | null;
}

interface Props {
  children: React.ReactNode;
  scope?: string;
}

export class ErrorBoundary extends React.Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    // Full details stay in device logs for developers — never shown to users.
    console.error('[ErrorBoundary]', this.props.scope ?? 'app', error, info.componentStack);
  }

  reset = () => this.setState({ error: null });

  render() {
    if (this.state.error) {
      return (
        <View style={s.outer}>
          <View style={s.card}>
            <View style={s.iconBox}>
              <AlertTriangle size={22} color="#B91C1C" />
            </View>
            <Text style={s.title}>Something went wrong</Text>
            <Text style={s.message}>
              {this.props.scope
                ? `This ${this.props.scope} screen hit an unexpected error.`
                : 'The app hit an unexpected error.'}
              {'\n'}Your session is safe — please try again.
            </Text>
            <Pressable
              onPress={this.reset}
              style={({ pressed }) => [s.retryButton, pressed && { opacity: 0.85 }]}
              accessibilityRole="button"
              accessibilityLabel="Try again"
            >
              <RefreshCw size={16} color="#FFFFFF" />
              <Text style={s.retryText}>Try again</Text>
            </Pressable>
          </View>
        </View>
      );
    }
    return this.props.children;
  }
}

const s = StyleSheet.create({
  outer: {
    flex: 1,
    backgroundColor: '#F8F7F4',
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 24,
  },
  card: {
    width: '100%',
    maxWidth: 400,
    backgroundColor: '#FFFFFF',
    borderRadius: 16,
    borderWidth: 1,
    borderColor: '#E5E7EB',
    padding: 24,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.08,
    shadowRadius: 12,
    elevation: 4,
  },
  iconBox: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: '#FEF2F2',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 12,
  },
  title: {
    fontSize: 18,
    fontWeight: '700',
    color: '#111827',
    marginBottom: 8,
  },
  message: {
    fontSize: 14,
    color: '#6B7280',
    textAlign: 'center',
    lineHeight: 20,
    marginBottom: 20,
  },
  retryButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    height: 48,
    borderRadius: 12,
    backgroundColor: '#0B3D91',
    width: '100%',
  },
  retryText: {
    color: '#FFFFFF',
    fontWeight: '600',
    marginLeft: 8,
  },
});
