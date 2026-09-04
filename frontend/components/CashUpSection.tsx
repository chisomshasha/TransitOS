import React, { useMemo, useState } from 'react';
import { StyleSheet, Text, TextInput, View } from 'react-native';
import { Wallet } from 'lucide-react-native';
import { useCashUps, useCreateCashUp } from '@/lib/queries';
import { useToast } from '@/components/ui/Toast';
import { Button } from '@/components/ui/Button';
import { formatNGN } from '@/lib/format';
import type { Trip } from '@/lib/types';

export interface CashUpSectionProps {
  trip: Trip;
}

const DENOMS = [1000, 500, 200, 100, 50] as const;

export function CashUpSection({ trip }: CashUpSectionProps) {
  const toast = useToast();
  const create = useCreateCashUp();
  const list = useCashUps({ trip_id: trip.id });
  const items = list.data?.items ?? [];
  const latest = items[0];

  // Denomination counting is purely a client-side convenience for
  // arriving at a cash total — the backend only stores a payment-method
  // breakdown (method/amount), not per-denomination counts, so we don't
  // try to reverse-populate these inputs from an existing cash-up.
  const [counts, setCounts] = useState<Record<number, string>>({});
  const [coins, setCoins] = useState('');

  const counted = useMemo(() => {
    let total = 0;
    DENOMS.forEach((d) => {
      const n = parseInt(counts[d] ?? '', 10) || 0;
      total += n * d;
    });
    total += parseFloat(coins || '0') || 0;
    return total;
  }, [counts, coins]);

  const expected = trip.total_revenue ?? 0;
  const variance = counted - expected;

  const onSubmit = async () => {
    try {
      await create.mutateAsync({
        trip_id: trip.id,
        conductor_id: trip.conductor_id,
        branch_id: trip.branch_id,
        breakdown: [{ method: 'cash', amount: counted }],
        declared_total: counted,
      });
      toast.success('Cash-up submitted');
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? 'Could not submit cash-up');
    }
  };

  return (
    <View style={s.card}>
      <View style={s.header}>
        <Wallet size={18} color="#0E7490" />
        <Text style={s.title}>Cash-up</Text>
      </View>
      <Text style={s.description}>
        Conductor declares takings by denomination. System compares against manifest revenue.
      </Text>
      <View style={s.grid}>
        {DENOMS.map((d) => (
          <DenomInput
            key={d}
            label={`₦${d.toLocaleString()}`}
            value={counts[d] ?? ''}
            onChange={(v) => setCounts((p) => ({ ...p, [d]: v }))}
          />
        ))}
        <DenomInput label="Coins (₦)" value={coins} onChange={setCoins} />
      </View>
      <View style={s.summary}>
        <Row label="Expected (system)" value={formatNGN(expected)} />
        <Row label="Counted (physical)" value={formatNGN(counted)} />
        <View style={s.row}>
          <Text style={s.rowLabelBold}>Variance</Text>
          <Text style={[s.rowValueBold, { color: variance >= 0 ? '#047857' : '#B91C1C' }]}>
            {formatNGN(variance)}
          </Text>
        </View>
        {latest ? (
          <View style={s.row}>
            <Text style={s.rowLabel}>Latest submitted</Text>
            <Text style={s.rowValue}>
              {formatNGN(latest.declared_total)} · {latest.status}
            </Text>
          </View>
        ) : null}
      </View>
      <View style={s.buttonWrap}>
        <Button
          label={latest ? 'Update cash-up' : 'Submit cash-up'}
          onPress={onSubmit}
          loading={create.isPending}
          fullWidth
        />
      </View>
    </View>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <View style={s.row}>
      <Text style={s.rowLabel}>{label}</Text>
      <Text style={s.rowValue}>{value}</Text>
    </View>
  );
}

function DenomInput({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  return (
    <View style={s.denomWrap}>
      <Text style={s.denomLabel}>{label}</Text>
      <TextInput
        style={s.denomInput}
        value={value}
        onChangeText={onChange}
        keyboardType="numeric"
        placeholder="0"
        placeholderTextColor="#94A3B8"
      />
    </View>
  );
}

const s = StyleSheet.create({
  card: { backgroundColor: '#FFFFFF', borderRadius: 12, borderWidth: 1, borderColor: '#E5E7EB', padding: 16 },
  header: { flexDirection: 'row', alignItems: 'center' },
  title: { fontSize: 16, fontWeight: '600', color: '#1E293B', marginLeft: 8 },
  description: { fontSize: 12, color: '#64748B', marginTop: 2 },
  grid: { flexDirection: 'row', flexWrap: 'wrap', marginHorizontal: -6, marginTop: 12 },
  denomWrap: { width: '50%', paddingHorizontal: 6, marginBottom: 12 },
  denomLabel: { fontSize: 12, fontWeight: '600', color: '#475569', marginBottom: 4 },
  denomInput: { height: 44, paddingHorizontal: 12, borderRadius: 12, borderWidth: 1, borderColor: '#E2E8F0', backgroundColor: '#FFFFFF', fontSize: 16, color: '#0F172A' },
  summary: { backgroundColor: '#F8FAFC', borderRadius: 12, padding: 12, marginTop: 4 },
  row: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 4 },
  rowLabel: { fontSize: 14, color: '#475569' },
  rowValue: { fontSize: 14, fontWeight: '600', color: '#1E293B' },
  rowLabelBold: { fontSize: 14, fontWeight: '600', color: '#475569' },
  rowValueBold: { fontSize: 14, fontWeight: '700' },
  buttonWrap: { marginTop: 12 },
});
