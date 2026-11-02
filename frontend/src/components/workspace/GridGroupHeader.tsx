import { Button } from '@/components/ui/Button';
import { useFormConfig, useFormConfigStore } from '@/store/formConfigStore';
import type { ParsedQuestion } from '@/types/form';

import { effectiveWeights } from '@/hooks/useQuestionRule';

/** Đầu nhóm các hàng của một câu lưới: chép tỷ lệ của hàng đầu cho mọi hàng. */
export function GridGroupHeader({ formId, rows }: { formId: string; rows: ParsedQuestion[] }) {
  const config = useFormConfig(formId);
  const patchRules = useFormConfigStore((s) => s.patchRules);
  const first = rows[0];
  if (!first) return null;

  const copyFirstRow = () => {
    const weights = effectiveWeights(first, config.rules[first.entry_id]);
    patchRules(formId, rows.slice(1).map((row) => ({ entry_id: row.entry_id, question_type: row.type_id, weights })));
  };

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl bg-sunken px-4 py-3">
      <div className="flex flex-col gap-0.5">
        <strong className="whitespace-pre-line text-[15px]">{first.grid_title}</strong>
        <span className="text-[13px] text-muted">Câu lưới · {rows.length} hàng, mỗi hàng là một câu riêng</span>
      </div>
      <Button size="sm" onClick={copyFirstRow}>Áp dụng tỷ lệ hàng đầu cho mọi hàng</Button>
    </div>
  );
}
