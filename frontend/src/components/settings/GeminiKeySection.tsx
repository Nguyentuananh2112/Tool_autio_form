import { useId, useState } from 'react';

import { type ApiError, toApiError } from '@/api/client';
import { settingsApi } from '@/api/endpoints';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { TextInput } from '@/components/ui/Field';
import type { AppSettingsRead } from '@/types/settings';

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
        <TextInput id={id} type="password" autoComplete="off" value={key} placeholder={settings?.gemini_key_configured ? '•••••••• (đã lưu — nhập key mới để thay)' : 'AIza...'} onChange={(e) => setKey(e.target.value)} className="min-w-[280px] flex-1 font-mono" />
        <Button variant="primary" disabled={key.trim().length < 10} loading={busy === 'save'} onClick={() => void run('save')}>Lưu key</Button>
        {settings?.gemini_key_configured && <Button variant="danger" loading={busy === 'delete'} onClick={() => void run('delete')}>Xóa key</Button>}
      </div>
      <span className={settings?.gemini_key_configured ? 'inline-flex items-center gap-1.5 text-[13px] text-ok' : 'text-[13px] text-muted'}>
        {settings?.gemini_key_configured ? `● Đã có key · mô hình ${settings.gemini_model}` : 'Chưa có key — câu tự luận cần tự dán câu trả lời mẫu.'}
      </span>
      {saved && <Alert tone="ok">Đã lưu. Thử bấm “Sinh 50 câu bằng Gemini” ở một câu tự luận để kiểm tra.</Alert>}
      {error && <Alert tone="bad" title={error.message} />}
      <p className="m-0 text-[13px] text-muted">
        Chưa có key? <a href="https://aistudio.google.com/apikey" target="_blank" rel="noreferrer">Lấy miễn phí tại Google AI Studio</a>. Key được lưu trong kho bảo mật của Windows trên máy này.
      </p>
    </Card>
  );
}
