import { cn } from '@/lib/cn';

export type WorkspaceTab = 'weights' | 'spss' | 'excel';

const TABS: { id: WorkspaceTab; label: string }[] = [
  { id: 'weights', label: 'Tỷ lệ & tự luận' },
  { id: 'spss', label: 'Nhóm tương quan SPSS' },
  { id: 'excel', label: 'Nhập từ Excel / CSV' },
];

export function SourceTabs({ active, onChange, counts }: {
  active: WorkspaceTab;
  onChange: (tab: WorkspaceTab) => void;
  counts: Partial<Record<WorkspaceTab, number>>;
}) {
  return (
    <div role="tablist" aria-label="Nguồn dữ liệu" data-tour="tabs" className="flex flex-wrap gap-1 self-start border-b border-line">
      {TABS.map((tab) => {
        const selected = tab.id === active;
        return (
          <button
            key={tab.id}
            type="button"
            role="tab"
            aria-selected={selected}
            onClick={() => onChange(tab.id)}
            className={cn(
              'inline-flex min-h-11 cursor-pointer items-center gap-2 border-0 border-b-2 bg-transparent px-3.5 text-sm',
              selected ? 'border-accent font-semibold text-accent' : 'border-transparent font-medium text-muted hover:text-ink',
            )}
          >
            {tab.label}
            {counts[tab.id] ? <span className="rounded-full bg-sunken px-2 text-xs">{counts[tab.id]}</span> : null}
          </button>
        );
      })}
    </div>
  );
}
