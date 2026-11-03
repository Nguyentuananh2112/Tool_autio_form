import { useId, useState } from 'react';

import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { Field, Select } from '@/components/ui/Field';
import { RULE_LEVELS, questionShortLabel } from '@/lib/logicLabels';
import { ruleCandidates } from '@/lib/logicDraft';
import type { ParsedQuestion } from '@/types/form';
import type { LogicRule } from '@/types/logic';

function ValuePicker({ question, values, onChange, legend }: {
  question: ParsedQuestion | undefined;
  values: string[];
  onChange: (next: string[]) => void;
  legend: string;
}) {
  if (!question) return null;
  return (
    <fieldset className="m-0 flex flex-col gap-1.5 border-0 p-0">
      <legend className="mb-1.5 p-0 text-[13px] font-medium text-muted">{legend}</legend>
      <div className="flex flex-wrap gap-x-4 gap-y-1">
        {question.options.map((option) => (
          <label key={option.value} className="flex min-h-8 items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={values.includes(option.value)}
              onChange={(e) => onChange(e.target.checked ? [...values, option.value] : values.filter((v) => v !== option.value))}
            />
            {option.label}
          </label>
        ))}
      </div>
    </fieldset>
  );
}

/** Sửa / thêm một ràng buộc NẾU câu A chọn X THÌ câu B (luôn / không bao giờ / thường) là Y. */
export function RuleEditorDialog({ rule, questions, onSave, onDelete, onClose }: {
  rule: LogicRule;
  questions: ParsedQuestion[];
  onSave: (rule: LogicRule) => void;
  onDelete?: () => void;
  onClose: () => void;
}) {
  const [draft, setDraft] = useState(rule);
  const ifId = useId();
  const thenId = useId();
  const levelId = useId();
  const candidates = ruleCandidates(questions);
  const order = new Map(questions.map((q, i) => [q.entry_id, i]));
  const byEntry = new Map(questions.map((q) => [q.entry_id, q]));
  const level = RULE_LEVELS.find((l) => l.then_op === draft.then_op && l.strength === draft.strength) ?? RULE_LEVELS[0]!;
  const valid = draft.if_entry !== draft.then_entry && draft.if_values.length > 0 && draft.then_values.length > 0;
  const option = (q: ParsedQuestion) => (
    <option key={q.entry_id} value={q.entry_id}>{questionShortLabel(q, order.get(q.entry_id))} — {q.title.slice(0, 70)}</option>
  );

  return (
    <Dialog
      open
      onClose={onClose}
      size="lg"
      title="Ràng buộc NẾU … THÌ …"
      description="Phản hồi vi phạm sẽ được sửa ở câu THÌ trước khi gửi."
      footer={(
        <>
          {onDelete && <Button variant="danger" className="mr-auto" onClick={onDelete}>Xoá ràng buộc</Button>}
          <Button variant="quiet" onClick={onClose}>Huỷ</Button>
          <Button variant="primary" disabled={!valid} onClick={() => onSave(draft)}>Lưu ràng buộc</Button>
        </>
      )}
    >
      <div className="flex flex-col gap-4">
        <Field label="NẾU câu" htmlFor={ifId}>
          <Select id={ifId} value={draft.if_entry} onChange={(e) => setDraft({ ...draft, if_entry: e.target.value, if_values: [] })}>
            {candidates.map(option)}
          </Select>
        </Field>
        <ValuePicker legend="chọn một trong các đáp án" question={byEntry.get(draft.if_entry)} values={draft.if_values} onChange={(if_values) => setDraft({ ...draft, if_values })} />
        <div className="grid gap-4 sm:grid-cols-[minmax(0,1fr)_220px]">
          <Field label="THÌ câu" htmlFor={thenId}>
            <Select id={thenId} value={draft.then_entry} onChange={(e) => setDraft({ ...draft, then_entry: e.target.value, then_values: [] })}>
              {candidates.filter((q) => q.entry_id !== draft.if_entry).map(option)}
            </Select>
          </Field>
          <Field label="Mức độ" htmlFor={levelId}>
            <Select id={levelId} value={level.id} onChange={(e) => {
              const next = RULE_LEVELS.find((l) => l.id === e.target.value) ?? RULE_LEVELS[0]!;
              setDraft({ ...draft, then_op: next.then_op, strength: next.strength });
            }}>
              {RULE_LEVELS.map((l) => <option key={l.id} value={l.id}>{l.label}</option>)}
            </Select>
          </Field>
        </div>
        <ValuePicker legend="đáp án" question={byEntry.get(draft.then_entry)} values={draft.then_values} onChange={(then_values) => setDraft({ ...draft, then_values })} />
        {draft.if_entry === draft.then_entry && <p className="m-0 text-sm text-bad">Ràng buộc phải nối hai câu khác nhau.</p>}
      </div>
    </Dialog>
  );
}
