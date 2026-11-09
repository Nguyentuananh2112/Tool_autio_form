// Khớp với backend/app/schemas/campaign_schema.py, campaign_api.py, event_schema.py

export type RuleStrategy = 'AUTO' | 'FIXED' | 'SKIP';
export type ScheduleMode = 'BURST' | 'SCHEDULED';
export type DataSource = 'PROBABILITY' | 'EXCEL';
export type CampaignStatus = 'IDLE' | 'RUNNING' | 'PAUSED' | 'COMPLETED' | 'FAILED';

export interface QuestionRuleConfig {
  entry_id: string;
  question_type: number;
  strategy?: RuleStrategy;
  weights?: Record<string, number>;
  min_checked?: number;
  max_checked?: number | null;
  other_text_pool?: string[];
  text_pool?: string[];
  fixed_value?: string | string[] | null;
  answer_rate?: number;
  date_start?: string | null;
  date_end?: string | null;
  time_start?: string | null;
  time_end?: string | null;
  ai_context?: string | null;
  ai_persona?: string | null;
}

export interface SpssGroupConfig {
  group_id: string;
  name: string;
  mean: number;
  std: number;
  r: number | null;
  alpha_target: number | null;
  entries: string[];
  reversed_entries: string[];
  calibrate: boolean;
}

export interface ScheduleConfig {
  mode: ScheduleMode;
  duration_minutes: number | null;
  concurrency: number;
}

export interface CampaignCreate {
  form_id: string;
  name: string;
  data_source: DataSource;
  total_target: number | null;
  schedule: ScheduleConfig;
  rules: QuestionRuleConfig[];
  spss_groups: SpssGroupConfig[];
  excel_records: Record<string, unknown>[] | null;
  proxy: string | null;
  use_playwright_fallback: boolean;
}

export interface CampaignRead {
  id: string;
  form_id: string;
  form_title: string;
  name: string;
  data_source: DataSource;
  status: CampaignStatus;
  total_target: number;
  completed_count: number;
  failed_count: number;
  schedule: ScheduleConfig;
  proxy: string | null;
  use_playwright_fallback: boolean;
  created_at: string;
  is_active: boolean;
  pause_reason: string | null;
  status_reason: string | null;
  /** App tự tạm dừng (Google giới hạn / từ chối liên tiếp) — khác người dùng bấm Tạm dừng */
  auto_paused: boolean;
}

export type FailureCategory = 'REJECTED' | 'RATE_LIMITED' | 'NETWORK' | 'BROWSER' | 'FORM_CLOSED' | 'OTHER';

export interface FailureReason {
  category: FailureCategory;
  title: string;
  fix: string;
  count: number;
  detail: string | null;
}

/** Thông báo kết thúc chiến dịch (màn 13) — khớp backend CampaignSummary. */
export interface CampaignSummary {
  campaign_id: string;
  name: string;
  form_id: string;
  form_title: string;
  status: CampaignStatus;
  status_reason: string | null;
  auto_paused: boolean;
  total_target: number;
  completed_count: number;
  failed_count: number;
  remaining: number;
  started_at: string | null;
  finished_at: string | null;
  duration_seconds: number;
  reasons: FailureReason[];
}

export interface SpssItemPreview {
  entry_id: string;
  title: string;
  is_reversed: boolean;
  mean: number;
  std: number;
  distribution: Record<string, number>;
}

export interface SpssGroupPreview {
  group_id: string;
  name: string;
  n_samples: number;
  n_items: number;
  cronbach_alpha: number | null;
  alpha_target: number | null;
  mean_inter_item_r: number | null;
  target_r: number | null;
  latent_r: number;
  target_mean: number;
  achieved_mean: number;
  target_std: number;
  achieved_std: number;
  items: SpssItemPreview[];
  warnings: string[];
}

export interface SpssPreviewResponse {
  groups: SpssGroupPreview[];
  warnings: string[];
}

export interface TrialSubmitResponse {
  success: boolean;
  outcome: string;
  status_code: number;
  engine_used: string;
  error: string | null;
  page_history: string;
  payload_sent: Record<string, string | string[]>;
}

export interface SubmissionLogRead {
  id: number;
  sequence_number: number;
  engine_used: string;
  status_code: number;
  is_success: boolean;
  error_detail: string | null;
  executed_at: string;
  page_history: string | null;
}

export interface OptionDistribution {
  label: string;
  sent_count: number;
  sent_pct: number;
  target_pct: number | null;
}

export interface QuestionDistribution {
  entry_id: string;
  title: string;
  answered: number;
  options: OptionDistribution[];
}
