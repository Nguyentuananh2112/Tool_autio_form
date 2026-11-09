import { useId } from 'react';

import { Badge } from '@/components/ui/Badge';
import { Card } from '@/components/ui/Card';
import { formatDecimal } from '@/lib/format';
import { setConsistency } from '@/lib/logicDraft';
import { CONSISTENCY_LEVELS, VIOLATION_KIND_LABELS, questionShortLabel } from '@/lib/logicLabels';
import type { ParsedQuestion } from '@/types/form';
import type { LogicMap, LogicReviewResult } from '@/types/logic';

export function ConsistencyCard({ logic, onChange }: { logic: LogicMap; onChange: (next: LogicMap) => void }) {
  const id = useId();
  const index = Math.max(0, CONSISTENCY_LEVELS.findIndex((l) => l.value === logic.consistency));
  const level = CONSISTENCY_LEVELS[index]!;
  return (
    <Card aria-labelledby={`${id}-h`} className="flex flex-col gap-3 p-5">
      <h2 id={`${id}-h`} className="m-0 text-base font-semibold">Độ đồng đều trong một người</h2>
      <div className="flex justify-between text-sm"><label htmlFor={id}>Mức</label><b>{level.label}</b></div>
      <input id={id} type="range" min={0} max={2} step={1} value={index} className="w-full accent-[var(--accent)]"
        onChange={(e) => onChange(setConsistency(logic, CONSISTENCY_LEVELS[Number(e.target.value)]!.value))} />
      <div className="flex justify-between text-xs text-muted">{CONSISTENCY_LEVELS.map((l) => <span key={l.value}>{l.label}</span>)}</div>
      <span className="text-xs text-muted">{level.hint}</span>
    </Card>
  );
}

function Row({ label, before, after }: { label: string; before: string; after: string }) {
  return (
    <tr className="border-t border-line">
      <td className="px-3 py-2">{label}</td>
      <td className="px-3 py-2 text-right tabular-nums text-bad">{before}</td>
      <td className="px-3 py-2 text-right font-semibold tabular-nums text-ok">{after}</td>
    </tr>
  );
}

/** Kết quả soát mẫu thử: so cách sinh cũ (không soát) với cách mới. */
export function ReviewResultCard({ result, logic, questions }: { result: LogicReviewResult; logic: LogicMap; questions: ParsedQuestion[] }) {
  const byEntry = new Map(questions.map((q) => [q.entry_id, q]));
  const order = new Map(questions.map((q, i) => [q.entry_id, i]));
  const ruleLabel = (key: string) => {
    const rule = logic.rules.find((r) => r.rule_id === key);
    return rule ? `${questionShortLabel(byEntry.get(rule.if_entry), order.get(rule.if_entry))} → ${questionShortLabel(byEntry.get(rule.then_entry), order.get(rule.then_entry))}` : key;
  };
  const keyLabel = (kind: string, key: string) =>
    kind === 'RULE' ? ruleLabel(key)
      : kind === 'EXCLUSIVE' ? questionShortLabel(byEntry.get(key), order.get(key))
        : logic.attitude_groups.find((g) => g.group_id === key)?.name ?? key;

  // Lệch hơn 0,03 so với mục tiêu mới đáng báo (sai số mẫu thử 200 người ~ ±0,02)
  const highAlpha = result.spss_alpha.filter((g) => g.after !== null && g.target !== null && g.after > g.target + 0.03);

  return (
    <Card aria-labelledby="h-check" aria-live="polite" className="flex flex-col gap-3 p-5">
      <h2 id="h-check" className="m-0 text-base font-semibold">Kết quả soát {result.sample_size} phản hồi thử</h2>
      <div className="flex flex-wrap items-baseline gap-2.5">
        <span className="text-4xl font-bold tabular-nums">{result.inconsistent_after}</span>
        <span className="text-sm text-muted">mâu thuẫn còn lại</span>
        <Badge tone={result.ready ? 'ok' : 'warn'} className="ml-auto">{result.ready ? 'Sẵn sàng chạy' : 'Cần xem lại'}</Badge>
      </div>
      <div className="overflow-x-auto rounded-[10px] border border-line">
        <table className="w-full border-collapse text-[13px]">
          <thead><tr className="text-xs font-semibold text-muted"><th className="px-3 py-2 text-left">Chỉ số</th><th className="px-3 py-2 text-right">Trước</th><th className="px-3 py-2 text-right">Sau</th></tr></thead>
          <tbody>
            <Row label="Phản hồi có mâu thuẫn" before={String(result.inconsistent_before)} after={String(result.inconsistent_after)} />
            {result.correlations.map((c) => (
              <Row key={c.group_id} label={`Độ khớp trong "${c.name}"`} before={c.before === null ? '—' : formatDecimal(c.before)} after={c.after === null ? '—' : formatDecimal(c.after)} />
            ))}
            {result.spss_alpha.map((a) => (
              <Row key={`alpha-${a.group_id}`} label={`Alpha nhóm SPSS "${a.name}"${a.target !== null ? ` (mục tiêu ${formatDecimal(a.target)})` : ''}`} before={a.before === null ? '—' : formatDecimal(a.before)} after={a.after === null ? '—' : formatDecimal(a.after)} />
            ))}
            {result.violations.filter((v) => v.before > 0 || v.after > 0).slice(0, 6).map((v) => (
              <Row key={`${v.kind}-${v.key}`} label={`${VIOLATION_KIND_LABELS[v.kind]}: ${keyLabel(v.kind, v.key)}`} before={String(v.before)} after={String(v.after)} />
            ))}
          </tbody>
        </table>
      </div>
      {highAlpha.length > 0 && (
        <p className="m-0 rounded-[10px] bg-accent-soft px-3 py-2.5 text-[13px] text-accent">
          Alpha của {highAlpha.map((g) => `"${g.name}"`).join(', ')} cao hơn mục tiêu vì các câu được giữ &quot;sàn sàn&quot; nhau. Muốn sát mục tiêu hơn: giảm r (hoặc Alpha mục tiêu) của nhóm ở bước Cấu hình, hoặc chọn độ đồng đều &quot;Đa dạng&quot;.
        </p>
      )}
      {result.unlabeled_texts > 0 && (
        <p className="m-0 text-[13px] text-muted">
          {result.unlabeled_texts} câu tự luận mẫu chưa phân loại được khen / chê (Gemini đang bận) nên tạm coi là trung lập. Bấm &quot;Soát lại&quot; sau ít phút để thử lại.
        </p>
      )}
      {result.drifts.length > 0 && (
        <div className="flex flex-col gap-1 rounded-[10px] bg-warn-soft px-3 py-2.5 text-[13px] text-warn">
          <strong>Tỷ lệ một vài câu xê dịch để giữ câu trả lời khớp nhau:</strong>
          {result.drifts.map((d) => <span key={d.entry_id}>{questionShortLabel(byEntry.get(d.entry_id), order.get(d.entry_id))}: lệch tối đa {formatDecimal(d.max_drift_pct)} điểm %</span>)}
          <span className="text-xs">Do các câu cùng thái độ đang có tỷ lệ rất khác nhau. Có thể chỉnh tỷ lệ ở bước Cấu hình cho gần nhau hơn.</span>
        </div>
      )}
      <span className="text-xs text-muted">&quot;Trước&quot; = sinh theo cách cũ (không soát). &quot;Độ khớp&quot; = mức các câu cùng thái độ cùng cao / cùng thấp (0 → 1). Chạy trong máy, không gửi gì lên Google.</span>
    </Card>
  );
}

export function SamplePersonCard({ result, logic, questions }: { result: LogicReviewResult; logic: LogicMap; questions: ParsedQuestion[] }) {
  const sample = result.sample;
  if (!sample) return null;
  const order = new Map(questions.map((q, i) => [q.entry_id, i]));
  const byEntry = new Map(questions.map((q) => [q.entry_id, q]));
  const shown = (logic.attitude_groups[0]?.items ?? []).map((i) => i.entry_id).filter((e) => sample.answers[e]).slice(0, 8);
  return (
    <Card aria-labelledby="h-person" className="flex flex-col gap-2.5 p-5">
      <h2 id="h-person" className="m-0 text-base font-semibold">Xem thử một người điền</h2>
      <span className="text-[13px] text-muted">Thái độ chung: <b className="text-ink">{sample.attitude}</b></span>
      {shown.map((entry) => (
        <div key={entry} className="grid grid-cols-[minmax(0,1fr)_auto] gap-2 text-[13px]">
          <span className="truncate" title={byEntry.get(entry)?.title}>{questionShortLabel(byEntry.get(entry), order.get(entry))}</span>
          <b>{sample.answers[entry]?.join(', ')}</b>
        </div>
      ))}
    </Card>
  );
}
