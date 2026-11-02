import { Plus } from 'lucide-react';
import { useState } from 'react';

import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { EmptyState } from '@/components/ui/EmptyState';
import { InfoHint } from '@/components/ui/InfoHint';
import { formatDecimal } from '@/lib/format';
import { useFormConfig, useFormConfigStore } from '@/store/formConfigStore';
import type { SpssGroupConfig } from '@/types/campaign';
import type { ParsedFormStructure } from '@/types/form';

import { SpssGroupDialog } from './SpssGroupDialog';

/** Tab "Nhóm tương quan SPSS": danh sách nhóm + mở hộp thoại tạo/sửa. */
export function SpssPanel({ formId, structure }: { formId: string; structure: ParsedFormStructure }) {
  const config = useFormConfig(formId);
  const removeGroup = useFormConfigStore((s) => s.removeGroup);
  const [editing, setEditing] = useState<SpssGroupConfig | null | 'new'>(null);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="m-0 flex items-center gap-1 text-sm text-muted">
          Gom các câu thang đo cùng đo một yếu tố (VD: các hàng của một câu lưới) để dữ liệu nhất quán khi chạy SPSS.
          <InfoHint term="Cronbach’s Alpha">Độ nhất quán của nhóm câu thang đo, từ 0 đến 1. Từ 0,7 trở lên thường được coi là đạt.</InfoHint>
        </p>
        <Button variant="primary" onClick={() => setEditing('new')}><Plus aria-hidden className="size-4" />Tạo nhóm</Button>
      </div>
      {config.groups.length === 0 ? (
        <Card><EmptyState title="Chưa có nhóm nào" description="Bấm Tạo nhóm, chọn các câu thang đo cùng thang (VD 1–5), đặt điểm trung bình rồi kiểm tra thử Alpha." /></Card>
      ) : (
        config.groups.map((group) => (
          <Card key={group.group_id} className="flex flex-wrap items-center justify-between gap-3 px-5 py-4">
            <div className="flex flex-col gap-0.5">
              <strong className="text-[15px]">{group.name}</strong>
              <span className="text-[13px] text-muted">
                {group.entries.length} biến · trung bình {formatDecimal(group.mean)} · SD {formatDecimal(group.std)} ·{' '}
                {group.r !== null ? `r = ${formatDecimal(group.r)}` : `α mục tiêu ${formatDecimal(group.alpha_target)}`}
                {group.reversed_entries.length > 0 && ` · ${group.reversed_entries.length} biến đảo chiều`}
              </span>
            </div>
            <div className="flex gap-2">
              <Button size="sm" onClick={() => setEditing(group)}>Sửa</Button>
              <Button size="sm" variant="danger" onClick={() => removeGroup(formId, group.group_id)}>Xóa</Button>
            </div>
          </Card>
        ))
      )}
      {editing !== null && (
        <SpssGroupDialog formId={formId} structure={structure} initial={editing === 'new' ? null : editing} onClose={() => setEditing(null)} />
      )}
    </div>
  );
}
