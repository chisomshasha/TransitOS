import React, { useMemo } from 'react';
import { Pressable, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { usePathname, useRouter } from 'expo-router';
import { BarChart3, Bus, Home, LayoutGrid, Truck, User } from 'lucide-react-native';
import { useAuth } from '@/lib/auth-context';
import { tabsForRole, type TabId } from '@/lib/rbac';
import { brand } from '@/lib/theme';

export const BOTTOM_TABS_CONTENT_HEIGHT = 56;
export const BOTTOM_TABS_BASE_BOTTOM_PADDING = 6;

interface Tab {
  id: TabId;
  href: string;
  label: string;
  Icon: React.ComponentType<{ size?: number; color?: string }>;
}

const ALL_TABS: Tab[] = [
  { id: 'home', href: '/', label: 'Home', Icon: Home },
  { id: 'trips', href: '/trips', label: 'Trips', Icon: Bus },
  { id: 'vehicles', href: '/vehicles', label: 'Vehicles', Icon: Truck },
  { id: 'more', href: '/more', label: 'More', Icon: LayoutGrid },
  { id: 'reports', href: '/reports', label: 'Reports', Icon: BarChart3 },
  { id: 'me', href: '/profile', label: 'Me', Icon: User },
];

export function BottomTabs() {
  const router = useRouter();
  const pathname = usePathname();
  const { user } = useAuth();
  const insets = useSafeAreaInsets();
  const bottomInset = Math.max(insets.bottom, 0);

  const visibleTabs = useMemo(() => {
    const allowed = new Set(tabsForRole(user?.role));
    return ALL_TABS.filter((t) => allowed.has(t.id));
  }, [user?.role]);

  return (
    <View
      style={{
        position: 'absolute',
        left: 0,
        right: 0,
        bottom: 0,
        flexDirection: 'row',
        backgroundColor: '#FFFFFF',
        borderTopWidth: 1,
        borderTopColor: brand.border,
        paddingTop: 6,
        paddingHorizontal: 4,
        paddingBottom: bottomInset + BOTTOM_TABS_BASE_BOTTOM_PADDING,
        shadowColor: '#000',
        shadowOffset: { width: 0, height: -2 },
        shadowOpacity: 0.06,
        shadowRadius: 8,
        elevation: 8,
      }}
      pointerEvents="box-none"
    >
      {visibleTabs.map((tab) => {
        const active = isActive(pathname, tab.href);
        return (
          <Pressable
            key={tab.href}
            onPress={() => router.push(tab.href as never)}
            style={{ flex: 1, alignItems: 'center', justifyContent: 'center', paddingTop: 4 }}
            accessibilityRole="button"
            accessibilityLabel={tab.label}
            accessibilityState={{ selected: active }}
          >
            <tab.Icon size={22} color={active ? brand.navy : '#94A3B8'} />
            <Text
              style={{
                fontSize: 11,
                marginTop: 4,
                fontWeight: active ? '700' : '500',
                color: active ? brand.navy : '#94A3B8',
              }}
              numberOfLines={1}
            >
              {tab.label}
            </Text>
            <View
              style={{
                width: 16,
                height: 3,
                borderRadius: 2,
                marginTop: 4,
                backgroundColor: active ? brand.yellow : 'transparent',
              }}
            />
          </Pressable>
        );
      })}
    </View>
  );
}

function isActive(pathname: string, href: string): boolean {
  if (href === '/') return pathname === '/' || pathname === '';
  return pathname === href || pathname.startsWith(href + '/');
}
