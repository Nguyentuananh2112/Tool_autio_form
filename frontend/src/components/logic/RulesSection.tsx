import { Pencil } from 'lucide-react';
import { useState } from 'react';

import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { nextRuleId, removeRule, ruleCandidates, upsertRule } from '@/lib/logicDraft';
import { questionFullTitle, questionShortLabel, ruleLevel } from '@/lib/logicLabels';
import type { ParsedQuestion } from '@/types/form';
import type { LogicMap, LogicRule } from '@/types/logic';

import { RuleEditorDialog } from './RuleEditorDialog';

function labelsOf(question: ParsedQuestion | undefined, values: string[]): string {
  const byValue = new Map(question?.options.map((o) => [o.value, o.label]) ?? []);
  return values.map((v) => byValue.get(v) ?? v).join(' / ');
}

/** ② Ràng buộc NẾU…THÌ (VD "Dưới 18" thì nghề là "Học sinh - sinh viên"). */
export function RulesSection({ logic, questions, onChange }: {
  logic: LogicMap;
  questions: ParsedQuestion[];
  onChange: (next: LogicMap) => void;
}) {
  const [editing, setEditing] = useState<{ rule: LogicRule; isNew: boolean } | null>(null);
  const byEntry = new Map(questions.map((q) => [q.entry_id, q]));
  const order = new Map(questions.map((q, i) => [q.entry_id, i]));
  const candidates = ruleCandidates(questions);
  const code = (entry: string) => questionShortLabel(byEntry.get(entry), order.get(entry));

  const startNew = () => {
    const [first, second] = candidates;
    if (!first || !second) return;
    setEditing({
      isNew: true,
      rule: { rule_id: nextRuleId(logic), if_entry: first.entry_id, if_values: [], then_entry: second.entry_id, then_op: 'IS', then_values: [], strength: 'ALWAYS', reason: null },
    });
  };

  return (
    <Card aria-labelledby="h-rules" className="flex flex-col gap-3 p-5">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 id="h-rules" className="m-0 text-base font-semibold">② Ràng buộc NẾU … THÌ …</h2>
        <span className="text-xs text-muted">Phản hồi vi phạm &quot;Luôn&quot; / &quot;Không bao giờ&quot; sẽ được sửa trước khi gửi</span>
      </div>
      {logic.rules.length === 0 ? (
        <p className="m-0 text-sm text-muted">Không có ràng buộc nào. Thêm nếu có cặp câu mà người thật không thể trả lời ngược nhau (VD tuổi ↔ nghề nghiệp).</p>
      ) : (
        <div className="overflow-x-auto rounded-[10px] border border-line">
          <table className="w-full min-w-[560px] border-collapse text-[13px]">
            <thead>
              <tr className="text-left text-xs font-semibold uppercase tracking-wide text-muted">
                <th className="px-3.5 py-2.5">Nếu</th><th className="px-3.5 py-2.5">Thì</th><th className="px-3.5 py-2.5">Mức độ</th><th className="px-3.5 py-2.5 text-right">Sửa</th>
              </tr>
            </thead>
            <tbody>
              {logic.rules.map((rule) => {
                const level = ruleLevel(rule);
                return (
                  <tr key={rule.rule_id} className="border-t border-line align-middle" title={rule.reason ?? undefined}>
                    <td className="px-3.5 py-2" title={questionFullTitle(byEntry.get(rule.if_entry))}>
                      <b className="font-mono text-xs">{code(rule.if_entry)}</b> = {labelsOf(byEntry.get(rule.if_entry), rule.if_values)}
                    </td>
                    <td className="px-3.5 py-2" title={questionFullTitle(byEntry.get(rule.then_entry))}>
                      <b className="font-mono text-xs">{code(rule.then_entry)}</b> {rule.then_op === 'IS' ? '=' : '≠'} {labelsOf(byEntry.get(rule.then_entry), rule.then_values)}
                    </td>
                    <td className="px-3.5 py-2"><Badge tone={level.tone}>{level.label}</Badge></td>
                    <td className="px-3.5 py-1 text-right">
                      <button type="button" aria-label={`Sửa ràng buộc ${code(rule.if_entry)} → ${code(rule.then_entry)}`} onClick={() => setEditing({ rule, isNew: false })} className="inline-flex size-10 items-center justify-center rounded-lg text-muted hover:bg-sunken">
                        <Pencil aria-hidden className="size-4" />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
      {candidates.length >= 2 && <Button size="sm" className="self-start border-dashed text-accent" onClick={startNew}>+ Thêm ràng buộc</Button>}
      {editing && (
        <RuleEditorDialog
          rule={editing.rule}
          questions={candidates}
          onClose={() => setEditing(null)}
          onSave={(rule) => { onChange(upsertRule(logic, rule)); setEditing(null); }}
          onDelete={editing.isNew ? undefined : () => { onChange(removeRule(logic, editing.rule.rule_id)); setEditing(null); }}
        />
      )}
    </Card>
  );
}
