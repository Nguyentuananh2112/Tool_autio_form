import { useNavigate } from 'react-router-dom';

import { campaignsApi } from '@/api/endpoints';
import { CampaignTable } from '@/components/dashboard/CampaignTable';
import { PageHeader } from '@/components/layout/PageHeader';
import { ErrorAlert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { EmptyState, Spinner } from '@/components/ui/EmptyState';
import { useAsyncData } from '@/hooks/useAsyncData';

export function CampaignListPage() {
  const navigate = useNavigate();
  const campaigns = useAsyncData(campaignsApi.list, []);
  return (
    <>
      <PageHeader title="Chiến dịch" description="Tất cả chiến dịch trên máy này. Bấm tên để xem tiến độ trực tiếp." />
      <ErrorAlert error={campaigns.error} />
      <Card>
        {campaigns.loading && !campaigns.data ? (
          <Spinner />
        ) : (campaigns.data ?? []).length === 0 ? (
          <EmptyState
            title="Chưa có chiến dịch"
            description="Tạo chiến dịch từ màn hình Cấu hình khảo sát sau khi đặt tỷ lệ câu trả lời."
            action={<Button variant="primary" onClick={() => navigate('/forms')}>Đi tới Cấu hình khảo sát</Button>}
          />
        ) : (
          <CampaignTable campaigns={campaigns.data ?? []} />
        )}
      </Card>
    </>
  );
}
