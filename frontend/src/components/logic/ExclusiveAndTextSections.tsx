import { Badge } from '@/components/ui/Badge';
import { Card } from '@/components/ui/Card';
import { toggleExclusive } from '@/lib/logicDraft';
import { questionShortLabel } from '@/lib/logicLabels';
import type { QuestionRuleConfig } from '@/types/campaign';
import type { ParsedQuestion } from '@/types/form';
import type { LogicMap, TextSentiment } from '@/types/logic';

/** ③ Ô chọn loại trừ: liệt kê mọi ô hộp kiểm AI đánh dấu, bỏ tích để cho phép chọn kèm. */
export function ExclusiveSection({ logic, questions, onChange }: {
  logic: LogicMap;
  questions: ParsedQuestion[];
  onChange: (next: LogicMap) => void;
}) {
  const byEntry = new Map(questions.map((q) => [q.entry_id, q]));
  const order = new Map(questions.map((q, i) => [q.entry_id, i]));
  return (
    <Card aria-labelledby="h-exclusive" className="flex flex-col gap-2 p-5">
      <h2 id="h-exclusive" className="m-0 text-base font-semibold">③ Ô chọn loại trừ (không đi kèm ô khác)</h2>
      {logic.exclusive_options.length === 0 && <p className="m-0 text-sm text-muted">Không có câu hộp kiểm nào có ô kiểu &quot;Không có…&quot;.</p>}
      {logic.exclusive_options.map((option) => {
        const question = byEntry.get(option.entry_id);
        const label = question?.options.find((o) => o.value === option.value)?.label ?? option.value;
        return (
          <label key={`${option.entry_id}-${option.value}`} className="flex min-h-11 items-center gap-2.5 text-sm">
            <input type="checkbox" checked onChange={() => onChange(toggleExclusive(logic, option.entry_id, option.value))} className="size-[18px]" />
            <b className="font-mono text-xs">{questionShortLabel(question, order.get(option.entry_id))}</b>&quot;{label}&quot;
          </label>
        );
      })}
    </Card>
  );
}

const SENTIMENTS: { value: TextSentiment; label: string; tone: 'ok' | 'neutral' | 'warn' }[] = [
  { value: 'POSITIVE', label: 'Tích cực', tone: 'ok' },
  { value: 'NEUTRAL', label: 'Trung lập', tone: 'neutral' },
  { value: 'NEGATIVE', label: 'Tiêu cực', tone: 'warn' },
];

/** ④ Câu tự luận theo thái độ: số câu mẫu mỗi loại (AI phân loại khi soát). */
export function TextAttitudeSection({ logic, questions, rules }: {
  logic: LogicMap;
  questions: ParsedQuestion[];
  rules: Record<string, QuestionRuleConfig>;
}) {
  if (logic.text_attitudes.length === 0) return null;
  const byEntry = new Map(questions.map((q) => [q.entry_id, q]));
  const order = new Map(questions.map((q, i) => [q.entry_id, i]));
  return (
    <Card aria-labelledby="h-text" className="flex flex-col gap-3 p-5">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 id="h-text" className="m-0 text-base font-semibold">④ Câu tự luận theo thái độ</h2>
        <span className="text-xs text-muted">Người chấm cao nhận câu khen, người chấm thấp nhận câu góp ý</span>
      </div>
      {logic.text_attitudes.map((text) => {
        const pool = rules[text.entry_id]?.text_pool ?? [];
        const count = (s: TextSentiment) => pool.filter((t) => (text.labels[t] ?? 'NEUTRAL') === s).length;
        return (
          <div key={text.entry_id} className="flex flex-wrap items-center gap-2 text-[13px]">
            <b className="min-w-9 font-mono text-xs">{questionShortLabel(byEntry.get(text.entry_id), order.get(text.entry_id))}</b>
            {pool.length === 0
              ? <span className="text-muted">Chưa có câu mẫu — thêm ở bước Cấu hình.</span>
              : SENTIMENTS.map((s) => <Badge key={s.value} tone={s.tone}>{s.label} {count(s.value)}</Badge>)}
          </div>
        );
      })}
    </Card>
  );
}
