import { campaignsApi, formsApi } from '@/api/endpoints';
import { PRACTICE_CAMPAIGN_NAME, practiceCampaign } from '@/lib/demoDefaults';

import type { TourScreen } from './tourSteps';

/** Đường dẫn cho từng màn hình của tour. Tour chạy trên form mẫu + một chiến dịch tập dùng (chỉ mô phỏng). */
export async function resolveTourRoute(screen: TourScreen): Promise<string> {
  if (screen === 'dashboard') return '/';
  const demo = await formsApi.openDemo();
  if (screen === 'workspace') return `/forms/${demo.id}?tab=weights`;

  const existing = (await campaignsApi.list()).find((c) => c.form_id === demo.id && c.name === PRACTICE_CAMPAIGN_NAME);
  if (existing) {
    if (!existing.is_active && existing.status !== 'COMPLETED') await campaignsApi.resume(existing.id);
    return `/campaigns/${existing.id}`;
  }
  const created = await campaignsApi.create(practiceCampaign(demo.id));
  await campaignsApi.start(created.id);
  return `/campaigns/${created.id}`;
}
