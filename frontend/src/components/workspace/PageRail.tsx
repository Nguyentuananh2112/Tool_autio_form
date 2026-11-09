import { cn } from '@/lib/cn';
import { isBranching, questionsByPage } from '@/lib/questions';
import type { Readiness } from '@/lib/readiness';
import type { ParsedFormStructure } from '@/types/form';

function navNote(structure: ParsedFormStructure, pageIndex: number): string | null {
  const section = structure.sections.find((s) => s.page_index === pageIndex);
  if (section?.navigation_action === 'SUBMIT') return 'Sau trang này → Gửi form';
  if (section?.navigation_action === 'GO_TO_PAGE') {
    const target = structure.sections.find((s) => s.section_item_id === section.jump_to_section_id);
    return target ? `Sau trang này → Trang ${target.page_index + 1}` : null;
  }
  return null;
}

/** Danh sách trang của form; bấm để cuộn tới trang đó. Màu cam = còn câu chưa cấu hình. */
export function PageRail({ structure, readiness }: { structure: ParsedFormStructure; readiness: Readiness }) {
  const pages = questionsByPage(structure);
  const missingByPage = new Map<number, number>();
  for (const issue of readiness.issues) missingByPage.set(issue.pageIndex, (missingByPage.get(issue.pageIndex) ?? 0) + 1);

  return (
    <nav aria-label="Các trang của form" data-tour="rail" className="flex flex-col gap-1 self-start rounded-xl border border-line bg-surface p-2.5 lg:sticky lg:top-6 lg:max-h-[calc(100vh-3rem)] lg:overflow-y-auto lg:overscroll-contain">
      <span className="px-2 py-1.5 text-xs font-semibold uppercase tracking-wide text-muted">{structure.total_pages} trang</span>
      {structure.sections.map((section) => {
        const questions = pages.get(section.page_index) ?? [];
        const missing = missingByPage.get(section.page_index) ?? 0;
        const notes = [
          missing > 0 ? `${missing} câu chưa xong` : questions.length === 0 ? 'Không có câu hỏi' : 'Đã cấu hình',
          questions.some(isBranching) ? 'rẽ nhánh' : null,
          navNote(structure, section.page_index),
        ].filter(Boolean);
        return (
          <a
            key={section.page_index}
            href={`#page-${section.page_index}`}
            className="flex flex-col gap-0.5 rounded-lg px-2.5 py-2 text-ink no-underline hover:bg-sunken"
          >
            <span className="flex justify-between gap-2 text-[13px] font-semibold">
              <span>{section.title}</span>
              <span className="tabular font-medium text-muted">{questions.length}</span>
            </span>
            <span className={cn('text-xs', missing > 0 ? 'text-warn' : 'text-muted')}>{notes.join(' · ')}</span>
          </a>
        );
      })}
    </nav>
  );
}
