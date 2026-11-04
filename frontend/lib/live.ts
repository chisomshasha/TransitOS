/**
 * Live trip events — Server-Sent Events with a polling fallback.
 *
 * The backend exposes `GET /events/trips` as a Server-Sent Events
 * stream. React Native's fetch cannot read a response body
 * incrementally, so the stream is consumed with
 * `XMLHttpRequest` and its `onprogress` event, which fires as bytes
 * arrive.
 *
 * If the stream cannot be established (a proxy that buffers, a device
 * that loses connectivity, a server without the SSE route) the hook
 * falls back to polling `GET /trips` on an interval, so the live board
 * degrades to "refreshed every N seconds" instead of going blank.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { api, resolveBaseURL } from '@/lib/api';
import { useAuthStore } from '@/stores/authStore';

export interface TripEvent {
  type: 'trip.created' | 'trip.updated' | 'trip.removed' | 'ping';
  data: {
    trip_id?: string;
    status?: string;
    previous_status?: string;
    branch_id?: string;
    route_id?: string;
    updated_at?: string;
  };
}

export type LiveConnection = 'connecting' | 'live' | 'polling' | 'offline';

/**
 * Subscribe to trip events.
 *
 * @param onEvent called for every event that arrives
 * @param enabled set to false to tear the connection down
 */
export function useTripEvents(
  onEvent: (event: TripEvent) => void,
  enabled = true
): { connection: LiveConnection } {
  const [connection, setConnection] = useState<LiveConnection>('connecting');
  const handlerRef = useRef(onEvent);
  handlerRef.current = onEvent;

  const connect = useCallback(() => {
    if (!enabled) return;

    let xhr: XMLHttpRequest | null = null;
    let cancelled = false;
    let retryTimer: ReturnType<typeof setTimeout> | null = null;
    // Bytes already consumed from the current response. `pending` holds
    // a frame that has not been terminated by a blank line yet.
    let consumed = 0;
    let pending = '';

    const parse = (raw: string) => {
      // SSE frames are separated by a blank line.
      for (const frame of raw.split('\n\n')) {
        const trimmed = frame.trim();
        if (!trimmed) continue;
        let type = 'message';
        let data = '';
        for (const line of trimmed.split('\n')) {
          if (line.startsWith('event:')) type = line.slice(6).trim();
          else if (line.startsWith('data:')) data += line.slice(5).trim();
        }
        if (!data) continue;
        try {
          handlerRef.current({ type: type as TripEvent['type'], data: JSON.parse(data) });
        } catch {
          // A malformed frame must not kill the stream.
        }
      }
    };

    const start = () => {
      if (cancelled) return;
      setConnection('connecting');
      consumed = 0;
      pending = '';

      try {
        xhr = new XMLHttpRequest();
        xhr.open('GET', `${resolveBaseURL()}/events/trips`);
        // Read the token at connect time so a sign-in that happens
        // after the screen mounted is picked up on the next connect.
        const currentToken = useAuthStore.getState().accessToken ?? '';
        if (currentToken) xhr.setRequestHeader('Authorization', `Bearer ${currentToken}`);
        xhr.setRequestHeader('Accept', 'text/event-stream');

        xhr.onreadystatechange = () => {
          if (cancelled) return;
          if (xhr?.readyState === 2) {
            // Headers are in — the stream is open.
            setConnection('live');
          }
          if (xhr?.readyState === 3) {
            // Body chunks are arriving.
            const chunk = xhr.responseText ?? '';
            if (chunk.length > consumed) {
              const fresh = chunk.slice(consumed);
              consumed = chunk.length;
              // Only complete frames are dispatched: a frame that has
              // not been terminated by a blank line stays in `pending`
              // until the rest of it arrives.
              pending += fresh;
              const parts = pending.split('\n\n');
              pending = parts.pop() ?? '';
              if (parts.length) parse(parts.join('\n\n'));
            }
          }
          if (xhr?.readyState === 4) {
            // The stream ended. Reconnect shortly.
            if (!cancelled) {
              setConnection('polling');
              retryTimer = setTimeout(start, 5000);
            }
          }
        };

        xhr.onerror = () => {
          if (cancelled) return;
          // The stream could not be established — the caller falls back
          // to polling.
          setConnection('polling');
        };

        xhr.send();
      } catch {
        setConnection('polling');
      }
    };

    start();

    return () => {
      cancelled = true;
      if (retryTimer) clearTimeout(retryTimer);
      try {
        xhr?.abort();
      } catch {
        // Already closed.
      }
    };
  }, [enabled]);

  useEffect(() => connect(), [connect]);

  return { connection };
}

/**
 * Poll `GET /trips` on an interval — the fallback when SSE is not
 * available.
 */
export function useTripPolling(
  onTrips: (trips: unknown[]) => void,
  intervalMs = 15_000,
  enabled = true
): void {
  const handlerRef = useRef(onTrips);
  handlerRef.current = onTrips;

  useEffect(() => {
    if (!enabled) return;
    let cancelled = false;

    const tick = async () => {
      try {
        const resp = await api.get<{ items?: unknown[] }>('/trips', {
          params: { page: 1, page_size: 100 },
        });
        if (!cancelled) handlerRef.current(resp.data?.items ?? []);
      } catch {
        // Offline — try again on the next tick.
      }
    };

    void tick();
    const id = setInterval(tick, intervalMs);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [intervalMs, enabled]);
}
