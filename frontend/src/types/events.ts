// Sự kiện WebSocket /ws/campaigns/{id} — khớp backend/app/schemas/event_schema.py
import type { CampaignRead } from './campaign';

export interface SnapshotEvent {
  event: 'SNAPSHOT';
  campaign: CampaignRead;
}

export interface SubmissionUpdateEvent {
  event: 'SUBMISSION_UPDATE';
  campaign_id: string;
  sequence_number: number;
  completed_count: number;
  failed_count: number;
  engine_used: string;
  status_code: number;
  is_success: boolean;
  page_history: string;
  error_detail: string | null;
  next_delay_seconds: number | null;
  timestamp: string;
}

export interface StatusChangeEvent {
  event: 'STATUS_CHANGE';
  campaign_id: string;
  status: CampaignRead['status'];
  reason: string | null;
  timestamp: string;
}

export interface RateLimitedEvent {
  event: 'RATE_LIMITED';
  campaign_id: string;
  sequence_number: number;
  status_code: number;
  wait_seconds: number;
  consecutive_blocks: number;
  will_pause: boolean;
  timestamp: string;
}

export interface PingEvent {
  event: 'PING';
}

export type CampaignEvent = SnapshotEvent | SubmissionUpdateEvent | StatusChangeEvent | RateLimitedEvent | PingEvent;
