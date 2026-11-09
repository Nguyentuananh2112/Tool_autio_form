import { useEffect, useRef } from 'react';

import { campaignsApi } from '@/api/endpoints';
import { justEnded, type Snapshot, snapshotOf } from '@/lib/completion';
import type { CampaignSummary } from '@/types/campaign';

export const FAST_POLL_MS = 3_000; // đang có chiến dịch chạy
export const IDLE_POLL_MS = 8_000;

/**
 * Theo dõi mọi chiến dịch ở nền (ở bất kỳ màn hình nào) và báo các chiến dịch VỪA kết thúc kèm tóm tắt
 * để hiện thông báo (màn 13). Chiến dịch chạy trong backend nên không cần mở trang của nó.
 */
export function useCampaignWatcher(onEnded: (summary: CampaignSummary) => void): void {
  const callback = useRef(onEnded);
  callback.current = onEnded;

  useEffect(() => {
    let previous: Map<string, Snapshot> | null = null;
    let stopped = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const since = Date.now();

    const tick = async () => {
      let delay = IDLE_POLL_MS;
      try {
        const campaigns = await campaignsApi.list();
        if (stopped) return;
        for (const campaign of justEnded(previous, campaigns, since)) {
          try {
            callback.current(await campaignsApi.summary(campaign.id));
          } catch {
            // Không lấy được tóm tắt lần này; trang chiến dịch vẫn hiện kết quả
          }
        }
        previous = new Map(campaigns.map((c) => [c.id, snapshotOf(c)]));
        if (campaigns.some((c) => c.is_active)) delay = FAST_POLL_MS;
      } catch {
        // Backend đang khởi động / tạm mất kết nối: lần sau thử lại
      }
      if (!stopped) timer = setTimeout(() => void tick(), delay);
    };

    void tick();
    return () => {
      stopped = true;
      if (timer) clearTimeout(timer);
    };
  }, []);
}
