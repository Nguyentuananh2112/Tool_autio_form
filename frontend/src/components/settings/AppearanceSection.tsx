import { Card } from '@/components/ui/Card';
import { cn } from '@/lib/cn';
import { type ThemePreference, useThemeStore } from '@/store/themeStore';

const OPTIONS: { value: ThemePreference; label: string }[] = [
  { value: 'light', label: 'Sáng' },
  { value: 'dark', label: 'Tối' },
  { value: 'system', label: 'Theo Windows' },
];

export function AppearanceSection() {
  const { preference, setPreference } = useThemeStore();
  return (
    <Card aria-labelledby="s-look" className="flex flex-col gap-3 p-5">
      <h2 id="s-look" className="m-0 text-[17px] font-semibold">Giao diện</h2>
      <div role="radiogroup" aria-label="Chế độ màu" className="flex max-w-md gap-1 rounded-[10px] bg-sunken p-1">
        {OPTIONS.map((option) => (
          <button
            key={option.value}
            type="button"
            role="radio"
            aria-checked={preference === option.value}
            onClick={() => setPreference(option.value)}
            className={cn('min-h-10 flex-1 cursor-pointer rounded-[7px] border-0 text-[13px]', preference === option.value ? 'bg-surface font-semibold text-ink' : 'bg-transparent text-muted')}
          >
            {option.label}
          </button>
        ))}
      </div>
    </Card>
  );
}
