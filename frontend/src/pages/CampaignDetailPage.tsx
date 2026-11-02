import { useParams } from 'react-router-dom';

import { formsApi } from '@/api/endpoints';
import { CampaignHeader } from '@/components/campaign/CampaignHeader';
import { DistributionChart } from '@/components/campaign/DistributionChart';
import { LiveLog } from '@/components/campaign/LiveLog';
import { LiveProgress } from '@/components/campaign/LiveProgress';
import { PaceChart } from '@/components/campaign/PaceChart';
import { PathStats } from '@/components/campaign/PathStats';
import { ErrorAlert } from '@/components/ui/Alert';
import { Card, CardHeader } from '@/components/ui/Card';
import { Spinner } from '@/components/ui/EmptyState';
import { useAsyncData } from '@/hooks/useAsyncData';
import { useCampaignControls } from '@/hooks/useCampaignControls';
import { useCampaignLive } from '@/hooks/useCampaignLive';

export function CampaignDetailPage() {
  const { campaignId = '' } = useParams();
  const live = useCampaignLive(campaignId);
  const controls = useCampaignControls(campaignId, (updated) => live.campaign.setData(updated));
  const campaign = live.campaign.data;
  const form = useAsyncData(() => (campaign ? formsApi.get(campaign.form_id) : Promise.resolve(null)), [campaign?.form_id]);

  if (live.campaign.loading && !campaign) return <Spinner label="Đang mở chiến dịch…" />;
  if (!campaign) return <ErrorAlert error={live.campaign.error ?? { message: 'Không tìm thấy chiến dịch.' }} />;

  return (
    <>
      <CampaignHeader campaign={campaign} controls={controls} />
      <ErrorAlert error={controls.error} />
      <LiveProgress campaign={campaign} lines={live.lines} nextDelay={live.nextDelay} />
      <div className="flex flex-wrap gap-4">
        <Card className="min-w-0 flex-[3] basis-[440px]" aria-labelledby="dist-title">
          <CardHeader id="dist-title" title="Phân phối đáp án đã gửi" description="So với tỷ lệ mục tiêu bạn đã đặt" />
          <div className="px-5 py-4"><DistributionChart items={live.distribution} /></div>
        </Card>
        <Card className="min-w-0 flex-[2] basis-[320px]" aria-labelledby="pace-title">
          <CardHeader id="pace-title" title="Nhịp gửi" description="Số phản hồi thành công mỗi 5 phút" />
          <div className="flex flex-col gap-4 px-5 py-4">
            <PaceChart lines={live.lines} />
            <div className="flex flex-col gap-2">
              <span className="text-[13px] font-semibold">Đường đi rẽ nhánh thực tế</span>
              <PathStats lines={live.lines} structure={form.data?.structure ?? null} />
            </div>
          </div>
        </Card>
      </div>
      <LiveLog lines={live.lines} socket={live.socket} />
    </>
  );
}
