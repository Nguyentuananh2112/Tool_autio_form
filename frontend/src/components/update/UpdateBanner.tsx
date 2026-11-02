import { Download } from 'lucide-react';

import { Button } from '@/components/ui/Button';

import { useUpdaterContext } from './UpdaterProvider';

export function UpdateBanner() {
  const updater = useUpdaterContext();
  if (updater.phase !== 'available' || !updater.info) return null;
  return (
    <section aria-label="Thông báo cập nhật" className="flex flex-wrap items-center gap-4 rounded-xl border border-accent-line bg-accent-soft px-5 py-4">
      <Download aria-hidden className="size-6 text-accent" />
      <div className="flex min-w-[280px] flex-1 flex-col gap-0.5">
        <strong className="text-[15px]">Đã có phiên bản {updater.info.version}</strong>
        <span className="text-sm text-muted">{updater.info.notes[0] ?? 'Có cải tiến và sửa lỗi mới.'} Dữ liệu của bạn được giữ nguyên.</span>
      </div>
      <div className="flex flex-wrap gap-2">
        <Button variant="quiet" size="sm" onClick={updater.openDialog}>Xem thay đổi</Button>
        <Button variant="primary" size="sm" onClick={updater.openDialog}>Cập nhật ngay</Button>
      </div>
    </section>
  );
}
