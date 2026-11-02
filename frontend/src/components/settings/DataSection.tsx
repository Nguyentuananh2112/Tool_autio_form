import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import type { AppSettingsRead } from '@/types/settings';

export function DataSection({ settings }: { settings: AppSettingsRead | null }) {
  const openPath = window.autoformDesktop?.openPath;
  return (
    <Card aria-labelledby="s-data" className="flex flex-col gap-3 p-5">
      <h2 id="s-data" className="m-0 text-[17px] font-semibold">Dữ liệu trên máy</h2>
      <div className="flex flex-wrap items-center gap-2.5">
        <code className="min-w-[280px] flex-1 break-all rounded-lg bg-sunken px-3 py-2.5 font-mono text-[13px]">{settings?.data_dir ?? '—'}</code>
        {openPath && settings && <Button onClick={() => void openPath(settings.data_dir)}>Mở thư mục</Button>}
      </div>
      <p className="m-0 text-[13px] text-muted">Mọi form, chiến dịch và nhật ký gửi được lưu trong thư mục này. Sao lưu = chép cả thư mục khi app đang tắt.</p>
    </Card>
  );
}
