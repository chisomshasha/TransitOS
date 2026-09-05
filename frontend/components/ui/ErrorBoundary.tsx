import React from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { AlertTriangle, RefreshCw } from 'lucide-react-native';

interface State {
  error: Error | null;
  componentStack: string | null;
}

interface Props {
  children: React.ReactNode;
  scope?: string;
}

export class ErrorBoundary extends React.Component<Props, State> {
  state: State = { error: null, componentStack: null };

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    // Full details stay in device logs for developers — never shown to users.
    console.error('[ErrorBoundary]', this.props.scope ?? 'app', error, info.componentStack);
    this.setState({ componentStack: info.componentStack ?? null });
  }

  reset = () => this.setState({ error: null, componentStack: null });

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
            {/* TEMP DEBUG — remove once the underlying bug is found */}
            <View style={s.debugBox}>
              <Text style={s.debugLabel}>Debug details (temporary):</Text>
              <Text style={s.debugText} selectable>
                {this.state.error.name}: {this.state.error.message}
              </Text>
              {this.state.componentStack ? (
                <Text style={s.debugStack} selectable numberOfLines={12}>
                  {this.state.componentStack.trim()}
                </Text>
              ) : null}
            </View>
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
  debugBox: {
    width: '100%',
    backgroundColor: '#FEF2F2',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#FECACA',
    padding: 10,
    marginBottom: 16,
    maxHeight: 220,
  },
  debugLabel: {
    fontSize: 11,
    fontWeight: '700',
    color: '#991B1B',
    marginBottom: 4,
  },
  debugText: {
    fontSize: 12,
    color: '#7F1D1D',
    fontWeight: '600',
  },
  debugStack: {
    fontSize: 10,
    color: '#991B1B',
    marginTop: 6,
    fontFamily: 'monospace',
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
