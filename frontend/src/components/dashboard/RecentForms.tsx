import { Link } from 'react-router-dom';

import { Badge } from '@/components/ui/Badge';
import type { FormSummary } from '@/types/form';

export function RecentForms({ forms }: { forms: FormSummary[] }) {
  return (
    <section className="flex flex-col gap-3 rounded-xl border border-line bg-surface p-5">
      <h2 className="m-0 text-[17px] font-semibold">Form đã phân tích</h2>
      {forms.length === 0 && <p className="m-0 text-sm text-muted">Chưa có form nào. Dán link ở ô bên cạnh để bắt đầu.</p>}
      {forms.slice(0, 5).map((form) => (
        <Link key={form.id} to={`/forms/${form.id}`} className="flex flex-col gap-0.5 rounded-lg bg-sunken px-3 py-2.5 text-ink no-underline hover:bg-accent-soft">
          <span className="flex flex-wrap items-center gap-2 text-sm font-semibold">
            {form.title}
            {form.is_demo && <Badge tone="accent">Tập dùng</Badge>}
          </span>
          <span className="text-[13px] text-muted">{form.total_pages} trang · {form.question_count} câu hỏi</span>
        </Link>
      ))}
    </section>
  );
}
