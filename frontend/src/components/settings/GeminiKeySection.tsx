import { useId, useState } from 'react';

import { type ApiError, toApiError } from '@/api/client';
import { settingsApi } from '@/api/endpoints';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { TextInput } from '@/components/ui/Field';
import type { AppSettingsRead } from '@/types/settings';

/** Thứ tự dùng key: key riêng → key chung của app → key dự phòng (SPEC-020). */
function keyStatus(settings: AppSettingsRead | null): string {
  if (!settings) return '';
  if (settings.gemini_user_key) return `● Đang dùng key riêng của bạn (ưu tiên trước key chung) · mô hình ${settings.gemini_model}`;
  if (settings.gemini_shared_key) return '● App có sẵn key chung — bạn không cần nhập key. Chỉ dán key riêng khi app báo hết lượt AI.';
  return 'Chưa có key — Soát logic và sinh câu tự luận bằng AI cần một API key Gemini.';
}

export function GeminiKeySection({ settings, onSaved }: { settings: AppSettingsRead | null; onSaved: () => void }) {
  const id = useId();
  const [key, setKey] = useState('');
  const [busy, setBusy] = useState<'save' | 'delete' | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [saved, setSaved] = useState(false);

  const run = async (kind: 'save' | 'delete') => {
    setBusy(kind);
    setError(null);
    setSaved(false);
    try {
      if (kind === 'save') await settingsApi.saveGeminiKey(key.trim());
      else await settingsApi.deleteGeminiKey();
      setKey('');
      setSaved(kind === 'save');
      onSaved();
    } catch (err) {
      setError(toApiError(err));
    } finally {
      setBusy(null);
    }
  };

  return (
    <Card aria-labelledby="s-ai" className="flex flex-col gap-3.5 p-5">
      <h2 id="s-ai" className="m-0 text-[17px] font-semibold">Gemini AI</h2>
      <label htmlFor={id} className="text-[13px] font-medium text-muted">API key</label>
      <div className="flex flex-wrap gap-2">
        <TextInput id={id} type="password" autoComplete="off" value={key} placeholder={settings?.gemini_user_key ? '•••••••• (đã lưu — nhập key mới để thay)' : 'Dán API key Gemini (AIza… hoặc AQ.…)'} onChange={(e) => setKey(e.target.value)} className="min-w-[280px] flex-1 font-mono" />
        <Button variant="primary" disabled={key.trim().length < 10} loading={busy === 'save'} onClick={() => void run('save')}>Lưu key</Button>
        {settings?.gemini_user_key && <Button variant="danger" loading={busy === 'delete'} onClick={() => void run('delete')}>Xóa key</Button>}
      </div>
      <span className={settings?.gemini_key_configured ? 'inline-flex items-center gap-1.5 text-[13px] text-ok' : 'text-[13px] text-muted'}>
        {keyStatus(settings)}
      </span>
      {saved && <Alert tone="ok">Đã lưu. Thử bấm “Sinh 50 câu bằng Gemini” ở một câu tự luận để kiểm tra.</Alert>}
      {error && <Alert tone="bad" title={error.message} />}
      <p className="m-0 text-[13px] text-muted">
        Chưa có key? <a href="https://aistudio.google.com/apikey" target="_blank" rel="noreferrer">Lấy miễn phí tại Google AI Studio</a>. Key được lưu trong kho bảo mật của Windows trên máy này.
      </p>
    </Card>
  );
}
