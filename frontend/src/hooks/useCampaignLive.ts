import { useCallback, useEffect, useRef, useState } from 'react';

import { campaignsApi } from '@/api/endpoints';
import type { CampaignRead, QuestionDistribution, SubmissionLogRead } from '@/types/campaign';
import type { CampaignEvent } from '@/types/events';

import { useAsyncData } from './useAsyncData';
import { type SocketStatus, useCampaignSocket } from './useCampaignSocket';

export interface LiveLogLine {
  key: string;
  time: string;
  sequence: number;
  engine: string;
  statusCode: number;
  ok: boolean;
  note: string;
  pageHistory: string | null;
}

const MAX_LINES = 300;
const DISTRIBUTION_REFRESH_MS = 8000;
const REFRESH_EVERY_UPDATES = 5;

function fromLog(log: SubmissionLogRead): LiveLogLine {
  return {
    key: `log-${log.id}`,
    time: log.executed_at,
    sequence: log.sequence_number,
    engine: log.engine_used,
    statusCode: log.status_code,
    ok: log.is_success,
    note: log.error_detail ?? 'đã gửi',
    pageHistory: log.page_history,
  };
}

/** Trạng thái chiến dịch + nhật ký + phân phối, cập nhật trực tiếp qua WebSocket. */
export function useCampaignLive(campaignId: string) {
  const campaign = useAsyncData(() => campaignsApi.get(campaignId), [campaignId]);
  const [lines, setLines] = useState<LiveLogLine[]>([]);
  const [nextDelay, setNextDelay] = useState<number | null>(null);
  const [distribution, setDistribution] = useState<QuestionDistribution[]>([]);
  const counter = useRef(0);

  const refreshDistribution = useCallback(async () => {
    try {
      setDistribution(await campaignsApi.distribution(campaignId));
    } catch {
      // biểu đồ không quan trọng bằng tiến độ: bỏ qua lỗi tạm thời
    }
  }, [campaignId]);

  useEffect(() => {
    void campaignsApi.logs(campaignId, 300).then((logs) => setLines(logs.map(fromLog))).catch(() => undefined);
    void refreshDistribution();
    const timer = setInterval(() => void refreshDistribution(), DISTRIBUTION_REFRESH_MS);
    return () => clearInterval(timer);
  }, [campaignId, refreshDistribution]);

  const patchCampaign = (patch: Partial<CampaignRead>) => campaign.setData((prev) => (prev ? { ...prev, ...patch } : prev));

  const onEvent = (event: CampaignEvent) => {
    if (event.event === 'SNAPSHOT') campaign.setData(event.campaign);
    if (event.event === 'STATUS_CHANGE') {
      patchCampaign({ status: event.status, pause_reason: event.reason, is_active: event.status === 'RUNNING' || event.status === 'PAUSED' });
      void refreshDistribution();
    }
    if (event.event === 'SUBMISSION_UPDATE') {
      patchCampaign({ completed_count: event.completed_count, failed_count: event.failed_count });
      setNextDelay(event.next_delay_seconds);
      counter.current += 1;
      if (counter.current % REFRESH_EVERY_UPDATES === 0) void refreshDistribution();
      const line: LiveLogLine = {
        key: `ev-${event.sequence_number}-${counter.current}`,
        time: event.timestamp,
        sequence: event.sequence_number,
        engine: event.engine_used,
        statusCode: event.status_code,
        ok: event.is_success,
        note: event.error_detail ?? (event.next_delay_seconds !== null ? `nghỉ tiếp ${event.next_delay_seconds} giây` : 'đã gửi'),
        pageHistory: event.page_history,
      };
      setLines((prev) => [line, ...prev].slice(0, MAX_LINES));
    }
    if (event.event === 'RATE_LIMITED') {
      counter.current += 1;
      setLines((prev) => [{
        key: `rl-${event.sequence_number}-${counter.current}`,
        time: event.timestamp,
        sequence: event.sequence_number,
        engine: 'HTTPX',
        statusCode: event.status_code,
        ok: false,
        note: event.will_pause
          ? 'Google giới hạn liên tiếp → chiến dịch tự tạm dừng'
          : `Google giới hạn số lần gửi → giãn nhịp, chờ ${Math.round(event.wait_seconds)} giây rồi gửi lại`,
        pageHistory: null,
      }, ...prev].slice(0, MAX_LINES));
    }
  };

  const socket: SocketStatus = useCampaignSocket(campaignId, onEvent);
  return { campaign, lines, nextDelay, distribution, socket, reload: campaign.reload };
}
