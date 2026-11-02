import { useEffect, useId, useState } from 'react';

import { TextArea } from '@/components/ui/Field';

/** Nhập danh sách câu, mỗi dòng một câu (câu trả lời mẫu, nội dung "Mục khác"). */
export function LinesEditor({ label, value, onChange, placeholder, rows = 4 }: {
  label: string;
  value: string[];
  onChange: (lines: string[]) => void;
  placeholder?: string;
  rows?: number;
}) {
  const id = useId();
  const joined = value.join('\n');
  const [text, setText] = useState(joined);
  // Theo dõi chuỗi (không phải mảng): mảng mới mỗi lần vẽ sẽ xóa nội dung đang gõ
  useEffect(() => setText(joined), [joined]);

  const commit = () => onChange(text.split('\n').map((line) => line.trim()).filter(Boolean));
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-[13px] font-medium text-muted">{label} · {value.length} câu</label>
      <TextArea id={id} rows={rows} value={text} placeholder={placeholder} onChange={(e) => setText(e.target.value)} onBlur={commit} />
      <span className="text-xs text-muted">Mỗi dòng một câu. Thay đổi được lưu khi bạn bấm ra ngoài ô.</span>
    </div>
  );
}
