import { useId } from 'react';

import { InfoHint } from '@/components/ui/InfoHint';
import { formatDecimal } from '@/lib/format';
import type { SpssGroupConfig } from '@/types/campaign';

function ParamSlider({ label, value, min, max, step, hint, onChange, help }: {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  hint: string;
  onChange: (value: number) => void;
  help?: { term: string; text: string };
}) {
  const id = useId();
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center justify-between gap-2">
        <span className="flex items-center gap-1">
          <label htmlFor={id} className="text-sm font-medium">{label}</label>
          {help && <InfoHint term={help.term}>{help.text}</InfoHint>}
        </span>
        <span className="tabular text-sm font-bold">{formatDecimal(value)}</span>
      </div>
      <input id={id} type="range" min={min} max={max} step={step} value={value} onChange={(e) => onChange(Number(e.target.value))} />
      <span className="text-xs text-muted">{hint}</span>
    </div>
  );
}

export function TargetParams({ draft, scale, onChange }: {
  draft: SpssGroupConfig;
  scale: [number, number];
  onChange: (patch: Partial<SpssGroupConfig>) => void;
}) {
  const radio = useId();
  const byAlpha = draft.r === null;
  return (
    <div className="flex flex-col gap-4">
      <ParamSlider label="Điểm trung bình mục tiêu" value={draft.mean} min={scale[0]} max={scale[1]} step={0.05}
        hint={`Trên thang ${scale[0]}–${scale[1]}. Quá sát biên sẽ khó đạt độ lệch chuẩn lớn.`} onChange={(mean) => onChange({ mean })} />
      <ParamSlider label="Độ lệch chuẩn" value={draft.std} min={0.4} max={1.2} step={0.05}
        hint="Mức độ phân tán câu trả lời của từng biến." onChange={(std) => onChange({ std })} />
      <fieldset className="m-0 flex flex-col gap-2 border-0 p-0">
        <legend className="mb-2 p-0 text-sm font-medium">Điều khiển độ tương quan theo</legend>
        <div className="flex gap-1 rounded-[10px] bg-sunken p-1">
          {[{ label: 'Hệ số r', alpha: false }, { label: 'Alpha mục tiêu', alpha: true }].map((option) => (
            <label key={option.label} className={`flex min-h-10 flex-1 cursor-pointer items-center justify-center gap-1.5 rounded-[7px] text-[13px] ${byAlpha === option.alpha ? 'bg-surface font-semibold' : 'text-muted'}`}>
              <input type="radio" name={radio} checked={byAlpha === option.alpha}
                onChange={() => onChange(option.alpha ? { r: null, alpha_target: draft.alpha_target ?? 0.85 } : { r: draft.r ?? 0.55 })} />
              {option.label}
            </label>
          ))}
        </div>
      </fieldset>
      {byAlpha ? (
        <ParamSlider label="Cronbach’s Alpha mục tiêu" value={draft.alpha_target ?? 0.85} min={0.6} max={0.95} step={0.01}
          hint="Từ 0,7 trở lên thường được coi là đạt; trên 0,9 là rất cao." onChange={(alpha_target) => onChange({ alpha_target })}
          help={{ term: 'Cronbach’s Alpha', text: 'Độ nhất quán của nhóm câu thang đo, từ 0 đến 1.' }} />
      ) : (
        <ParamSlider label="Tương quan giữa các biến (r)" value={draft.r ?? 0.55} min={0.3} max={0.85} step={0.05}
          hint="Gợi ý 0,45–0,7. Quá cao (> 0,85) khiến dữ liệu trông giả tạo khi chạy EFA." onChange={(r) => onChange({ r })}
          help={{ term: 'Tương quan (r)', text: 'Mức các câu trong nhóm “đi cùng nhau”: chọn cao ở câu này thì cũng có xu hướng chọn cao ở câu kia.' }} />
      )}
    </div>
  );
}
