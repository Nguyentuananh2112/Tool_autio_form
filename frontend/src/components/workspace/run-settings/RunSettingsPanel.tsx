import { useId, useState } from 'react';

import { ErrorAlert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { Field, TextInput } from '@/components/ui/Field';
import { Switch } from '@/components/ui/Switch';
import { useCampaignActions } from '@/hooks/useCampaignActions';
import type { Readiness } from '@/lib/readiness';
import { useFormConfig, useFormConfigStore } from '@/store/formConfigStore';
import type { FormDetail } from '@/types/form';

import { ModePicker } from './ModePicker';
import { ReadinessChecklist } from './ReadinessChecklist';
import { TrialResultDialog } from './TrialResultDialog';

export function RunSettingsPanel({ form, readiness }: { form: FormDetail; readiness: Readiness }) {
  const config = useFormConfig(form.id);
  const patch = useFormConfigStore((s) => s.patchConfig);
  const actions = useCampaignActions(form.id, form.title, config);
  const [previewOnly, setPreviewOnly] = useState(false);
  const targetId = useId();
  const nameId = useId();
  const proxyId = useId();
  const excelMode = config.dataSource === 'EXCEL';
  const target = excelMode ? config.excel?.validRows ?? 0 : config.target;
  // Nguồn Excel: dữ liệu lấy từ file nên không cần đủ luật cho từng câu
  const blocked = (excelMode ? !config.excel?.validRows : readiness.issues.length > 0) || target <= 0;

  return (
    <aside aria-label="Thiết lập chạy" data-tour="run" className="flex flex-col gap-4 self-start rounded-xl border border-line bg-surface p-5 lg:sticky lg:top-6">
      <h2 className="m-0 text-[17px] font-semibold">Thiết lập chạy</h2>
      <Field label="Tên chiến dịch (không bắt buộc)" htmlFor={nameId}>
        <TextInput id={nameId} value={config.name} placeholder="VD: Đợt chính thức" onChange={(e) => patch(form.id, { name: e.target.value })} />
      </Field>
      <Field label="Số phản hồi cần gửi" htmlFor={targetId} hint={excelMode ? 'Bằng số dòng hợp lệ của file Excel.' : undefined}>
        <TextInput id={targetId} type="number" min={1} max={10000} value={target} disabled={excelMode} onChange={(e) => patch(form.id, { target: Math.max(1, Math.min(10000, Number(e.target.value) || 1)) })} className="text-base font-semibold" />
      </Field>
      <ModePicker schedule={config.schedule} target={target} onChange={(schedule) => patch(form.id, { schedule })} />

      {!form.is_demo && (
        <details className="border-t border-line pt-3.5">
          <summary className="min-h-7 cursor-pointer text-sm font-semibold">Nâng cao: proxy mạng và trình duyệt dự phòng</summary>
          <div className="flex flex-col gap-3 pt-3">
            <Field label="Proxy của mạng bạn (nếu cần)" htmlFor={proxyId} hint="Nếu Google giới hạn số lần gửi, app sẽ tự giãn nhịp và tạm dừng để bạn quyết định.">
              <TextInput id={proxyId} value={config.proxy} placeholder="http://user:pass@ip:port" className="font-mono text-[13px]" onChange={(e) => patch(form.id, { proxy: e.target.value })} />
            </Field>
            <Switch label="Dùng trình duyệt cho form kiểm tra dữ liệu phức tạp" description="Cần tải trình duyệt một lần trong Cài đặt → Trình duyệt dự phòng" checked={config.useFallback} onChange={(useFallback) => patch(form.id, { useFallback })} />
          </div>
        </details>
      )}

      <ReadinessChecklist readiness={readiness} config={config} />
      <ErrorAlert error={actions.error} />

      <div data-tour="start" className="flex flex-col gap-2">
        {!form.is_demo && (
          <label className="flex items-center gap-2 text-[13px] text-muted">
            <input type="checkbox" checked={previewOnly} onChange={(e) => setPreviewOnly(e.target.checked)} />Chỉ xem trước, không gửi lên Google
          </label>
        )}
        <Button onClick={() => void actions.runTrial(previewOnly || form.is_demo)} loading={actions.busy === 'trial'}>
          {form.is_demo || previewOnly ? 'Xem trước 1 phản hồi' : 'Gửi thử 1 phản hồi'}
        </Button>
        <Button variant="primary" size="lg" disabled={blocked} loading={actions.busy === 'start'} onClick={() => void actions.start()}>
          Bắt đầu chạy {target} phản hồi
        </Button>
        {blocked && <span className="text-center text-xs text-muted">Hoàn tất các câu còn thiếu để bắt đầu.</span>}
      </div>
      <TrialResultDialog result={actions.trial} onClose={actions.clearTrial} />
    </aside>
  );
}
