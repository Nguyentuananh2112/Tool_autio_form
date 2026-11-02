import type { FormConfig } from '@/store/formConfigStore';
import type { CampaignCreate } from '@/types/campaign';

export function defaultCampaignName(formTitle: string): string {
  const stamp = new Date().toLocaleString('vi-VN', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
  return `${formTitle.slice(0, 60)} — ${stamp}`;
}

/** Bản nháp cấu hình trên giao diện → body POST /campaigns. */
export function buildCampaignPayload(formId: string, formTitle: string, config: FormConfig): CampaignCreate {
  const excel = config.dataSource === 'EXCEL' ? config.excel : null;
  return {
    form_id: formId,
    name: config.name.trim() || defaultCampaignName(formTitle),
    data_source: config.dataSource,
    total_target: excel ? Math.min(config.target || excel.validRows, excel.validRows) : config.target,
    schedule: config.schedule,
    rules: Object.values(config.rules),
    spss_groups: config.groups,
    excel_records: excel?.records ?? null,
    proxy: config.proxy.trim() || null,
    use_playwright_fallback: config.useFallback,
  };
}
