import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Spinner } from '@/components/ui/EmptyState';
import { ProgressBar } from '@/components/ui/ProgressBar';
import { useBrowserInstall } from '@/hooks/useBrowserInstall';

/** Trình duyệt dự phòng: dùng khi form từ chối dữ liệu gửi trực tiếp (dev-notes RISK-012). */
export function BrowserSection() {
  const { status, error, install } = useBrowserInstall();
  return (
    <Card aria-labelledby="s-browser" className="flex flex-col gap-3 p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-col gap-0.5">
          <h2 id="s-browser" className="m-0 text-[17px] font-semibold">Trình duyệt dự phòng</h2>
          <span className="text-[13px] text-muted">Khi form có kiểm tra dữ liệu phức tạp và từ chối gửi trực tiếp, app mở một trình duyệt ẩn để điền như người dùng.</span>
        </div>
        {status && !status.installed && !status.installing && (
          <Button variant="primary" onClick={() => void install()}>Tải trình duyệt (~120 MB)</Button>
        )}
      </div>
      {!status && !error && <Spinner label="Đang kiểm tra…" />}
      {status?.installed && <span className="text-[13px] text-ok">● Đã sẵn sàng.</span>}
      {status?.installing && (
        <div className="flex flex-col gap-2">
          <ProgressBar value={status.percent ?? 0} label="Tiến độ tải trình duyệt" />
          <span className="tabular text-[13px] text-muted">{status.detail ?? 'Đang tải…'} Bạn vẫn dùng app bình thường trong lúc tải.</span>
        </div>
      )}
      {status && !status.installed && !status.installing && !status.error && (
        <span className="text-[13px] text-muted">Chưa tải. Chỉ cần tải một lần; cần mạng Internet.</span>
      )}
      {status?.error && <Alert tone="bad" title={status.error} />}
      {error && <Alert tone="bad" title={error.message} />}
    </Card>
  );
}
