import { useId, type ReactNode } from 'react';

export function WeightSliderRow({ label, sublabel, value, onChange, disabled = false }: {
  label: string;
  sublabel?: ReactNode;
  value: number;
  onChange: (value: number) => void;
  disabled?: boolean;
}) {
  const id = useId();
  return (
    <div className="grid grid-cols-[minmax(120px,240px)_minmax(0,1fr)_72px] items-center gap-3.5">
      <div className="flex flex-col gap-0.5">
        <label htmlFor={id} className="text-sm">{label}</label>
        {sublabel && <span className="text-xs text-accent">{sublabel}</span>}
      </div>
      <input id={id} type="range" min={0} max={100} step={1} value={value} disabled={disabled} onChange={(e) => onChange(Number(e.target.value))} className="w-full" />
      <div className="flex items-center justify-end gap-1">
        <input
          type="number"
          min={0}
          max={100}
          value={value}
          disabled={disabled}
          aria-label={`Tỷ lệ % cho ${label}`}
          onChange={(e) => onChange(Math.max(0, Math.min(100, Number(e.target.value) || 0)))}
          className="tabular w-14 rounded-md border border-line bg-bg px-1.5 py-1 text-right text-sm font-semibold"
        />
        <span aria-hidden className="text-sm text-muted">%</span>
      </div>
    </div>
  );
}
