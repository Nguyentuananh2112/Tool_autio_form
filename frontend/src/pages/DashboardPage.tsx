import { Plus } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

import { campaignsApi, formsApi } from '@/api/endpoints';
import { CampaignTable } from '@/components/dashboard/CampaignTable';
import { KpiGrid, type Kpi } from '@/components/dashboard/KpiGrid';
import { QuickParseCard } from '@/components/dashboard/QuickParseCard';
import { RecentForms } from '@/components/dashboard/RecentForms';
import { PageHeader } from '@/components/layout/PageHeader';
import { ErrorAlert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { Card, CardHeader } from '@/components/ui/Card';
import { EmptyState, Spinner } from '@/components/ui/EmptyState';
import { UpdateBanner } from '@/components/update/UpdateBanner';
import { useAsyncData } from '@/hooks/useAsyncData';
import { formatNumber, formatPercent } from '@/lib/format';
import type { CampaignRead } from '@/types/campaign';

function buildKpis(campaigns: CampaignRead[], formCount: number): Kpi[] {
  const completed = campaigns.reduce((sum, c) => sum + c.completed_count, 0);
  const failed = campaigns.reduce((sum, c) => sum + c.failed_count, 0);
  const attempts = completed + failed;
  return [
    { label: 'Đang chạy', value: String(campaigns.filter((c) => c.is_active).length), hint: 'chiến dịch' },
    { label: 'Đã gửi thành công', value: formatNumber(completed), hint: 'phản hồi trên máy này' },
    { label: 'Tỷ lệ thành công', value: attempts ? formatPercent((completed * 100) / attempts) : '—', hint: 'trên tất cả chiến dịch' },
    { label: 'Form đã phân tích', value: String(formCount), hint: 'lưu trên máy này' },
  ];
}

export function DashboardPage() {
  const navigate = useNavigate();
  const campaigns = useAsyncData(campaignsApi.list, []);
  const forms = useAsyncData(formsApi.list, []);
  const list = campaigns.data ?? [];

  return (
    <>
      <PageHeader
        title="Tổng quan"
        description="Tình hình các chiến dịch điền khảo sát trên máy này."
        actions={<Button variant="primary" onClick={() => navigate('/forms')}><Plus aria-hidden className="size-4" />Tạo chiến dịch mới</Button>}
      />
      <UpdateBanner />
      <ErrorAlert error={campaigns.error ?? forms.error} />
      <KpiGrid items={buildKpis(list, forms.data?.length ?? 0)} />
      <div className="flex flex-wrap gap-4">
        <div className="min-w-[320px] flex-[3]"><QuickParseCard /></div>
        <div className="min-w-[280px] flex-[2]"><RecentForms forms={forms.data ?? []} /></div>
      </div>
      <Card aria-labelledby="recent-campaigns">
        <CardHeader id="recent-campaigns" title="Chiến dịch gần đây" />
        {campaigns.loading && !campaigns.data ? (
          <Spinner />
        ) : list.length === 0 ? (
          <EmptyState title="Chưa có chiến dịch nào" description="Phân tích một form, đặt tỷ lệ câu trả lời rồi bấm Bắt đầu chạy. Chiến dịch sẽ hiện ở đây." />
        ) : (
          <CampaignTable campaigns={list.slice(0, 8)} />
        )}
      </Card>
    </>
  );
}
