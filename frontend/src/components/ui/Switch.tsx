import { cn } from '@/lib/cn';

export function Switch({ checked, onChange, label, description, disabled = false }: {
  checked: boolean;
  onChange: (value: boolean) => void;
  label: string;
  description?: string;
  disabled?: boolean;
}) {
  return (
    <div className="flex items-center justify-between gap-4">
      <span className="flex flex-col gap-0.5">
        <span className="text-sm font-medium">{label}</span>
        {description && <span className="text-xs text-muted">{description}</span>}
      </span>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        aria-label={label}
        disabled={disabled}
        onClick={() => onChange(!checked)}
        className={cn(
          'flex h-7 w-12 shrink-0 cursor-pointer rounded-full p-[3px] transition-colors disabled:opacity-50',
          checked ? 'justify-end bg-accent' : 'justify-start bg-muted/60',
        )}
      >
        <span className="size-[22px] rounded-full bg-white shadow" />
      </button>
    </div>
  );
}
