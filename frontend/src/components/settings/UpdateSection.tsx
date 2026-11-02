import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { useUpdaterContext } from '@/components/update/UpdaterProvider';

export function UpdateSection({ version }: { version: string | null }) {
  const updater = useUpdaterContext();
  return (
    <Card aria-labelledby="s-up" className="flex flex-col gap-3 p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-col gap-0.5">
          <h2 id="s-up" className="m-0 text-[17px] font-semibold">Cập nhật</h2>
          <span className="text-[13px] text-muted">Phiên bản {version ?? '—'}</span>
        </div>
        <Button disabled={!updater.supported} loading={updater.phase === 'checking'} onClick={() => void updater.check()}>Kiểm tra cập nhật ngay</Button>
      </div>
      {!updater.supported && <Alert tone="info">Tự cập nhật chỉ có trong bản cài đặt (.exe). Bạn đang chạy bản phát triển.</Alert>}
      {updater.phase === 'available' && updater.info && (
        <Alert tone="info" title={`Có phiên bản ${updater.info.version}`} action={<Button variant="primary" size="sm" onClick={updater.openDialog}>Cập nhật</Button>} />
      )}
      {updater.phase === 'idle' && updater.supported && <span className="text-[13px] text-ok">Bạn đang dùng phiên bản mới nhất.</span>}
      {updater.error && <Alert tone="bad">{updater.error}</Alert>}
    </Card>
  );
}
