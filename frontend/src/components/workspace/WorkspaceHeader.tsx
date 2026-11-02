import { useId, useState } from 'react';

import { Alert } from '@/components/ui/Alert';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { TextInput } from '@/components/ui/Field';
import { useFormParse } from '@/hooks/useFormParse';
import { isBranching } from '@/lib/questions';
import { useFormConfig } from '@/store/formConfigStore';
import type { FormDetail } from '@/types/form';

export function WorkspaceHeader({ form }: { form: FormDetail }) {
  const config = useFormConfig(form.id);
  const urlId = useId();
  const [url, setUrl] = useState(form.view_url);
  const { busy, error, parse } = useFormParse();
  const branches = form.structure.questions.filter(isBranching).length;
  const chips = [`${form.total_pages} trang`, `${form.question_count} câu hỏi`];
  if (branches > 0) chips.push(`${branches} câu rẽ nhánh`);
  if (config.groups.length > 0) chips.push(`${config.groups.length} nhóm SPSS`);

  return (
    <header className="flex flex-col gap-3.5">
      <div className="flex min-w-0 flex-col gap-1.5">
        <span className="text-[13px] text-muted">Cấu hình khảo sát</span>
        <h1 className="m-0 text-2xl font-bold tracking-tight">{form.title}</h1>
        <div className="flex flex-wrap gap-2">
          {form.is_demo && <Badge tone="accent">Chế độ tập dùng — không gửi gì ra ngoài</Badge>}
          {chips.map((chip) => <Badge key={chip}>{chip}</Badge>)}
        </div>
      </div>
      {!form.is_demo && (
        <form className="flex flex-wrap gap-2" onSubmit={(e) => { e.preventDefault(); void parse(url); }}>
          <label htmlFor={urlId} className="sr-only">Link Google Form</label>
          <TextInput id={urlId} value={url} onChange={(e) => setUrl(e.target.value)} className="min-w-[320px] flex-1 font-mono text-[13px]" />
          <Button type="submit" variant="dark" loading={busy === 'parse'}>Phân tích lại</Button>
        </form>
      )}
      {error && <Alert tone="bad" title={error.message} />}
    </header>
  );
}
