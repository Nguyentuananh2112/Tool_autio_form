import { useId } from 'react';

import { Field, TextInput } from '@/components/ui/Field';
import { cn } from '@/lib/cn';
import { formatDecimal } from '@/lib/format';
import type { ScheduleConfig, ScheduleMode } from '@/types/campaign';

const MODES: { mode: ScheduleMode; title: string; text: string }[] = [
  { mode: 'BURST', title: 'Tốc độ tối đa', text: 'Gửi song song, xong nhanh nhất.' },
  { mode: 'SCHEDULED', title: 'Rải đều tự nhiên', text: 'Khoảng nghỉ ngẫu nhiên như người thật.' },
];

export function ModePicker({ schedule, target, onChange }: {
  schedule: ScheduleConfig;
  target: number;
  onChange: (schedule: ScheduleConfig) => void;
}) {
  const durationId = useId();
  const concurrencyId = useId();
  const name = useId();
  const minutes = schedule.duration_minutes ?? 60;
  return (
    <div className="flex flex-col gap-3">
      <fieldset className="m-0 flex flex-col gap-2 border-0 p-0">
        <legend className="mb-2 p-0 text-[13px] font-medium text-muted">Cách gửi</legend>
        {MODES.map((option) => {
          const active = schedule.mode === option.mode;
          return (
            <label key={option.mode} className={cn('flex cursor-pointer gap-2.5 rounded-[10px] p-3', active ? 'border-2 border-accent bg-accent-soft' : 'border border-line')}>
              <input
                type="radio"
                name={name}
                checked={active}
                onChange={() => onChange({ ...schedule, mode: option.mode, duration_minutes: option.mode === 'SCHEDULED' ? minutes : schedule.duration_minutes })}
                className="mt-0.5"
              />
              <span className="flex flex-col gap-0.5"><strong className="text-sm">{option.title}</strong><span className="text-[13px] text-muted">{option.text}</span></span>
            </label>
          );
        })}
      </fieldset>
      {schedule.mode === 'SCHEDULED' ? (
        <Field label="Trong khoảng (phút)" htmlFor={durationId} hint={target > 0 ? `Trung bình ~${formatDecimal((minutes * 60) / target)} giây giữa hai phản hồi.` : undefined}>
          <TextInput id={durationId} type="number" min={1} value={minutes} onChange={(e) => onChange({ ...schedule, duration_minutes: Math.max(1, Number(e.target.value) || 1) })} />
        </Field>
      ) : (
        <Field label="Số luồng gửi cùng lúc" htmlFor={concurrencyId} hint="Càng nhiều càng nhanh, nhưng dễ bị Google giới hạn hơn.">
          <TextInput id={concurrencyId} type="number" min={1} max={50} value={schedule.concurrency} onChange={(e) => onChange({ ...schedule, concurrency: Math.max(1, Math.min(50, Number(e.target.value) || 1)) })} />
        </Field>
      )}
    </div>
  );
}
