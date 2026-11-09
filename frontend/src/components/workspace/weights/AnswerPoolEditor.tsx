import { ListPlus, Rows3, X } from 'lucide-react';
import { useEffect, useId, useState } from 'react';

import { Button } from '@/components/ui/Button';
import { TextArea, TextInput } from '@/components/ui/Field';

/**
 * Câu trả lời mẫu dạng danh sách: mỗi câu một dòng đánh số, xoá từng câu, thêm câu mới.
 * Ô văn bản lớn chỉ dùng khi "Dán / sửa hàng loạt". Tắt gạch đỏ chính tả (trình duyệt không hiểu tiếng Việt).
 */
export function AnswerPoolEditor({ label, value, onChange, emptyHint }: {
  label: string;
  value: string[];
  onChange: (lines: string[]) => void;
  emptyHint: string;
}) {
  const id = useId();
  const [bulk, setBulk] = useState(false);
  const [draft, setDraft] = useState('');
  const joined = value.join('\n');
  const [text, setText] = useState(joined);
  useEffect(() => setText(joined), [joined]);

  const commitBulk = () => onChange(text.split('\n').map((line) => line.trim()).filter(Boolean));
  const add = () => {
    const line = draft.trim();
    if (!line) return;
    onChange([...value, line]);
    setDraft('');
  };

  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <label htmlFor={bulk ? id : `${id}-add`} className="text-[13px] font-medium text-muted">
          {label} · <span className="tabular-nums">{value.length}</span> câu
        </label>
        <Button size="sm" variant="quiet" onClick={() => { if (bulk) commitBulk(); setBulk(!bulk); }}>
          {bulk ? <><Rows3 aria-hidden className="size-4" />Xem dạng danh sách</> : <><ListPlus aria-hidden className="size-4" />Dán / sửa hàng loạt</>}
        </Button>
      </div>

      {bulk ? (
        <>
          <TextArea id={id} rows={10} spellCheck={false} value={text} placeholder="Mỗi dòng một câu trả lời"
            onChange={(e) => setText(e.target.value)} onBlur={commitBulk} className="resize-y leading-relaxed" />
          <span className="text-xs text-muted">Mỗi dòng một câu. Thay đổi được lưu khi bạn bấm ra ngoài ô.</span>
        </>
      ) : (
        <>
          {value.length === 0 ? (
            <p className="m-0 rounded-[10px] border border-dashed border-line px-4 py-5 text-center text-[13px] text-muted">{emptyHint}</p>
          ) : (
            <ol aria-label={label} className="m-0 max-h-72 list-none overflow-y-auto overscroll-contain rounded-[10px] border border-line p-0">
              {value.map((line, index) => (
                <li key={`${index}-${line}`} className="group grid grid-cols-[2rem_minmax(0,1fr)_2rem] items-start gap-2 border-line px-3 py-2 text-sm leading-relaxed [&:not(:first-child)]:border-t">
                  <span aria-hidden className="pt-px text-right text-xs tabular-nums text-muted">{index + 1}</span>
                  <span className="break-words">{line}</span>
                  <button type="button" aria-label={`Xoá câu ${index + 1}`} onClick={() => onChange(value.filter((_, i) => i !== index))}
                    className="inline-flex size-7 items-center justify-center rounded-md text-muted opacity-0 hover:bg-sunken hover:text-bad focus-visible:opacity-100 group-hover:opacity-100">
                    <X aria-hidden className="size-3.5" />
                  </button>
                </li>
              ))}
            </ol>
          )}
          <div className="flex gap-2">
            <TextInput id={`${id}-add`} spellCheck={false} value={draft} placeholder="Thêm một câu rồi nhấn Enter…"
              onChange={(e) => setDraft(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); add(); } }} className="flex-1" />
            <Button disabled={!draft.trim()} onClick={add}>Thêm</Button>
          </div>
        </>
      )}
    </div>
  );
}
