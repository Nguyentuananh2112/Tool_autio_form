import { type FormEvent, useId, useState } from 'react';

import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { TextInput } from '@/components/ui/Field';
import { useFormParse } from '@/hooks/useFormParse';

export function QuickParseCard() {
  const inputId = useId();
  const [url, setUrl] = useState('');
  const { busy, error, parse, openDemo } = useFormParse();

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (url.trim()) void parse(url.trim());
  };

  return (
    <form onSubmit={submit} data-tour="quick" className="flex flex-col gap-3 rounded-xl border border-line bg-surface p-5">
      <h2 className="m-0 text-[17px] font-semibold">Phân tích một Google Form</h2>
      <label htmlFor={inputId} className="text-[13px] font-medium text-muted">Link chia sẻ của form</label>
      <div className="flex flex-wrap gap-2">
        <TextInput
          id={inputId}
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://forms.gle/... hoặc docs.google.com/forms/d/e/.../viewform"
          invalid={Boolean(error)}
          className="min-w-[260px] flex-1"
        />
        <Button type="submit" variant="primary" loading={busy === 'parse'} disabled={!url.trim()}>Phân tích</Button>
      </div>
      <p className="m-0 text-[13px] text-muted">
        Lấy link từ nút <strong className="text-ink">Gửi</strong> → biểu tượng liên kết trong Google Forms. Link chỉnh sửa (có <code className="font-mono">/edit</code>) không dùng được.
      </p>
      {error && <Alert tone="bad" title={error.message} />}
      <div className="flex flex-wrap items-center gap-3 border-t border-line pt-3 text-sm">
        <span className="text-muted">Chưa có form? Tập dùng trước với form mẫu — không gửi gì ra ngoài.</span>
        <Button size="sm" onClick={() => void openDemo()} loading={busy === 'demo'}>Thử với form mẫu</Button>
      </div>
    </form>
  );
}
