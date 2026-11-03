import { campaignsApi, formsApi, logicApi } from '@/api/endpoints';
import { DEMO_RULES, PRACTICE_CAMPAIGN_NAME, practiceCampaign } from '@/lib/demoDefaults';
import { useFormConfigStore } from '@/store/formConfigStore';

import type { TourScreen } from './tourSteps';

/** Form mẫu trong tour cần đủ cấu hình tối thiểu để màn Soát logic chạy được (câu tự luận bắt buộc). */
function ensureDemoConfig(formId: string): void {
  const store = useFormConfigStore.getState();
  const rules = store.configs[formId]?.rules ?? {};
  for (const rule of DEMO_RULES) {
    if (!rules[rule.entry_id]) store.updateRule(formId, rule);
  }
}

/** Chiến dịch tập dùng cũng phải qua Soát logic (quy tắc 6): xác nhận bản đồ dựng sẵn của form mẫu. */
async function ensureDemoLogicConfirmed(formId: string): Promise<void> {
  const logic = (await logicApi.get(formId)) ?? (await logicApi.analyze(formId));
  if (!logic.confirmed) await logicApi.save(formId, { ...logic, confirmed: true });
}

/** Đường dẫn cho từng màn hình của tour. Tour chạy trên form mẫu + một chiến dịch tập dùng (chỉ mô phỏng). */
export async function resolveTourRoute(screen: TourScreen): Promise<string> {
  if (screen === 'dashboard') return '/';
  const demo = await formsApi.openDemo();
  ensureDemoConfig(demo.id);
  if (screen === 'workspace') return `/forms/${demo.id}?tab=weights`;
  if (screen === 'logic') return `/forms/${demo.id}/logic`;

  const existing = (await campaignsApi.list()).find((c) => c.form_id === demo.id && c.name === PRACTICE_CAMPAIGN_NAME);
  if (existing) {
    if (!existing.is_active && existing.status !== 'COMPLETED') await campaignsApi.resume(existing.id);
    return `/campaigns/${existing.id}`;
  }
  await ensureDemoLogicConfirmed(demo.id);
  const created = await campaignsApi.create(practiceCampaign(demo.id));
  await campaignsApi.start(created.id);
  return `/campaigns/${created.id}`;
}
