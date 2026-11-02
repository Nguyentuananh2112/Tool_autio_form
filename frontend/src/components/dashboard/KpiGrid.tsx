export interface Kpi {
  label: string;
  value: string;
  hint: string;
}

export function KpiGrid({ items, tourId }: { items: Kpi[]; tourId?: string }) {
  return (
    <section aria-label="Chỉ số chính" data-tour={tourId} className="grid grid-cols-[repeat(auto-fit,minmax(200px,1fr))] gap-4">
      {items.map((kpi) => (
        <div key={kpi.label} className="flex flex-col gap-2 rounded-xl border border-line bg-surface px-5 py-4">
          <span className="text-[13px] font-medium text-muted">{kpi.label}</span>
          <span className="tabular text-[28px] font-bold tracking-tight">{kpi.value}</span>
          <span className="text-[13px] text-muted">{kpi.hint}</span>
        </div>
      ))}
    </section>
  );
}
