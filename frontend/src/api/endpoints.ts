import type {
  CampaignCreate,
  CampaignRead,
  QuestionDistribution,
  QuestionRuleConfig,
  SpssGroupConfig,
  SpssPreviewResponse,
  SubmissionLogRead,
  TrialSubmitResponse,
} from '@/types/campaign';
import type { ColumnMapping, ExcelConvertResponse, ExcelPreview } from '@/types/excel';
import type { FormDetail, FormSummary } from '@/types/form';
import type { LogicMap, LogicReviewResult } from '@/types/logic';
import type { AppSettingsRead, BrowserStatus, GeneratePoolRequest } from '@/types/settings';

import { api, request } from './client';

export const formsApi = {
  parse: (url: string) => request(() => api.post<FormDetail>('/forms/parse', { url })),
  openDemo: () => request(() => api.post<FormDetail>('/forms/demo')),
  list: () => request(() => api.get<FormSummary[]>('/forms')),
  get: (id: string) => request(() => api.get<FormDetail>(`/forms/${id}`)),
  remove: (id: string) => request(() => api.delete<void>(`/forms/${id}`)),
};

export interface LogicReviewPayload {
  rules: QuestionRuleConfig[];
  spss_groups: SpssGroupConfig[];
  logic?: LogicMap | null;
  sample_size?: number;
}

/** Soát logic (màn 11). Đọc câu hỏi bằng AI có thể mất 1–3 phút khi Gemini quá tải. */
export const logicApi = {
  get: (formId: string) => request(() => api.get<LogicMap | null>(`/forms/${formId}/logic`)),
  analyze: (formId: string) => request(() => api.post<LogicMap>(`/forms/${formId}/logic/analyze`, undefined, { timeout: 300_000 })),
  save: (formId: string, logic: LogicMap) => request(() => api.put<LogicMap>(`/forms/${formId}/logic`, logic)),
  review: (formId: string, payload: LogicReviewPayload) =>
    request(() => api.post<LogicReviewResult>(`/forms/${formId}/logic/review`, payload, { timeout: 300_000 })),
};

export const excelApi = {
  preview: (formId: string, file: File) => {
    const body = new FormData();
    body.append('file', file);
    return request(() => api.post<ExcelPreview>(`/forms/${formId}/parse-excel`, body));
  },
  convert: (formId: string, file: File, mappings: ColumnMapping[]) => {
    const body = new FormData();
    body.append('file', file);
    body.append('mappings', JSON.stringify(mappings));
    return request(() => api.post<ExcelConvertResponse>(`/forms/${formId}/excel-convert`, body));
  },
};

export const aiApi = {
  generatePool: (payload: GeneratePoolRequest) =>
    request(() => api.post<{ answers: string[] }>('/ai/generate-pool', payload, { timeout: 180_000 })),
};

export const settingsApi = {
  get: () => request(() => api.get<AppSettingsRead>('/settings')),
  saveGeminiKey: (apiKey: string) => request(() => api.put<void>('/settings/gemini-key', { api_key: apiKey })),
  deleteGeminiKey: () => request(() => api.delete<void>('/settings/gemini-key')),
  browserStatus: () => request(() => api.get<BrowserStatus>('/system/browser', { timeout: 90_000 })),
  installBrowser: () => request(() => api.post<BrowserStatus>('/system/browser/install')),
};

export interface PreviewPayload {
  form_id: string;
  rules: QuestionRuleConfig[];
  spss_groups: SpssGroupConfig[];
  sample_size?: number;
}

export const campaignsApi = {
  list: () => request(() => api.get<CampaignRead[]>('/campaigns')),
  get: (id: string) => request(() => api.get<CampaignRead>(`/campaigns/${id}`)),
  create: (payload: CampaignCreate) => request(() => api.post<CampaignRead>('/campaigns', payload)),
  remove: (id: string) => request(() => api.delete<void>(`/campaigns/${id}`)),
  previewSpss: (payload: PreviewPayload) => request(() => api.post<SpssPreviewResponse>('/campaigns/preview-spss', payload)),
  trialSubmit: (payload: Omit<PreviewPayload, 'sample_size'> & { proxy: string | null; dry_run: boolean }) =>
    request(() => api.post<TrialSubmitResponse>('/campaigns/trial-submit', payload)),
  start: (id: string) => request(() => api.post<CampaignRead>(`/campaigns/${id}/start`)),
  pause: (id: string) => request(() => api.post<CampaignRead>(`/campaigns/${id}/pause`)),
  resume: (id: string) => request(() => api.post<CampaignRead>(`/campaigns/${id}/resume`)),
  stop: (id: string) => request(() => api.post<CampaignRead>(`/campaigns/${id}/stop`)),
  logs: (id: string, limit = 100) => request(() => api.get<SubmissionLogRead[]>(`/campaigns/${id}/logs`, { params: { limit } })),
  distribution: (id: string) => request(() => api.get<QuestionDistribution[]>(`/campaigns/${id}/distribution`)),
  exportUrl: (id: string, format: 'xlsx' | 'csv') => `/campaigns/${id}/export?format=${format}`,
  exportFile: (id: string, format: 'xlsx' | 'csv') =>
    request(() => api.get<Blob>(`/campaigns/${id}/export`, { params: { format }, responseType: 'blob' })),
};
