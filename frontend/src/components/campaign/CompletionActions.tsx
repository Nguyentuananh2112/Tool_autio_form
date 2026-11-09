import { ErrorAlert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { useCompletionActions } from '@/hooks/useCompletionActions';
import { ACTION_LABELS, type CompletionAction } from '@/lib/completion';
import type { CampaignSummary } from '@/types/campaign';

/** Hàng nút của thông báo kết thúc: nút cuối là nút chính. */
export function CompletionActions({ summary, actions, onDone }: {
  summary: CampaignSummary;
  actions: CompletionAction[];
  onDone: () => void;
}) {
  const { busy, error, run } = useCompletionActions(summary, onDone);
  return (
    <div className="flex w-full flex-col gap-2">
      <ErrorAlert error={error} />
      <div className="flex flex-wrap justify-end gap-2">
        {actions.map((action, index) => (
          <Button
            key={action}
            variant={index === actions.length - 1 ? 'primary' : 'secondary'}
            loading={busy === action}
            disabled={busy !== null && busy !== action}
            onClick={() => void run(action)}
          >
            {ACTION_LABELS[action](summary)}
          </Button>
        ))}
      </div>
    </div>
  );
}
