import { useEffect, useRef, useState } from 'react';

import { getRuntimeConfig } from '@/config/runtime';
import type { CampaignEvent } from '@/types/events';

export type SocketStatus = 'connecting' | 'open' | 'closed';

const RECONNECT_DELAY_MS = 2000;

/** Nhận sự kiện real-time của một chiến dịch; tự kết nối lại khi mất kết nối. */
export function useCampaignSocket(campaignId: string | undefined, onEvent: (event: CampaignEvent) => void): SocketStatus {
  const [status, setStatus] = useState<SocketStatus>('connecting');
  const handler = useRef(onEvent);
  handler.current = onEvent;

  useEffect(() => {
    if (!campaignId) return undefined;
    const { wsBase, token } = getRuntimeConfig();
    const url = `${wsBase}/ws/campaigns/${campaignId}${token ? `?token=${encodeURIComponent(token)}` : ''}`;
    let socket: WebSocket | null = null;
    let retry: ReturnType<typeof setTimeout> | null = null;
    let disposed = false;

    const connect = () => {
      setStatus('connecting');
      socket = new WebSocket(url);
      socket.onopen = () => setStatus('open');
      socket.onmessage = (message) => {
        try {
          handler.current(JSON.parse(String(message.data)) as CampaignEvent);
        } catch {
          // bỏ qua gói tin hỏng
        }
      };
      socket.onclose = () => {
        setStatus('closed');
        if (!disposed) retry = setTimeout(connect, RECONNECT_DELAY_MS);
      };
    };
    connect();

    return () => {
      disposed = true;
      if (retry) clearTimeout(retry);
      socket?.close();
    };
  }, [campaignId]);

  return status;
}
