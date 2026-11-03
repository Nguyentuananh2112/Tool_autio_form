import { ArrowDownUp, X } from 'lucide-react';
import { useId, useState } from 'react';

import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Select } from '@/components/ui/Field';
import { addGroup, addToGroup, attitudeCandidates, removeFromGroup, toggleDirection } from '@/lib/logicDraft';
import { questionFullTitle, questionShortLabel } from '@/lib/logicLabels';
import type { ParsedQuestion } from '@/types/form';
import type { AttitudeGroup, AttitudeItem, LogicMap } from '@/types/logic';

function AttitudeChip({ item, question, index, onFlip, onRemove }: {
  item: AttitudeItem;
  question: ParsedQuestion | undefined;
  index: number;
  onFlip: () => void;
  onRemove: () => void;
}) {
  const label = questionShortLabel(question, index);
  return (
    <span title={questionFullTitle(question)} className="inline-flex min-h-9 items-center gap-1.5 rounded-lg border border-line bg-surface pl-2.5 text-[13px]">
      <b className="font-mono text-xs">{label.split(' · ')[0]}</b>
      {question?.row_label && <span className="max-w-[260px] truncate">{question.row_label}</span>}
      <button type="button" onClick={onFlip} aria-label={`Đổi chiều ${label}`} className={item.positive_high
        ? 'inline-flex items-center gap-1 rounded-md bg-ok-soft px-1.5 py-0.5 text-[11px] font-semibold text-ok'
        : 'inline-flex items-center gap-1 rounded-md bg-warn-soft px-1.5 py-0.5 text-[11px] font-semibold text-warn'}>
        <ArrowDownUp aria-hidden className="size-3" />{item.positive_high ? 'Tốt ở trên' : 'Tốt ở dưới'}
      </button>
      <button type="button" onClick={onRemove} aria-label={`Bỏ ${label} khỏi nhóm`} className="inline-flex size-8 items-center justify-center rounded-md text-muted hover:bg-sunken">
        <X aria-hidden className="size-3.5" />
      </button>
    </span>
  );
}

function GroupBlock({ group, questions, order, candidates, onChange, logic }: {
  group: AttitudeGroup;
  questions: Map<string, ParsedQuestion>;
  order: Map<string, number>;
  candidates: ParsedQuestion[];
  logic: LogicMap;
  onChange: (next: LogicMap) => void;
}) {
  const selectId = useId();
  return (
    <div className="flex flex-col gap-2.5 rounded-[10px] bg-sunken p-3.5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-[15px] font-semibold">{group.name}</span>
        <Badge tone="accent">{logic.source === 'AI' ? 'AI đề xuất' : logic.source === 'DEMO' ? 'Có sẵn' : 'Bạn sửa'} · {group.items.length} câu</Badge>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {group.items.map((item) => (
          <AttitudeChip
            key={item.entry_id}
            item={item}
            question={questions.get(item.entry_id)}
            index={order.get(item.entry_id) ?? 0}
            onFlip={() => onChange(toggleDirection(logic, group.group_id, item.entry_id))}
            onRemove={() => onChange(removeFromGroup(logic, group.group_id, item.entry_id))}
          />
        ))}
      </div>
      {candidates.length > 0 && (
        <div className="flex flex-wrap items-center gap-2">
          <label htmlFor={selectId} className="text-[13px] text-muted">Thêm câu vào nhóm:</label>
          <Select id={selectId} value="" onChange={(e) => e.target.value && onChange(addToGroup(logic, group.group_id, e.target.value))} className="max-w-[360px]">
            <option value="">Chọn câu…</option>
            {candidates.map((q) => <option key={q.entry_id} value={q.entry_id}>{questionShortLabel(q, order.get(q.entry_id))} — {q.title.slice(0, 60)}</option>)}
          </Select>
        </div>
      )}
    </div>
  );
}

/** ① Câu cùng đo một thái độ: cùng cao / cùng thấp theo "tính cách" từng người điền. */
export function AttitudeGroupsSection({ logic, questions, onChange }: {
  logic: LogicMap;
  questions: ParsedQuestion[];
  onChange: (next: LogicMap) => void;
}) {
  const [adding, setAdding] = useState(false);
  const newId = useId();
  const byEntry = new Map(questions.map((q) => [q.entry_id, q]));
  const order = new Map(questions.map((q, i) => [q.entry_id, i]));
  const candidates = attitudeCandidates(questions, logic);

  return (
    <Card aria-labelledby="h-attitude" className="flex flex-col gap-3 p-5">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 id="h-attitude" className="m-0 text-base font-semibold">① Câu cùng đo một thái độ</h2>
        <span className="text-xs text-muted">Cùng cao hoặc cùng thấp theo &quot;tính cách&quot; từng người điền</span>
      </div>
      {logic.attitude_groups.length === 0 && (
        <p className="m-0 text-sm text-muted">Không tìm thấy nhóm câu đánh giá nào. Nếu form có các câu chấm điểm cùng về một đối tượng, hãy thêm nhóm.</p>
      )}
      {logic.attitude_groups.map((group) => (
        <GroupBlock key={group.group_id} group={group} questions={byEntry} order={order} candidates={candidates} logic={logic} onChange={onChange} />
      ))}
      <p className="m-0 text-xs text-muted">
        &quot;Tốt ở trên&quot; = đáp án cuối là tích cực nhất (VD thang 1–5). &quot;Tốt ở dưới&quot; = đáp án đầu là tích cực nhất (VD &quot;Rất nhất quán → Không nhất quán&quot;). Bấm nhãn để đổi chiều.
      </p>
      {adding ? (
        <div className="flex flex-wrap items-center gap-2">
          <label htmlFor={newId} className="text-[13px] text-muted">Câu đầu tiên của nhóm mới:</label>
          <Select id={newId} value="" onChange={(e) => {
            if (!e.target.value) return;
            onChange(addGroup(logic, `Nhóm ${logic.attitude_groups.length + 1}`, e.target.value));
            setAdding(false);
          }} className="max-w-[360px]">
            <option value="">Chọn câu…</option>
            {candidates.map((q) => <option key={q.entry_id} value={q.entry_id}>{questionShortLabel(q, order.get(q.entry_id))} — {q.title.slice(0, 60)}</option>)}
          </Select>
          <Button size="sm" variant="quiet" onClick={() => setAdding(false)}>Huỷ</Button>
        </div>
      ) : (
        candidates.length > 0 && <Button size="sm" className="self-start border-dashed text-accent" onClick={() => setAdding(true)}>+ Thêm nhóm thái độ</Button>
      )}
    </Card>
  );
}
