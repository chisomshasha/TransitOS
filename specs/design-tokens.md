# TransitOS Sprint A — Design Tokens & Component Library

> **Source of truth for the frontend engineer.** The design system
> is intentionally small in Sprint A — 12 primitives — but every
> primitive is a real, typed, tested component, not a styled
> `Pressable`. NativeWind v4 is the layout utility; the primitives
> in `components/ui/` are what the screens actually compose from.
> Ad-hoc Tailwind is reserved for one-off layout (flex, padding,
> margin) — never for buttons, cards, or inputs.

---

## 0 · Design language

**Three words**: **operational, trustworthy, fast.** The owner
checks this app between board meetings. The driver checks it from
a moving bus. The branch accountant squints at it in a poorly-lit
office at 11pm during cash-up. Every token reflects those three
constraints:

- High contrast (works outdoors, works in dim light)
- Large tap targets (44pt minimum — driver-friendly)
- Conservative motion (no bounces, no springs — respect users on
  slow Nigerian 3G)

**No** is the most-used word in this spec. We do not add a new
shade, a new spacing step, or a new component variant without a
real screen that needs it.

---

## 1 · Color palette

### 1.1 Primary — Transit Teal
A deep, slightly desaturated teal-cyan. Reads as "infrastructure"
without screaming "tech startup". Used for: primary CTAs, active
tab indicator, focus ring, brand mark.

| Token            | Hex       | Tailwind  | Use                                |
|------------------|-----------|-----------|------------------------------------|
| `primary-50`     | `#ECFEFF` | `cyan-50` | Subtle background tint             |
| `primary-100`    | `#CFFAFE` | `cyan-100`| Hover surface (filled button)      |
| `primary-200`    | `#A5F3FC` | `cyan-200`| —                                  |
| `primary-300`    | `#67E8F9` | `cyan-300`| —                                  |
| `primary-400`    | `#22D3EE` | `cyan-400`| Decorative accent                  |
| `primary-500`    | `#06B6D4` | `cyan-500`| Secondary button                   |
| **`primary-600`**| **`#0891B2`** | **`cyan-600`** | **Default brand action**     |
| `primary-700`    | `#0E7490` | `cyan-700`| Pressed state                      |
| `primary-800`    | `#155E75` | `cyan-800`| —                                  |
| `primary-900`    | `#164E63` | `cyan-900`| Dark mode surface (text on light) |

### 1.2 Secondary — Road Amber
A warm amber. Reads as "fuel, energy, the road". Used for: warning
badges, the secondary CTA, profile highlights.

| Token            | Hex       | Tailwind  | Use                                |
|------------------|-----------|-----------|------------------------------------|
| `secondary-50`   | `#FFFBEB` | `amber-50`| —                                  |
| `secondary-100`  | `#FEF3C7` | `amber-100`| —                                 |
| `secondary-200`  | `#FDE68A` | `amber-200`| —                                 |
| `secondary-300`  | `#FCD34D` | `amber-300`| —                                 |
| `secondary-400`  | `#FBBF24` | `amber-400`| —                                 |
| **`secondary-500`**| **`#F59E0B`** | **`amber-500`** | **Secondary CTA, warning**|
| `secondary-600`  | `#D97706` | `amber-600`| Pressed                           |
| `secondary-700`  | `#B45309` | `amber-700`| —                                 |

### 1.3 Semantic

| Token         | Hex       | Tailwind     | Use                                  |
|---------------|-----------|--------------|--------------------------------------|
| `success-50`  | `#ECFDF5` | `emerald-50` | Success toast background              |
| `success-100` | `#D1FAE5` | `emerald-100`| Success badge bg                     |
| `success-500` | `#10B981` | `emerald-500`| Success badge text, success border   |
| `success-700` | `#047857` | `emerald-700`| Success text on light                |
| `warning-50`  | `#FFFBEB` | `amber-50`   | Warning background                   |
| `warning-100` | `#FEF3C7` | `amber-100`  | Warning badge bg                     |
| `warning-500` | `#F59E0B` | `amber-500`  | Warning badge text                   |
| `warning-700` | `#B45309` | `amber-700`  | Warning text                         |
| `danger-50`   | `#FEF2F2` | `red-50`     | Error background, error toast        |
| `danger-100`  | `#FEE2E2` | `red-100`    | Error badge bg                       |
| `danger-500`  | `#EF4444` | `red-500`    | Error badge text, error border       |
| `danger-700`  | `#B91C1C` | `red-700`    | Error text                           |
| `info-50`     | `#EFF6FF` | `blue-50`    | Info background                      |
| `info-500`    | `#3B82F6` | `blue-500`   | Info badge, link                     |
| `info-700`    | `#1D4ED8` | `blue-700`   | Info text                            |

### 1.4 Neutrals — Slate
Cool slate. Used for: text, borders, dividers, surface.

| Token         | Hex       | Tailwind  | Use                                |
|---------------|-----------|-----------|------------------------------------|
| `neutral-0`   | `#FFFFFF` | `white`   | Pure white surface                 |
| `neutral-50`  | `#F8FAFC` | `slate-50`| App background                     |
| `neutral-100` | `#F1F5F9` | `slate-100`| Subtle surface (hover)            |
| `neutral-200` | `#E2E8F0` | `slate-200`| Border (default)                  |
| `neutral-300` | `#CBD5E1` | `slate-300`| Border (strong)                   |
| `neutral-400` | `#94A3B8` | `slate-400`| Disabled text, placeholder        |
| `neutral-500` | `#64748B` | `slate-500`| Secondary text                    |
| `neutral-600` | `#475569` | `slate-600`| Body text (secondary)             |
| **`neutral-700`**| **`#334155`** | **`slate-700`** | **Body text (default)**     |
| `neutral-800` | `#1E293B` | `slate-800`| Heading text                      |
| `neutral-900` | `#0F172A` | `slate-900`| Strongest text                    |

### 1.5 Domain-specific (Sprint B will add more)

| Token            | Hex       | Use                                      |
|------------------|-----------|------------------------------------------|
| `trip-active`    | `#10B981` | Active trip badge (Sprint B)             |
| `trip-delayed`   | `#F59E0B` | Delayed trip badge (Sprint B)            |
| `cash-good`      | `#10B981` | Variance within ±2% (Sprint B)           |
| `cash-warn`      | `#F59E0B` | Variance within ±10% (Sprint B)          |
| `cash-leak`      | `#EF4444` | Variance >10% (Sprint B)                 |

These are listed now so the palette stays consistent across sprints.

### 1.6 Dark mode (declared, not implemented in Sprint A)
Sprint A is **light mode only**. The token names above already
slot into NativeWind's dark mode class extension; flipping to dark
in Sprint C is a token swap, not a redesign.

---

## 2 · Typography

System font stack. **No custom font files in Sprint A** — the build
must stay fast on slow networks and offline.

```css
font-family: -apple-system, BlinkMacSystemFont, "Segoe UI",
             Roboto, "Helvetica Neue", Arial, sans-serif;
```

| Token           | Size (pt) | Line height | Weight | Tailwind    | Use                       |
|-----------------|-----------|-------------|--------|-------------|---------------------------|
| `text-display`  | 32        | 40          | 700    | `text-3xl font-bold`     | Screen title (rarely)     |
| `text-h1`       | 24        | 32          | 700    | `text-2xl font-bold`     | Page title                |
| `text-h2`       | 20        | 28          | 600    | `text-xl font-semibold`  | Section header            |
| `text-h3`       | 18        | 26          | 600    | `text-lg font-semibold`  | Card title                |
| `text-body`     | 16        | 24          | 400    | `text-base`              | Default body              |
| `text-body-strong` | 16     | 24          | 600    | `text-base font-semibold`| List item title           |
| `text-caption`  | 14        | 20          | 400    | `text-sm`                | Helper text, table cells  |
| `text-overline` | 12        | 16          | 600    | `text-xs font-semibold uppercase tracking-wide` | Section label, badge text |
| `text-mono`     | 14        | 20          | 500    | `text-sm font-medium tabular-nums` | Currency, odometer, count |

**Letter spacing**: `tracking-wide` (0.025em) only on `text-overline`.

**Numerics**: any column that shows money or counts uses
`font-variant-numeric: tabular-nums` so columns line up.

---

## 3 · Spacing scale

Eight steps. **No 7, no 9, no 13.** Use the closest token.

| Token        | Value (pt) | Tailwind  | Use                                |
|--------------|------------|-----------|------------------------------------|
| `space-1`    | 4          | `p-1`     | Icon-to-text gap                   |
| `space-2`    | 8          | `p-2`     | Inline gap                         |
| `space-3`    | 12         | `p-3`     | Card inner padding (compact)       |
| `space-4`    | 16         | `p-4`     | Card inner padding (default)       |
| `space-6`    | 24         | `p-6`     | Section gap                        |
| `space-8`    | 32         | `p-8`     | Page edge padding (compact)        |
| `space-12`   | 48         | `p-12`    | Page edge padding (default)        |
| `space-16`   | 64         | `p-16`    | Hero / empty-state                 |

### Layout grid
- Screen edge padding: `space-4` (16pt) on phones, `space-8` (32pt) on tablets.
- Card-to-card gap: `space-3` (12pt).
- Section-to-section gap: `space-6` (24pt).

---

## 4 · Border radius

| Token    | Value (pt) | Tailwind    | Use                          |
|----------|------------|-------------|------------------------------|
| `rounded-sm`  | 4    | `rounded-sm`  | Tags, badges (small)         |
| `rounded`     | 8    | `rounded`     | Inputs, buttons              |
| `rounded-md`  | 12   | `rounded-md`  | Cards                        |
| `rounded-lg`  | 16   | `rounded-lg`  | Modal, bottom sheet          |
| `rounded-full`| 9999 | `rounded-full`| Avatars, status dots         |

---

## 5 · Shadow / elevation

Three elevations. **No more.** Higher elevations feel gamey and
hide taps in bright sunlight.

| Token       | iOS              | Android          | Use                          |
|-------------|------------------|------------------|------------------------------|
| `shadow-sm` | `0 1 2 rgba(15,23,42,0.05)` | `elevation 1` | Subtle border replacement    |
| `shadow`    | `0 2 4 rgba(15,23,42,0.08)` | `elevation 2` | Cards                        |
| `shadow-lg` | `0 8 24 rgba(15,23,42,0.12)`| `elevation 8` | Modal, popover, toast        |

All shadows use `rgba(15, 23, 42, X)` — that's `neutral-900` with
alpha. **No pure black, ever** — looks too harsh on AMOLED.

---

## 6 · Component primitives

Twelve primitives. Each is a real component in `components/ui/`.
Each has explicit props and three states: **default / hover-or-focused
/ disabled**. **Error** is a variant, not a state, on inputs.

### 6.1 `<Button />`
**File**: `components/ui/Button.tsx`
**Props**:
```ts
type ButtonVariant = 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger';
type ButtonSize    = 'sm' | 'md' | 'lg';

interface ButtonProps {
  label: string;
  onPress: () => void;
  variant?: ButtonVariant;        // default: 'primary'
  size?: ButtonSize;                // default: 'md'
  loading?: boolean;                // shows Spinner, disables press
  disabled?: boolean;
  icon?: React.ReactNode;           // lucide icon
  iconPosition?: 'left' | 'right';  // default: 'left'
  fullWidth?: boolean;              // default: false
  testID?: string;
}
```

**Variants**:
- `primary` — `bg-primary-600 text-white`
- `secondary` — `bg-secondary-500 text-white`
- `outline` — `border border-neutral-300 bg-white text-neutral-800`
- `ghost` — `bg-transparent text-primary-700`
- `danger` — `bg-danger-500 text-white`

**Sizes**:
- `sm` — h-8 px-3 text-caption
- `md` — h-11 px-4 text-body (default; 44pt tap target)
- `lg` — h-14 px-6 text-body-strong

**States**: default, pressed (`opacity-80`), disabled
(`opacity-40`), loading (Spinner replaces label, width locked).

### 6.2 `<Input />`
**File**: `components/ui/Input.tsx`
**Props**:
```ts
interface InputProps {
  value: string;
  onChangeText: (v: string) => void;
  placeholder?: string;
  label?: string;             // rendered by <Field> wrapper, not Input itself
  error?: string;             // red border + helper text
  helperText?: string;
  disabled?: boolean;
  secureTextEntry?: boolean;  // for password
  keyboardType?: 'default' | 'email-address' | 'numeric' | 'phone-pad';
  autoCapitalize?: 'none' | 'words' | 'sentences';
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  testID?: string;
}
```

The Input renders **only the text field**. Labels, helper text,
and error are composed via `<Field>` (§6.4). This is the
sneaky detail that makes forms readable.

**Variants**:
- `default` — `border-neutral-300 bg-white`
- `error` — `border-danger-500 bg-danger-50`
- `disabled` — `bg-neutral-100 text-neutral-400`

**Sizes**: single size — `h-11 px-3 text-body`.

### 6.3 `<Card />`
**File**: `components/ui/Card.tsx`
**Props**:
```ts
interface CardProps {
  children: React.ReactNode;
  onPress?: () => void;       // if set, renders as Pressable
  variant?: 'default' | 'outlined' | 'elevated';
  padding?: 'sm' | 'md' | 'lg';  // default: 'md' (space-4)
  className?: string;
}
```

**Variants**:
- `default` — `bg-white rounded-md shadow`
- `outlined` — `bg-white rounded-md border border-neutral-200`
- `elevated` — `bg-white rounded-md shadow-lg`

If `onPress` is set, the card adds `active:opacity-80` and a subtle
scale press.

### 6.4 `<Field />`
**File**: `components/ui/Field.tsx`
**Props**:
```ts
interface FieldProps {
  label: string;                 // required
  required?: boolean;            // adds red asterisk
  error?: string;                // replaces helperText
  helperText?: string;
  children: React.ReactNode;     // typically <Input />
}
```

**Anatomy** (top to bottom):
- `text-overline text-neutral-600` label
- `text-caption text-danger-700` error OR `text-caption text-neutral-500` helper
- the `children` (Input, Select, etc.)

Use this **everywhere** there is a labelled input. No bare Inputs.

### 6.5 `<Select />`
**File**: `components/ui/Select.tsx`
**Props**:
```ts
interface SelectOption<T extends string> {
  label: string;
  value: T;
}

interface SelectProps<T extends string> {
  value: T | null;
  onChange: (v: T) => void;
  options: SelectOption<T>[];
  placeholder?: string;
  disabled?: boolean;
  error?: string;
  testID?: string;
}
```

Sprint A implementation: a `Pressable` styled like Input that opens
a `Modal` (bottom-sheet on iOS, dialog on Android) with a scrollable
list of options. **Not** the native Picker (terrible a11y, doesn't
match the design system). The single-select version is enough for
Sprint A; multi-select comes in Sprint B.

### 6.6 `<Modal />`
**File**: `components/ui/Modal.tsx`
**Props**:
```ts
interface ModalProps {
  visible: boolean;
  onClose: () => void;
  title?: string;
  children: React.ReactNode;
  primaryAction?: { label: string; onPress: () => void; loading?: boolean; };
  secondaryAction?: { label: string; onPress: () => void; };
  size?: 'sm' | 'md' | 'lg';  // max-w on tablet; full-width on phone
}
```

Wraps RN's `Modal` with our styling. Renders a scrim
(`bg-neutral-900/50`), a card with `rounded-lg shadow-lg`, and a
header (title + close). **Always provide at least a Close button
or have a tap-on-scrim `onClose`.**

### 6.7 `<Toast />`
**File**: `components/ui/Toast.tsx`
**Props**:
```ts
type ToastVariant = 'success' | 'error' | 'info' | 'warning';

interface ToastProps {
  visible: boolean;
  message: string;
  variant?: ToastVariant;       // default: 'info'
  duration?: number;            // default: 3000ms
  onHide: () => void;
}
```

Use the `react-native-toast-message` library under the hood — wrap
it so screens call `<Toast />` directly without importing a
third-party component. Variants map to the semantic color tokens.

### 6.8 `<Badge />`
**File**: `components/ui/Badge.tsx`
**Props**:
```ts
type BadgeVariant = 'neutral' | 'success' | 'warning' | 'danger' | 'info' | 'primary';

interface BadgeProps {
  label: string;
  variant?: BadgeVariant;       // default: 'neutral'
  size?: 'sm' | 'md';            // default: 'sm'
}
```

**Variants** (text + bg + border, never solid fill):
- `neutral` — `bg-neutral-100 text-neutral-700`
- `success` — `bg-success-100 text-success-700`
- `warning` — `bg-warning-100 text-warning-700`
- `danger`  — `bg-danger-100 text-danger-700`
- `info`    — `bg-info-50 text-info-700`
- `primary` — `bg-primary-50 text-primary-700`

**Sizes**:
- `sm` — `px-2 py-0.5 text-overline`
- `md` — `px-3 py-1 text-caption`

### 6.9 `<EmptyState />`
**File**: `components/ui/EmptyState.tsx`
**Props**:
```ts
interface EmptyStateProps {
  icon?: React.ReactNode;          // lucide icon, 48pt
  title: string;                   // "No branches yet"
  description?: string;            // 1-2 sentences
  action?: { label: string; onPress: () => void; };
}
```

Centered column: icon → `text-h3` title → `text-caption text-neutral-500`
description → optional `<Button variant="primary" />` action.

### 6.10 `<Spinner />`
**File**: `components/ui/Spinner.tsx`
**Props**:
```ts
interface SpinnerProps {
  size?: 'sm' | 'md' | 'lg';     // 16 / 24 / 32 pt
  color?: string;                 // default: primary-600
}
```

Uses RN's `ActivityIndicator`. `sm` is for inline (button, badge);
`md` is the default full-page loader; `lg` is for the auth hydration
gate.

### 6.11 `<Skeleton />`
**File**: `components/ui/Skeleton.tsx`
**Props**:
```ts
interface SkeletonProps {
  width?: number | string;        // default: '100%'
  height?: number | string;       // default: 16
  rounded?: 'sm' | 'md' | 'full'; // default: 'sm'
  count?: number;                 // repeat the line N times with gap
}
```

A neutral-200 block with a subtle pulse. Use this in list-screen
loading states, not a Spinner — the user can already see the page
shape, they just need the data to land.

### 6.12 `<Tabs />`
**File**: `components/ui/Tabs.tsx`
**Props**:
```ts
interface TabsProps {
  value: string;                              // active tab id
  onChange: (id: string) => void;
  items: { id: string; label: string; badge?: string }[];
}
```

A horizontal row of pill-style tabs. Active tab: `bg-primary-600
text-white`. Inactive: `text-neutral-600`. Underline-style tabs are
**not** used — the pill style is more legible on small phones.

> Note: this primitive is for **in-page** tab bars (e.g. the
> Branch detail page in Sprint B). The Expo Router's
> `(tabs)/_layout.tsx` is a separate construct and is documented
> in `sprint-a-tasks.md` §3.

---

## 7 · `components/ui/` folder layout

```
components/
  ui/
    index.ts                  // barrel: re-exports all primitives
    Button.tsx
    Input.tsx
    Card.tsx
    Field.tsx
    Select.tsx
    Modal.tsx
    Toast.tsx
    Badge.tsx
    EmptyState.tsx
    Spinner.tsx
    Skeleton.tsx
    Tabs.tsx
    cn.ts                     // tailwind class merge helper (clsx + tailwind-merge)
    theme.ts                  // the color tokens as a typed object (mirror of §1)
```

`cn.ts`:
```ts
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

`theme.ts` exports `colors`, `spacing`, `radius`, `shadow`, `text`
as plain objects — screens that need to look up a token at runtime
(rare) import from here instead of stringifying Tailwind class names.

---

## 8 · `tailwind.config.js` integration

The frontend engineer's `tailwind.config.js` MUST extend with the
palette from §1. Don't redefine — `extend`:

```js
// tailwind.config.js
module.exports = {
  content: ['./app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}'],
  presets: [require('nativewind/preset')],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#ECFEFF', 100: '#CFFAFE', 200: '#A5F3FC',
          300: '#67E8F9', 400: '#22D3EE', 500: '#06B6D4',
          600: '#0891B2', 700: '#0E7490', 800: '#155E75', 900: '#164E63',
        },
        secondary: {
          50: '#FFFBEB', 100: '#FEF3C7', 200: '#FDE68A',
          300: '#FCD34D', 400: '#FBBF24', 500: '#F59E0B',
          600: '#D97706', 700: '#B45309',
        },
        success: {
          50: '#ECFDF5', 100: '#D1FAE5', 500: '#10B981', 700: '#047857',
        },
        warning: {
          50: '#FFFBEB', 100: '#FEF3C7', 500: '#F59E0B', 700: '#B45309',
        },
        danger: {
          50: '#FEF2F2', 100: '#FEE2E2', 500: '#EF4444', 700: '#B91C1C',
        },
        info: {
          50: '#EFF6FF', 500: '#3B82F6', 700: '#1D4ED8',
        },
        neutral: {
          0: '#FFFFFF', 50: '#F8FAFC', 100: '#F1F5F9', 200: '#E2E8F0',
          300: '#CBD5E1', 400: '#94A3B8', 500: '#64748B', 600: '#475569',
          700: '#334155', 800: '#1E293B', 900: '#0F172A',
        },
      },
      spacing: {
        'space-1': '4pt', 'space-2': '8pt', 'space-3': '12pt',
        'space-4': '16pt', 'space-6': '24pt', 'space-8': '32pt',
        'space-12': '48pt', 'space-16': '64pt',
      },
      borderRadius: {
        sm: '4pt', DEFAULT: '8pt', md: '12pt', lg: '16pt', full: '9999pt',
      },
    },
  },
};
```

**The screens and primitives only use these tokens.** No
`bg-blue-500` from the default Tailwind palette. If the verifier
finds `bg-red-`, `bg-green-`, `bg-blue-` (other than `bg-info-`), or
`bg-purple-` etc. outside this file, the spec has been violated.

---

## 9 · Accessibility

- Every interactive element has a `testID` and a meaningful
  `accessibilityLabel` (set by the screen, not the primitive).
- Color is never the sole carrier of meaning: a status badge always
  has a text label. A destructive Button uses `variant="danger"`
  **and** a "Delete" label.
- Touch targets ≥ 44pt (`size="md"` Button and all `Input`s).
- Contrast: text on white ≥ 4.5:1; tokens above are picked to
  satisfy this. Do not introduce lighter text colors.
- Reduce-motion respected: Skeleton pulse uses `transform` and
  honors `AccessibilityInfo.isReduceMotionEnabled`.

---

## 10 · What is NOT in Sprint A

The following are deferred:

- Dark mode (token names ready, theme not flipped)
- Multi-select, search, combobox (Select is single-select only)
- Date picker, time picker (form fields are typed strings for now)
- Carousel, accordion, stepper, breadcrumb — not needed yet
- Custom font — system stack only
- Animated illustrations — the EmptyState icon is enough
- Charts — Sprint B/C (Owner dashboard)
- Bottom-sheet library — Modal suffices for Sprint A
