import React, { useMemo } from 'react';
import { ActivityIndicator, StyleSheet, Text, View } from 'react-native';
import { WebView } from 'react-native-webview';
import { MapPin, Crosshair } from 'lucide-react-native';
import { Modal } from './Modal';

export interface MapPoint {
  id: string;
  lat: number;
  lng: number;
  label: string;
  color?: 'primary' | 'success' | 'danger' | 'warning' | 'info' | 'neutral';
  description?: string;
}

export interface MapPath {
  coordinates: Array<[number, number]>;
  color?: 'primary' | 'success' | 'danger' | 'warning' | 'info';
}

export interface MapModalProps {
  visible: boolean;
  onClose: () => void;
  title?: string;
  points: MapPoint[];
  paths?: MapPath[];
  center?: { lat: number; lng: number };
  zoom?: number;
  height?: number;
  pickMode?: boolean;
  onPick?: (point: { lat: number; lng: number }) => void;
  pickedPoint?: { lat: number; lng: number } | null;
  testID?: string;
}

const COLOR_HEX: Record<string, string> = {
  primary: '#0E7490',
  success: '#047857',
  danger: '#B91C1C',
  warning: '#B45309',
  info: '#1D4ED8',
  neutral: '#475569',
};

export function MapModal({
  visible,
  onClose,
  title = 'Map',
  points,
  paths = [],
  center,
  zoom = 6,
  height = 480,
  pickMode = false,
  onPick,
  pickedPoint,
  testID,
}: MapModalProps) {
  const html = useMemo(
    () => buildLeafletHtml({ points, paths, center, zoom, pickMode, pickedPoint }),
    [points, paths, center, zoom, pickMode, pickedPoint],
  );

  return (
    <Modal visible={visible} onClose={onClose} title={title} variant="sheet" testID={testID}>
      <View style={[styles.mapWrap, { height }]}>
        <WebView
          originWhitelist={['*']}
          source={{ html }}
          style={styles.webview}
          onMessage={(event) => {
            try {
              const data = JSON.parse(event.nativeEvent.data);
              if (data.type === 'pick' && onPick) onPick({ lat: data.lat, lng: data.lng });
            } catch {
              /* ignore non-JSON messages */
            }
          }}
          startInLoadingState
          renderLoading={() => (
            <View style={styles.loading}>
              <ActivityIndicator size="small" color="#0891B2" />
              <Text style={styles.loadingText}>Loading map…</Text>
            </View>
          )}
        />
      </View>
      {pickMode ? (
        <View style={styles.pickBar}>
          <Crosshair size={16} color="#0E7490" />
          <Text style={styles.pickText}>Tap anywhere on the map to set the location</Text>
        </View>
      ) : null}
      {pickMode && pickedPoint ? (
        <View style={styles.pickedChip}>
          <MapPin size={12} color="#0E7490" />
          <Text style={styles.pickedText}>
            {pickedPoint.lat.toFixed(5)}, {pickedPoint.lng.toFixed(5)}
          </Text>
        </View>
      ) : null}
    </Modal>
  );
}

export interface InlineMapProps {
  points: MapPoint[];
  paths?: MapPath[];
  center?: { lat: number; lng: number };
  zoom?: number;
  height?: number;
}

export function InlineMap({ points, paths = [], center, zoom = 6, height = 220 }: InlineMapProps) {
  const html = useMemo(
    () => buildLeafletHtml({ points, paths, center, zoom, pickMode: false }),
    [points, paths, center, zoom],
  );
  return (
    <View style={[styles.mapWrap, { height }]}>
      <WebView
        originWhitelist={['*']}
        source={{ html }}
        style={styles.webview}
        startInLoadingState
        renderLoading={() => (
          <View style={styles.loading}>
            <ActivityIndicator size="small" color="#0891B2" />
          </View>
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  mapWrap: { borderRadius: 12, overflow: 'hidden', backgroundColor: '#E5E7EB' },
  webview: { backgroundColor: '#E5E7EB' },
  loading: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  loadingText: { marginTop: 8, fontSize: 13, color: '#64748B' },
  pickBar: { flexDirection: 'row', alignItems: 'center', marginTop: 12 },
  pickText: { fontSize: 13, color: '#0E7490', marginLeft: 8, flex: 1 },
  pickedChip: {
    flexDirection: 'row',
    alignItems: 'center',
    alignSelf: 'flex-start',
    backgroundColor: '#ECFEFF',
    borderRadius: 9999,
    paddingHorizontal: 10,
    paddingVertical: 4,
    marginTop: 8,
  },
  pickedText: { fontSize: 12, color: '#0E7490', marginLeft: 4, fontWeight: '600' },
});

function buildLeafletHtml({
  points,
  paths,
  center,
  zoom,
  pickMode,
  pickedPoint,
}: {
  points: MapPoint[];
  paths: MapPath[];
  center?: { lat: number; lng: number };
  zoom: number;
  pickMode: boolean;
  pickedPoint?: { lat: number; lng: number } | null;
}) {
  const pointsJson = JSON.stringify(
    points.map((p) => ({ ...p, color: p.color ? COLOR_HEX[p.color] : COLOR_HEX.primary })),
  );
  const pathsJson = JSON.stringify(
    paths.map((p) => ({ ...p, color: p.color ? COLOR_HEX[p.color] : COLOR_HEX.primary })),
  );
  const pickedJson = pickedPoint ? JSON.stringify(pickedPoint) : 'null';
  const centerJson = center ? JSON.stringify(center) : 'null';
  const pickModeStr = pickMode ? 'true' : 'false';

  return `<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>html,body{margin:0;padding:0;height:100%;}#map{width:100%;height:100%;}</style>
</head>
<body>
<div id="map"></div>
<script>
  var points = ${pointsJson};
  var paths = ${pathsJson};
  var center = ${centerJson};
  var picked = ${pickedJson};
  var pickMode = ${pickModeStr};
  var zoom = ${zoom};
  var map = L.map('map');
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19, attribution: '&copy; OpenStreetMap' }).addTo(map);
  var pickedMarker = null;
  function setPicked(ll) {
    if (pickedMarker) { pickedMarker.setLatLng(ll); }
    else {
      pickedMarker = L.marker([ll.lat, ll.lng], { draggable: true }).addTo(map);
      pickedMarker.on('dragend', function () {
        var p = pickedMarker.getLatLng();
        window.ReactNativeWebView.postMessage(JSON.stringify({ type: 'pick', lat: p.lat, lng: p.lng }));
      });
    }
  }
  points.forEach(function (p) {
    var m = L.circleMarker([p.lat, p.lng], { radius: 9, color: p.color, weight: 2, fillColor: p.color, fillOpacity: 0.85 }).addTo(map);
    m.bindPopup('<strong>' + (p.label || '') + '</strong>' + (p.description ? '<br/>' + p.description : ''));
  });
  paths.forEach(function (p) { L.polyline(p.coordinates, { color: p.color, weight: 4, opacity: 0.85 }).addTo(map); });
  if (picked) setPicked(picked);
  if (pickMode) {
    map.on('click', function (e) {
      setPicked({ lat: e.latlng.lat, lng: e.latlng.lng });
      window.ReactNativeWebView.postMessage(JSON.stringify({ type: 'pick', lat: e.latlng.lat, lng: e.latlng.lng }));
    });
  }
  if (center) { map.setView([center.lat, center.lng], zoom); }
  else if (points.length || paths.length) {
    var bounds = L.latLngBounds();
    points.forEach(function (p) { bounds.extend([p.lat, p.lng]); });
    paths.forEach(function (p) { p.coordinates.forEach(function (c) { bounds.extend(c); }); });
    map.fitBounds(bounds, { padding: [24, 24] });
  } else { map.setView([9.082, 8.6753], 6); }
</script>
</body>
</html>`;
}

export { COLOR_HEX as MAP_COLORS };
