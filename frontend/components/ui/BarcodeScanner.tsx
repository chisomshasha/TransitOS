/**
 * BarcodeScanner — full-screen camera view that scans QR + common
 * 1D barcodes and fires `onScan(data)` on the first successful read.
 *
 * Uses expo-camera's modern CameraView API (SDK 54+). The parent
 * is responsible for installing `expo-camera` in package.json and
 * adding it to app.json plugins.
 */
import React, { useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { CameraView, useCameraPermissions, type BarcodeScanningResult } from 'expo-camera';
import { X, RotateCcw, Camera } from 'lucide-react-native';
import { brand } from '@/lib/theme';

interface BarcodeScannerProps {
  onScan: (data: string) => void;
  onClose: () => void;
  /** Optional label shown above the viewfinder */
  hint?: string;
}

export function BarcodeScanner({ onScan, onClose, hint }: BarcodeScannerProps) {
  const [permission, requestPermission] = useCameraPermissions();
  const [scanned, setScanned] = useState(false);

  if (!permission) {
    return (
      <View style={s.container}>
        <View style={s.permissionCard}>
          <Camera size={32} color={brand.navy} />
          <Text style={s.permissionTitle}>Camera access needed</Text>
          <Text style={s.permissionBody}>
            TransitOS needs camera access to scan vehicle and driver QR codes.
          </Text>
          <Pressable style={s.permissionBtn} onPress={requestPermission}>
            <Text style={s.permissionBtnText}>Grant permission</Text>
          </Pressable>
        </View>
      </View>
    );
  }

  if (!permission.granted) {
    return (
      <View style={s.container}>
        <View style={s.permissionCard}>
          <Camera size={32} color={brand.navy} />
          <Text style={s.permissionTitle}>Permission denied</Text>
          <Text style={s.permissionBody}>
            Please enable camera access in your device settings.
          </Text>
          <Pressable style={s.permissionBtn} onPress={onClose}>
            <Text style={s.permissionBtnText}>Go back</Text>
          </Pressable>
        </View>
      </View>
    );
  }

  const handleScan = (result: BarcodeScanningResult) => {
    if (scanned) return;
    setScanned(true);
    onScan(result.data);
  };

  return (
    <View style={s.container}>
      <CameraView
        style={StyleSheet.absoluteFillObject}
        onBarcodeScanned={scanned ? undefined : handleScan}
        barcodeScannerSettings={{
          barcodeTypes: ['qr', 'code128', 'code39', 'ean13', 'ean8', 'upc_a', 'upc_e'],
        }}
      />

      {/* Viewfinder overlay */}
      <View style={s.overlay} pointerEvents="none">
        <View style={s.viewfinder}>
          <View style={[s.corner, s.cornerTL]} />
          <View style={[s.corner, s.cornerTR]} />
          <View style={[s.corner, s.cornerBL]} />
          <View style={[s.corner, s.cornerBR]} />
        </View>
        {hint ? <Text style={s.hintText}>{hint}</Text> : null}
      </View>

      {/* Close button */}
      <Pressable style={s.closeBtn} onPress={onClose} accessibilityLabel="Close scanner">
        <X size={20} color="#FFFFFF" />
      </Pressable>

      {/* Rescan button after a successful scan */}
      {scanned ? (
        <Pressable style={s.rescanBtn} onPress={() => setScanned(false)}>
          <RotateCcw size={16} color="#FFFFFF" />
          <Text style={s.rescanText}>Scan another</Text>
        </Pressable>
      ) : null}
    </View>
  );
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#000' },
  overlay: {
    ...StyleSheet.absoluteFillObject,
    alignItems: 'center',
    justifyContent: 'center',
  },
  viewfinder: {
    width: 260,
    height: 260,
    position: 'relative',
  },
  corner: {
    position: 'absolute',
    width: 30,
    height: 30,
    borderColor: brand.yellow,
  },
  cornerTL: { top: 0, left: 0, borderTopWidth: 4, borderLeftWidth: 4 },
  cornerTR: { top: 0, right: 0, borderTopWidth: 4, borderRightWidth: 4 },
  cornerBL: { bottom: 0, left: 0, borderBottomWidth: 4, borderLeftWidth: 4 },
  cornerBR: { bottom: 0, right: 0, borderBottomWidth: 4, borderRightWidth: 4 },
  hintText: {
    marginTop: 20,
    color: '#FFFFFF',
    fontSize: 14,
    fontWeight: '600',
    textAlign: 'center',
    paddingHorizontal: 40,
    textShadowColor: 'rgba(0,0,0,0.6)',
    textShadowOffset: { width: 0, height: 1 },
    textShadowRadius: 4,
  },
  closeBtn: {
    position: 'absolute',
    top: 56,
    right: 16,
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: 'rgba(0,0,0,0.5)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  rescanBtn: {
    position: 'absolute',
    bottom: 60,
    alignSelf: 'center',
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: brand.navy,
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderRadius: 24,
    gap: 8,
  },
  rescanText: { color: '#FFFFFF', fontWeight: '700', fontSize: 14 },
  permissionCard: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 32,
    backgroundColor: brand.bg,
  },
  permissionTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: brand.slate,
    marginTop: 16,
  },
  permissionBody: {
    fontSize: 14,
    color: brand.muted,
    textAlign: 'center',
    marginTop: 8,
    lineHeight: 20,
  },
  permissionBtn: {
    marginTop: 20,
    backgroundColor: brand.navy,
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 12,
  },
  permissionBtnText: { color: '#FFFFFF', fontWeight: '700', fontSize: 14 },
});
