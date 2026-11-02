import { useState } from 'react';

import { Button } from '@/components/ui/Button';
import { questionCode } from '@/lib/questions';
import { type CandidateGroup, itemLabel } from '@/lib/spssCandidates';

/** Chọn biến quan sát cho nhóm; đánh dấu biến đảo chiều. Chỉ các câu cùng thang đo mới chọn chung được. */
export function ItemPicker({ candidates, selected, reversed, onToggle, onToggleReversed, lockedScale }: {
  candidates: CandidateGroup[];
  selected: string[];
  reversed: string[];
  onToggle: (entryId: string) => void;
  onToggleReversed: (entryId: string) => void;
  lockedScale: string | null;
}) {
  const [filter, setFilter] = useState(candidates[0]?.key ?? '');
  const group = candidates.find((c) => c.key === filter) ?? candidates[0];

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-col gap-2">
        <span className="text-[13px] font-medium text-muted">Lọc theo câu hỏi</span>
        <div className="flex flex-wrap gap-1.5">
          {candidates.map((c) => (
            <Button key={c.key} size="sm" variant={c.key === group?.key ? 'primary' : 'secondary'} aria-pressed={c.key === group?.key} onClick={() => setFilter(c.key)}>
              {c.label} · {c.questions.length}
            </Button>
          ))}
        </div>
      </div>
      <div className="overflow-hidden rounded-[10px] border border-line">
        <div className="grid grid-cols-[44px_64px_minmax(0,1fr)_88px] gap-2 border-b border-line px-3 py-2.5 text-xs font-semibold uppercase tracking-wide text-muted">
          <span>Chọn</span><span>Mã</span><span>Biến quan sát</span><span>Đảo chiều</span>
        </div>
        {group?.questions.map((q, index) => {
          const disabled = lockedScale !== null && lockedScale !== group.scaleKey && !selected.includes(q.entry_id);
          const checked = selected.includes(q.entry_id);
          return (
            <div key={q.entry_id} className="grid min-h-11 grid-cols-[44px_64px_minmax(0,1fr)_88px] items-center gap-2 border-t border-line px-3 first:border-t-0">
              <input type="checkbox" aria-label={`Chọn ${itemLabel(q)}`} checked={checked} disabled={disabled} onChange={() => onToggle(q.entry_id)} className="size-[18px]" />
              <span className="font-mono text-[13px] font-medium">{questionCode(q) ? `${questionCode(q)}.${index + 1}` : index + 1}</span>
              <span className="text-sm">{itemLabel(q)}</span>
              <input type="checkbox" aria-label={`Đảo chiều ${itemLabel(q)}`} checked={reversed.includes(q.entry_id)} disabled={!checked} onChange={() => onToggleReversed(q.entry_id)} className="size-[18px]" />
            </div>
          );
        })}
      </div>
      <span className="text-[13px] text-muted">Đã chọn {selected.length} biến. Nhóm cần ít nhất 2 biến có cùng thang đo.</span>
    </div>
  );
}
