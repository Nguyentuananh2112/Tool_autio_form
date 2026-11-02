import { Button } from '@/components/ui/Button';
import { PRESET_LABELS, type PresetKind } from '@/lib/presets';

const KINDS: PresetKind[] = ['uniform', 'bell', 'agree'];

export function PresetButtons({ onPick }: { onPick: (kind: PresetKind) => void }) {
  return (
    <div className="flex flex-wrap gap-1.5" role="group" aria-label="Phân phối nhanh">
      {KINDS.map((kind) => (
        <Button key={kind} size="sm" onClick={() => onPick(kind)}>{PRESET_LABELS[kind]}</Button>
      ))}
    </div>
  );
}

export function WeightTotal({ total }: { total: number }) {
  const ok = Math.round(total) === 100;
  return (
    <span className={ok ? 'text-[13px] font-semibold text-ok' : 'text-[13px] font-semibold text-warn'}>
      Tổng {Math.round(total)}% {ok ? '✓' : '— sẽ được tự chia lại cho đủ 100%'}
    </span>
  );
}
