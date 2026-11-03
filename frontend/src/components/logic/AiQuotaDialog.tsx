import { useId, useState } from 'react';

import { toApiError, type ApiError } from '@/api/client';
import { settingsApi } from '@/api/endpoints';
import { ErrorAlert } from '@/components/ui/Alert';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { TextInput } from '@/components/ui/Field';
import { KEY_SLOT_LABELS, KEY_STATE_LABELS } from '@/lib/logicLabels';
import type { KeyAttempt, KeySlot } from '@/types/logic';

const ORDER: KeySlot[] = ['USER', 'SHARED', 'BACKUP'];

/** Màn 12: mọi key đều hết lượt → dán key riêng, lưu vào kho bảo mật Windows rồi chạy tiếp đúng chỗ dừng. */
export function AiQuotaDialog({ keys, message, onClose, onSaved }: {
  keys: KeyAttempt[];
  message: string;
  onClose: () => void;
  onSaved: () => void;
}) {
  const inputId = useId();
  const [value, setValue] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const states = new Map(keys.map((k) => [k.slot, k.state]));

  const save = async () => {
    setSaving(true);
    setError(null);
    try {
      await settingsApi.saveGeminiKey(value.trim());
      onSaved();
    } catch (err) {
      setError(toApiError(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog
      open
      onClose={onClose}
      title={message}
      description="Bước Soát logic cần Gemini để đọc câu hỏi. Việc soát đang tạm dừng; dán key xong sẽ chạy tiếp từ chỗ dừng."
      footer={(
        <>
          <Button variant="quiet" onClick={onClose}>Để sau</Button>
          <Button variant="primary" disabled={!value.trim()} loading={saving} onClick={() => void save()}>Lưu key &amp; tiếp tục</Button>
        </>
      )}
    >
      <div className="flex flex-col gap-4">
        <section aria-labelledby={`${inputId}-chain`} className="flex flex-col gap-2">
          <h3 id={`${inputId}-chain`} className="m-0 text-sm font-semibold">App đã thử lần lượt</h3>
          <ol className="m-0 flex list-none flex-col rounded-[10px] border border-line p-0">
            {ORDER.map((slot, index) => {
              const state = KEY_STATE_LABELS[states.get(slot) ?? 'MISSING'];
              return (
                <li key={slot} className="grid min-h-12 grid-cols-[28px_minmax(0,1fr)_auto] items-center gap-2.5 border-line px-3.5 text-sm [&:not(:first-child)]:border-t">
                  <span className="font-mono text-xs font-semibold text-muted">{index + 1}</span>
                  <span>{KEY_SLOT_LABELS[slot]}</span>
                  <Badge tone={state.tone}>{state.label}</Badge>
                </li>
              );
            })}
          </ol>
        </section>
        <div className="flex flex-col gap-1.5">
          <label htmlFor={inputId} className="text-sm font-semibold">API key Gemini của bạn</label>
          <TextInput id={inputId} type="password" autoComplete="off" value={value} placeholder="Dán API key Gemini (AIza… hoặc AQ.…)" className="font-mono" onChange={(e) => setValue(e.target.value)} />
          <span className="text-xs text-muted">Key được cất trong kho bảo mật của Windows trên máy này, chỉ dùng để gọi Google. Đổi hoặc xoá trong Cài đặt → Gemini.</span>
        </div>
        <details open className="rounded-[10px] bg-sunken px-4 py-3.5">
          <summary className="min-h-6 cursor-pointer text-sm font-semibold">Chưa có key? Tạo miễn phí trong 2 phút</summary>
          <ol className="mb-0 mt-2.5 flex flex-col gap-1.5 pl-5 text-sm">
            <li>Mở <a href="https://aistudio.google.com/apikey" target="_blank" rel="noreferrer">aistudio.google.com/apikey</a> và đăng nhập tài khoản Google.</li>
            <li>Bấm <b>Create API key</b> (Tạo API key), chọn dự án bất kỳ.</li>
            <li>Bấm <b>Copy</b> rồi dán vào ô phía trên.</li>
          </ol>
        </details>
        <ErrorAlert error={error} />
      </div>
    </Dialog>
  );
}
