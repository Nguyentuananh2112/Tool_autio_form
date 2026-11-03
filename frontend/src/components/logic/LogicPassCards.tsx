import { Check, Loader2 } from 'lucide-react';

import { cn } from '@/lib/cn';
import type { LogicPhase } from '@/hooks/useLogicReview';
import type { LogicMap, LogicReviewResult } from '@/types/logic';

type PassState = 'done' | 'running' | 'waiting';

function PassCard({ step, title, detail, state }: { step: string; title: string; detail: string; state: PassState }) {
  return (
    <div className="flex gap-3 rounded-xl border border-line bg-surface p-4">
      <span aria-hidden className={cn(
        'inline-flex size-8 shrink-0 items-center justify-center rounded-full font-bold',
        state === 'done' && 'bg-ok-soft text-ok',
        state === 'running' && 'bg-accent-soft text-accent',
        state === 'waiting' && 'border border-line text-muted',
      )}>
        {state === 'done' ? <Check className="size-4" /> : state === 'running' ? <Loader2 className="size-4 animate-spin" /> : '·'}
      </span>
      <div className="flex min-w-0 flex-col gap-1">
        <span className="text-xs font-semibold text-muted">{step}</span>
        <span className="text-[15px] font-semibold">{title}</span>
        <span className="text-[13px] text-muted">{detail}</span>
      </div>
    </div>
  );
}

/** Ba lượt soát (artboard 11): đọc câu hỏi → sinh thử → soát chéo từng phản hồi. */
export function LogicPassCards({ phase, logic, result, questionCount }: {
  phase: LogicPhase;
  logic: LogicMap | null;
  result: LogicReviewResult | null;
  questionCount: number;
}) {
  const read: PassState = logic ? 'done' : phase === 'analyzing' || phase === 'loading' ? 'running' : 'waiting';
  const checked: PassState = result && phase !== 'reviewing' ? 'done' : phase === 'reviewing' ? 'running' : 'waiting';
  const groups = logic?.attitude_groups.length ?? 0;
  const items = logic?.attitude_groups.reduce((sum, g) => sum + g.items.length, 0) ?? 0;

  return (
    <section aria-label="Ba lượt soát" className="grid gap-3 [grid-template-columns:repeat(auto-fit,minmax(240px,1fr))]">
      <PassCard
        step="Lượt 1 · Đọc câu hỏi"
        state={read}
        title={logic ? `Đã đọc ${questionCount} câu hỏi` : 'AI đang đọc toàn bộ câu hỏi…'}
        detail={logic
          ? `${groups} nhóm thái độ (${items} câu), ${logic.rules.length} ràng buộc, ${logic.exclusive_options.length} ô loại trừ.`
          : 'Thường mất 10–60 giây; lâu hơn khi Gemini đang quá tải.'}
      />
      <PassCard
        step="Lượt 2 · Sinh thử"
        state={checked}
        title={result ? `Tạo ${result.sample_size} người điền ảo` : 'Tạo người điền ảo'}
        detail="Mỗi người có một mức thái độ chung, mọi câu xoay quanh mức đó."
      />
      <PassCard
        step="Lượt 3 · Soát chéo"
        state={checked}
        title="Đọc lại từng phản hồi"
        detail={result
          ? `${result.repaired} phản hồi được sửa cho khớp, ${result.regenerated} sinh lại. Còn ${result.inconsistent_after} mâu thuẫn.`
          : 'Câu nào mâu thuẫn sẽ được sửa, sửa không được thì sinh lại.'}
      />
    </section>
  );
}
