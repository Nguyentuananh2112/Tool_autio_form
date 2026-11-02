import { Badge, type BadgeTone } from '@/components/ui/Badge';
import { Select } from '@/components/ui/Field';
import { questionCode } from '@/lib/questions';
import type { ColumnMapping } from '@/types/excel';
import type { ParsedQuestion } from '@/types/form';

function howBadge(mapping: ColumnMapping): { text: string; tone: BadgeTone } {
  if (!mapping.entry_id) return { text: 'Bỏ qua', tone: 'neutral' };
  if (mapping.kind === 'CODE') return { text: 'Theo mã câu', tone: 'ok' };
  if (mapping.kind === 'MANUAL') return { text: 'Bạn chọn', tone: 'accent' };
  const percent = Math.round(mapping.score * 100);
  return percent >= 80 ? { text: `Giống tiêu đề ${percent}%`, tone: 'ok' } : { text: `Cần kiểm tra · ${percent}%`, tone: 'warn' };
}

const optionLabel = (q: ParsedQuestion) => `${questionCode(q) ? `${questionCode(q)} · ` : ''}${q.row_label ? `${q.grid_title?.slice(0, 40)} [${q.row_label}]` : q.title.slice(0, 70)}`;

export function MappingTable({ mappings, questions, onChange }: {
  mappings: ColumnMapping[];
  questions: ParsedQuestion[];
  onChange: (index: number, entryId: string | null) => void;
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[720px] border-collapse text-sm">
        <thead>
          <tr className="text-left text-xs uppercase tracking-wide text-muted">
            <th scope="col" className="px-5 py-2.5 font-semibold">Cột trong file</th>
            <th scope="col" className="px-3 py-2.5 font-semibold">Câu hỏi Google Form</th>
            <th scope="col" className="px-5 py-2.5 font-semibold">Cách ghép</th>
          </tr>
        </thead>
        <tbody>
          {mappings.map((mapping, index) => {
            const badge = howBadge(mapping);
            return (
              <tr key={mapping.column} className="border-t border-line">
                <td className="px-5 py-2.5 font-mono text-[13px] font-medium">{mapping.column}</td>
                <td className="px-3 py-2.5">
                  <Select aria-label={`Câu hỏi cho cột ${mapping.column}`} value={mapping.entry_id ?? ''} onChange={(e) => onChange(index, e.target.value || null)} className={badge.tone === 'warn' ? 'border-warn' : ''}>
                    <option value="">— Không ghép —</option>
                    {questions.map((q) => <option key={q.entry_id} value={q.entry_id}>{optionLabel(q)}</option>)}
                  </Select>
                </td>
                <td className="px-5 py-2.5"><Badge tone={badge.tone}>{badge.text}</Badge></td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
