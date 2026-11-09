import { Dialog } from '@/components/ui/Dialog';
import { completionView } from '@/lib/completion';
import type { CampaignSummary } from '@/types/campaign';

import { CompletionActions } from './CompletionActions';
import { CompletionContent, CompletionIcon } from './CompletionContent';

/** Hộp thoại kết thúc chiến dịch (màn 13): hiện ở mọi màn hình ngay khi chiến dịch xong / tự tạm dừng. */
export function CompletionDialog({ summary, onClose }: { summary: CampaignSummary; onClose: () => void }) {
  const view = completionView(summary);
  return (
    <Dialog
      open
      onClose={onClose}
      title={(
        <span className="flex items-center gap-3.5">
          <CompletionIcon kind={view.kind} />
          {view.title}
        </span>
      )}
      description={view.subtitle}
      footer={<CompletionActions summary={summary} actions={view.actions} onDone={onClose} />}
    >
      <CompletionContent summary={summary} />
    </Dialog>
  );
}
